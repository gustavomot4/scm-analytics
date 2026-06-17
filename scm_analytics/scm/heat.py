"""Calor (E3) — reduz o TOTAL de gols: T_m *= (1 − κ_heat·excesso_WBGT). κ [a calibrar].

WBGT (proxy de bulbo úmido, sem sol/vento) por jogo, a partir de **climatologia mensal por
cidade** (Open-Meteo Archive, construída 1x na máquina do usuário — `build_climatology`).
Sem coeficiente publicado para κ → ajustado no **treino** e validado no **teste** (anti
p-hacking). Ver `02 - Modelos/Ajustes ambientais`, contrato §3.11/E3.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from . import db
from .predictor import PredictParams, predict
from .backtest_harness import brier, outcome_of, gate
from .ingest import DEFAULT_DB

WBGT_THRESHOLD = 28.0   # °C — estresse térmico relevante [verificar]
HEAT_FLOOR = 0.85       # T_m reduz no máximo 15%
CLIMA_PATH = Path(__file__).resolve().parent.parent / "dados" / "climatology.json"

# Só vale buscar clima onde o calor pode morder (WBGT alto). Filtra a ingestão p/ ser viável.
HOT_COUNTRIES = {
    "Qatar","United Arab Emirates","Saudi Arabia","Kuwait","Bahrain","Oman","Iraq","Iran","Yemen",
    "Egypt","Sudan","Libya","Algeria","Morocco","Tunisia","Mauritania",
    "Nigeria","Ghana","Senegal","Ivory Coast","Cameroon","Mali","Burkina Faso","Guinea","Gabon",
    "DR Congo","Congo","Angola","Kenya","Tanzania","Uganda","Ethiopia","Somalia","Zambia","Zimbabwe",
    "Brazil","Mexico","Colombia","Venezuela","Ecuador","Peru","Bolivia","Paraguay","Guyana","Suriname",
    "Panama","Costa Rica","Honduras","Nicaragua","Guatemala","El Salvador","Cuba","Jamaica","Haiti",
    "Dominican Republic","Trinidad and Tobago",
    "India","Pakistan","Bangladesh","Sri Lanka","Thailand","Vietnam","Malaysia","Indonesia","Singapore",
    "Philippines","Myanmar","Cambodia","United States","Australia",
}


def wbgt(temp_c: float, rh: float) -> float:
    """Proxy WBGT (Australian BoM, sem sol/vento). temp_c em °C, rh em %."""
    e = (rh / 100.0) * 6.105 * math.exp(17.27 * temp_c / (237.7 + temp_c))  # pressão de vapor (hPa)
    return 0.567 * temp_c + 0.393 * e + 3.94


def excesso(temp_c: float, rh: float, threshold: float = WBGT_THRESHOLD) -> float:
    return max(0.0, wbgt(temp_c, rh) - threshold)


def heat_factor(temp_c: float, rh: float, kappa: float,
                threshold: float = WBGT_THRESHOLD, floor: float = HEAT_FLOOR) -> float:
    return max(floor, 1.0 - kappa * excesso(temp_c, rh, threshold))


# ---------------- Open-Meteo (REDE; roda na máquina do usuário) ----------------
def _geocode(city: str):
    import requests
    r = requests.get("https://geocoding-api.open-meteo.com/v1/search",
                     params={"name": city, "count": 1}, timeout=30).json()
    res = r.get("results")
    return (res[0]["latitude"], res[0]["longitude"]) if res else None


def build_climatology(conn, year: int = 2023, path=CLIMA_PATH, all_cities: bool = False) -> dict:
    """Climatologia mensal (Tmax médio, RH médio) por cidade única, via Open-Meteo. Cacheia JSON.
    LENTO: ~1 chamada por cidade. Roda na máquina do usuário (requer rede)."""
    import requests
    path = Path(path)
    clima = json.loads(path.read_text()) if path.exists() else {}
    if all_cities:
        cities = [r[0] for r in conn.execute(
            "SELECT DISTINCT city FROM matches WHERE city IS NOT NULL AND city <> ''")]
    else:
        q = ("SELECT DISTINCT city FROM matches WHERE city IS NOT NULL AND city <> '' "
             "AND country IN (%s)" % ",".join("?" * len(HOT_COUNTRIES)))
        cities = [r[0] for r in conn.execute(q, tuple(HOT_COUNTRIES))]
    pend = [c for c in cities if c not in clima]
    print(f"cidades a processar: {len(pend)} (de {len(cities)} em países quentes)", flush=True)
    for i, city in enumerate(cities):
        if i % 20 == 0:
            print(f"  ... {i}/{len(cities)}", flush=True)
        if city in clima:
            continue
        ll = _geocode(city)
        if not ll:
            clima[city] = None
        else:
            d = requests.get("https://archive-api.open-meteo.com/v1/archive", params={
                "latitude": ll[0], "longitude": ll[1],
                "start_date": f"{year}-01-01", "end_date": f"{year}-12-31",
                "daily": "temperature_2m_max,relative_humidity_2m_mean", "timezone": "auto",
            }, timeout=60).json().get("daily", {})
            by_m: dict = {}
            for date, tmax, rh in zip(d.get("time", []), d.get("temperature_2m_max", []),
                                      d.get("relative_humidity_2m_mean", [])):
                if tmax is None:
                    continue
                by_m.setdefault(date[5:7], []).append((tmax, rh if rh is not None else 60.0))
            clima[city] = {m: [sum(t for t, _ in v) / len(v), sum(h for _, h in v) / len(v)]
                           for m, v in by_m.items()}
        if i % 50 == 0:
            path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(clima))
    path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(clima))
    return clima


def load_climatology(path=CLIMA_PATH) -> dict:
    p = Path(path)
    return json.loads(p.read_text()) if p.exists() else {}


def match_excesso(clima: dict, city, month) -> float:
    c = clima.get(city) if city else None
    if not c:
        return 0.0
    mm = c.get(month)
    return excesso(mm[0], mm[1]) if mm else 0.0


# ---------------- portão ----------------
def gate_heat(conn, clima=None, kappas=(0.01, 0.02, 0.03, 0.05),
              cutoff: str = "2014-01-01", B: int = 10000, seed: int = 12345) -> dict:
    if clima is None:
        clima = load_climatology()
    rows = conn.execute(
        """SELECT mf.dr_adj AS dr, mf.sigma_dr AS sg, m.home_score AS hs, m.away_score AS a,
                  m.city AS city, substr(m.date, 6, 2) AS mon, m.date AS date
           FROM match_features mf JOIN matches m USING (match_id)"""
    ).fetchall()
    # Calor afeta o TOTAL de gols -> portão no Brier de OVER/UNDER 2.5 (métrica certa).
    hot = []
    for r in rows:
        exc = match_excesso(clima, r["city"], r["mon"])
        if exc > 0:
            over = 1.0 if (r["hs"] + r["a"]) >= 3 else 0.0
            hot.append((r["dr"], r["sg"], over, exc, r["date"]))
    if not hot:
        return {"n_hot": 0, "keep": False}
    p = PredictParams()
    train = [x for x in hot if x[4] < cutoff]
    test = [x for x in hot if x[4] >= cutoff]
    if not train or not test:
        return {"n_hot": len(hot), "keep": False, "erro": "split treino/teste vazio"}

    def _brier_over_k(rows_, k):
        tot = 0.0
        for dr, sg, over, exc, _ in rows_:
            hf = max(HEAT_FLOOR, 1.0 - k * exc)
            tot += (predict(dr, sg, p, heat_factor=hf)["p_over25"] - over) ** 2
        return tot / len(rows_)

    best_k = min(kappas, key=lambda k: _brier_over_k(train, k))
    deltas = []
    for dr, sg, over, exc, _ in test:
        b0 = (predict(dr, sg, p)["p_over25"] - over) ** 2            # sem calor
        hf = max(HEAT_FLOOR, 1.0 - best_k * exc)
        b1 = (predict(dr, sg, p, heat_factor=hf)["p_over25"] - over) ** 2
        deltas.append(b0 - b1)
    g = gate(deltas, B=B, seed=seed)
    return {"n_hot": len(hot), "n_train": len(train), "n_test": len(test), "best_kappa": best_k, **g}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Calor (E3): climatologia (Open-Meteo) + portão.")
    p.add_argument("--db", default=str(DEFAULT_DB))
    p.add_argument("--build-climatology", action="store_true", help="baixa climatologia por cidade (LENTO, requer rede)")
    p.add_argument("--year", type=int, default=2023)
    p.add_argument("--all-cities", action="store_true", help="todas as cidades (LENTÍSSIMO); padrão só países quentes")
    args = p.parse_args(argv)
    conn = db.connect(args.db)
    if args.build_climatology:
        c = build_climatology(conn, year=args.year, all_cities=args.all_cities)
        print(f"climatologia construída p/ {len(c)} cidades -> {CLIMA_PATH}")
        conn.close(); return 0
    clima = load_climatology()
    if not clima:
        print("[erro] sem climatologia. Rode `python -m scm.heat --build-climatology` (na sua máquina) antes.")
        conn.close(); return 1
    r = gate_heat(conn, clima)
    conn.close()
    if r["n_hot"] == 0:
        print("nenhum jogo quente (WBGT>limiar) encontrado."); return 1
    print(f"jogos quentes: n={r['n_hot']} (treino {r.get('n_train')}, teste {r.get('n_test')}) | melhor κ={r.get('best_kappa')}")
    if "mean" in r:
        print(f"ganho de Brier OVER/UNDER (com calor) = {r['mean']:+.4f}  IC95 [{r['ic_lo']:+.4f}, {r['ic_hi']:+.4f}]")
        print(f"MANTER calor? (IC não cruza 0) -> {'SIM' if r['keep'] else 'NÃO'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
