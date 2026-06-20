"""Altitude (E1) — termo GD_alt (McSharry), atrás do portão.

Usa a **cidade** da partida (do martj42) + tabelas pequenas de elevação (fatos públicos,
**[verificar via Open-Meteo Elevation]**). McSharry (BMJ 2007): ~½ gol de saldo por 1000 m
de diferença; só morde para o time **não-adaptado** jogando em sede alta.

    pen(T)  = max(0, elev_sede − elev_casa_T)
    GD_alt  = θ_alt · (pen_away − pen_home) / 1000        (favorece quem está adaptado)

Aceite (portão): `compare()` v0.1 vs v0.1+altitude **só nos jogos de altitude** (gd_alt≠0);
mantém o termo SSE o IC do ΔBrier não cruza zero. Ver vault `02 - Modelos/Ajustes ambientais`.
"""
from __future__ import annotations

import argparse
import unicodedata

from . import db
from .predictor import PredictParams, predict
from .backtest_harness import brier, outcome_of, gate
from .ingest import DEFAULT_DB

THETA_ALT = 0.5  # gol/1000 m (McSharry, CONMEBOL) — [a calibrar fora da CONMEBOL]

def _norm(s) -> str:
    """minúsculas + sem acentos (casa 'Bogotá'/'bogota'/'Ciudad de México' etc.)."""
    s = unicodedata.normalize("NFKD", (s or "").strip().lower())
    return "".join(ch for ch in s if not unicodedata.combining(ch))


# Elevação (m) de cidades-sede de altitude. Fatos públicos aproximados — [verificar via Open-Meteo].
# Chaves SEM acento (a busca normaliza). Limiar prático ~1500 m: cidades abaixo disso
# (ex.: Monterrey 540 m) são tratadas como nível do mar — não são "altitude".
# Inclui as sedes ALTAS da Copa 2026: Cidade do México (2240) e Guadalajara (1566).
CITY_ALT = {
    "la paz": 3637, "el alto": 4150, "oruro": 3706, "potosi": 4070, "cochabamba": 2558,
    "sucre": 2810, "quito": 2850, "bogota": 2640, "cusco": 3399, "cuzco": 3399,
    "arequipa": 2335, "pasto": 2527,
    "mexico city": 2240, "ciudad de mexico": 2240, "toluca": 2660, "puebla": 2135,
    "guadalajara": 1566, "zapopan": 1566,   # Guadalajara/Estadio Akron (sede 2026)
}
# Altitude "de casa" das seleções adaptadas (m). Default 0 (litoral) p/ as demais. [verificar]
# As 4 seleções genuinamente adaptadas à altitude (jogam mando em cidade alta).
TEAM_HOME_ALT = {"Bolivia": 3637, "Ecuador": 2850, "Colombia": 2640, "Mexico": 2240}


def venue_alt(city) -> float:
    return float(CITY_ALT.get(_norm(city), 0.0))


def team_alt(name) -> float:
    return float(TEAM_HOME_ALT.get(name, 0.0))


def gd_alt(city, home_team, away_team, theta: float = THETA_ALT) -> float:
    v = venue_alt(city)
    pen_home = max(0.0, v - team_alt(home_team))
    pen_away = max(0.0, v - team_alt(away_team))
    return theta * (pen_away - pen_home) / 1000.0


def gate_altitude(conn, versao: str = "baseline-v0.1", theta: float = THETA_ALT,
                  B: int = 10000, seed: int = 12345) -> dict:
    """Portão do termo de altitude: compara v0.1 vs v0.1+GD_alt SÓ nos jogos de altitude."""
    rows = conn.execute(
        """SELECT mf.dr_adj AS dr, mf.sigma_dr AS sg, m.home_score AS hs, m.away_score AS a,
                  m.city AS city, th.name AS home, ta.name AS away
           FROM match_features mf JOIN matches m USING (match_id)
           JOIN teams th ON th.team_id = m.home_team_id
           JOIN teams ta ON ta.team_id = m.away_team_id"""
    ).fetchall()
    p = PredictParams()
    deltas = []
    for r in rows:
        ga = gd_alt(r["city"], r["home"], r["away"], theta)
        if abs(ga) < 1e-9:
            continue  # só jogos onde a altitude de fato morde
        o = outcome_of(r["hs"], r["a"])
        base = predict(r["dr"], r["sg"], p)
        alt = predict(r["dr"], r["sg"], p, gd_alt=ga)
        b0 = brier({"p_v": base["p_v"], "p_e": base["p_e"], "p_d": base["p_d"]}, o)
        b1 = brier({"p_v": alt["p_v"], "p_e": alt["p_e"], "p_d": alt["p_d"]}, o)
        deltas.append(b0 - b1)  # >0 = altitude melhora o Brier
    if not deltas:
        return {"n_alt": 0, "keep": False}
    g = gate(deltas, B=B, seed=seed)
    return {"n_alt": len(deltas), **g}


# Sedes de altitude da CONCACAF (México); o restante de CITY_ALT é CONMEBOL.
MX_CITIES = {"mexico city", "ciudad de mexico", "toluca", "puebla", "guadalajara", "zapopan"}


def confederation_of(city) -> Optional[str]:
    """'CONCACAF' / 'CONMEBOL' / None (sem altitude) p/ a cidade-sede."""
    if venue_alt(city) <= 0:
        return None
    return "CONCACAF" if _norm(city) in MX_CITIES else "CONMEBOL"


def gate_by_confederation(conn, theta: float = THETA_ALT, B: int = 10000, seed: int = 12345) -> dict:
    """Portão da altitude SEPARADO por confederação — revisa se θ deveria diferir (audit).

    Achado no DB local: θ=0,5 sustenta nas DUAS. CONMEBOL ΔBrier ~+0,066 IC[+0,035,+0,096];
    CONCACAF ~+0,023 IC[+0,001,+0,045] (mais fraco, porém positivo; θ ótimo ≈0,5 em ambas).
    Ou seja, a força do México em casa é REAL — a superestimação do bracket era o vazamento
    da altitude no mata-mata (D-48, corrigido), não o θ do grupo. Mantém θ único = 0,5.
    """
    rows = conn.execute(
        """SELECT mf.dr_adj dr, mf.sigma_dr sg, m.home_score hs, m.away_score a,
                  m.city city, th.name home, ta.name away
           FROM match_features mf JOIN matches m USING (match_id)
           JOIN teams th ON th.team_id = m.home_team_id
           JOIN teams ta ON ta.team_id = m.away_team_id
           WHERE m.home_score IS NOT NULL"""
    ).fetchall()
    p = PredictParams()
    by = {}
    for r in rows:
        conf = confederation_of(r["city"])
        if not conf:
            continue
        ga = gd_alt(r["city"], r["home"], r["away"], theta)
        if abs(ga) < 1e-9:
            continue
        o = outcome_of(r["hs"], r["a"])
        b0 = brier(predict(r["dr"], r["sg"], p), o)
        b1 = brier(predict(r["dr"], r["sg"], p, gd_alt=ga), o)
        by.setdefault(conf, []).append(b0 - b1)
    return {conf: {"n": len(d), **gate(d, B=B, seed=seed)} for conf, d in by.items()}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Portão do termo de altitude (E1).")
    p.add_argument("--db", default=str(DEFAULT_DB))
    p.add_argument("--theta", type=float, default=THETA_ALT)
    p.add_argument("--by-confed", action="store_true", help="portão separado por confederação (CONMEBOL vs CONCACAF)")
    args = p.parse_args(argv)
    conn = db.connect(args.db)
    if args.by_confed:
        res = gate_by_confederation(conn, theta=args.theta)
        conn.close()
        if not res:
            print("nenhum jogo de altitude encontrado."); return 1
        print(f"Portão da altitude por confederação (θ={args.theta}):")
        for conf, g in sorted(res.items()):
            print(f"  {conf}: n={g['n']}  ΔBrier {g['mean']:+.4f}  IC95 [{g['ic_lo']:+.4f}, {g['ic_hi']:+.4f}]"
                  f"  -> {'mantém' if g['keep'] else 'NÃO sustenta'}")
        return 0
    r = gate_altitude(conn, theta=args.theta)
    conn.close()
    if r["n_alt"] == 0:
        print("nenhum jogo de altitude encontrado (cidades em CITY_ALT)."); return 1
    print(f"jogos de altitude: n={r['n_alt']}  (θ_alt={args.theta})")
    print(f"ganho de Brier (com altitude) = {r['mean']:+.4f}  IC95 [{r['ic_lo']:+.4f}, {r['ic_hi']:+.4f}]")
    print(f"MANTER altitude? (IC não cruza 0) -> {'SIM' if r['keep'] else 'NÃO'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
