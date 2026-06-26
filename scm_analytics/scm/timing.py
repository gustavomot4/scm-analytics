"""timing — tempo do gol (D-51): curva empírica de minuto do gol -> mercados de tempo.

POR QUE: "quando sai o gol" não sai da matriz de placar (que só vê o total). Mas a
DISTRIBUIÇÃO do minuto do gol é estável e barata: modelamos como um processo de Poisson
NÃO-HOMOGÊNEO. Com Λ = λ_a+λ_b gols esperados e F(t) = fração empírica de gols até o min t:

    gols em [0,t] ~ Poisson(Λ·F(t))
    P(1º gol até o min X) = 1 − exp(−Λ·F(X))
    P(gol no 1º tempo)    = 1 − exp(−Λ·F(45))
    P(gol no 2º tempo)    = 1 − exp(−Λ·(1−F(45)))
    P(gol nos dois tempos)= P(≥1 1ºT)·P(≥1 2ºT)        (incrementos disjuntos => independentes)
    Resultado no intervalo (HT): gols por time no 1ºT ~ Poisson(λ_i·F(45)).

NÃO entra em λ nem muda o 1X2 — é leitura derivada (como markets()). Portão validado
(2026-06, StatsBomb local): previsto×observado em ±1,2pp (gol 1ºT/2ºT/dois tempos/0 gols).

FONTES da curva (a curva é só um JSON em dados/goal_timing.json):
  • StatsBomb open-data LOCAL (sem rede): python -m scm.timing build-sb open-data
      Cobertura PARCIAL (6 comps de seleção 2018-2024, ~800 gols) — gol-timing é estável.
  • martj42 goalscorers.csv (amostra AMPLA; você baixa 1x, requer rede, SUA máquina):
      python -m scm.timing download
      python -m scm.timing build-csv dados/goalscorers.csv
NADA lê a internet no cálculo: o build cria um snapshot (a curva) em disco.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
import time
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
DEFAULT_CURVE = _BASE / "dados" / "goal_timing.json"
GOALSCORERS_URL = "https://raw.githubusercontent.com/martj42/international_results/master/goalscorers.csv"
DEFAULT_GOALSCORERS = _BASE / "dados" / "goalscorers.csv"

_BANDS = (("0–15", 0, 15), ("16–30", 15, 30), ("31–45", 30, 45),
          ("46–60", 45, 60), ("61–75", 60, 75), ("76–90", 75, 90))


def _curve_from_hist(hist, names, n_matches, source):
    """hist: lista 0..90 (contagem por minuto da partida). Monta cdf/f45/bandas."""
    ng = sum(hist)
    if ng == 0:
        raise ValueError("sem gols na amostra")
    cdf = [0.0] * 91
    acc = 0
    for t in range(1, 91):
        acc += hist[t]
        cdf[t] = acc / ng
    bands = {nm: round(sum(hist[lo + 1:hi + 1]) / ng, 4) for nm, lo, hi in _BANDS}
    return {"source": source, "competicoes": names, "n_matches": n_matches, "n_goals": ng,
            "f45": round(cdf[45], 4), "cdf": [round(x, 5) for x in cdf[1:]], "bands": bands,
            "built": time.strftime("%Y-%m-%d"),
            "nota": "Curva empírica de minuto do gol (regulamentar). Probabilidade, não certeza."}


def build_curve_from_statsbomb(repo_path, out_path=DEFAULT_CURVE, min_year=2018):
    """Curva de minuto do gol a partir de um clone LOCAL do StatsBomb open-data (sem rede)."""
    base = Path(repo_path) / "data"
    comps = json.loads((base / "competitions.json").read_text(encoding="utf-8"))

    def yr(s):
        m = re.search(r"(19|20)\d{2}", s or "")
        return int(m.group(0)) if m else 0

    youth = ("u20", "u-20", "u23", "u-23", "u21", "u17", "u-17", "women", "olympic")
    sel = []
    for c in comps:
        nmc = (c.get("competition_name") or "").lower()
        if ((c.get("competition_gender") or "male") == "male" and c.get("competition_international", None) is True
                and not any(y in nmc for y in youth) and yr(c.get("season_name")) >= min_year):
            sel.append((c["competition_id"], c["season_id"], c.get("competition_name"), c.get("season_name")))
    hist = [0] * 91
    n_matches = 0
    names = []
    for cid, sid, cn, sn in sorted(sel):
        names.append(f"{cn} {sn}")
        mp = base / "matches" / str(cid) / f"{sid}.json"
        if not mp.exists():
            continue
        for m in json.loads(mp.read_text(encoding="utf-8")):
            ep = base / "events" / f"{m['match_id']}.json"
            if not ep.exists():
                continue
            try:
                ev = json.loads(ep.read_text(encoding="utf-8"))
            except (ValueError, OSError):
                continue
            n_matches += 1
            for e in ev:
                t = (e.get("type") or {}).get("name")
                is_goal = (t == "Shot" and ((e.get("shot") or {}).get("outcome") or {}).get("name") == "Goal") \
                    or t == "Own Goal Against"
                if not is_goal:
                    continue
                prd = e.get("period")
                mn = e.get("minute") or 0
                if prd == 1:
                    hist[min(45, max(1, mn))] += 1
                elif prd == 2:
                    hist[min(90, max(46, mn))] += 1
    curve = _curve_from_hist(hist, names, n_matches, "statsbomb-open-data")
    if out_path:
        Path(out_path).write_text(json.dumps(curve, ensure_ascii=False, indent=1), encoding="utf-8")
    return curve


def _parse_minute(s):
    """'45+2'->45(1ºT); '90+3'->90(2ºT); '67'->67(2ºT); '23'->23(1ºT). None se vazio/ruim."""
    s = (s or "").strip()
    if not s:
        return None
    base = s.split("+")[0]
    try:
        m = int(base)
    except ValueError:
        return None
    if "+" in s:
        return 45 if (base.startswith("45") or m <= 45) else 90
    if m <= 45:
        return max(1, m)
    return min(90, m)


def build_curve_from_goalscorers(csv_path, out_path=DEFAULT_CURVE):
    """Curva de minuto do gol a partir do goalscorers.csv do martj42 (amostra ampla)."""
    hist = [0] * 91
    with Path(csv_path).open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            b = _parse_minute(row.get("minute"))
            if b:
                hist[b] += 1
    curve = _curve_from_hist(hist, ["martj42/international_results"], 0, "martj42-goalscorers")
    if out_path:
        Path(out_path).write_text(json.dumps(curve, ensure_ascii=False, indent=1), encoding="utf-8")
    return curve


def download_goalscorers(dest=DEFAULT_GOALSCORERS, url=GOALSCORERS_URL):
    """Baixa o goalscorers.csv do martj42 (snapshot local 1x; requer rede, sua máquina)."""
    import requests
    Path(dest).parent.mkdir(parents=True, exist_ok=True)
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    Path(dest).write_bytes(r.content)
    return dest


def load_curve(path=DEFAULT_CURVE):
    p = Path(path)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None


def _ht_result(la, lb, mx=8):
    pa = [math.exp(-la) * la ** i / math.factorial(i) for i in range(mx + 1)]
    pb = [math.exp(-lb) * lb ** j / math.factorial(j) for j in range(mx + 1)]
    pv = sum(pa[i] * pb[j] for i in range(mx + 1) for j in range(i))
    pe = sum(pa[k] * pb[k] for k in range(mx + 1))
    return {"home": pv, "draw": pe, "away": max(0.0, 1.0 - pv - pe)}


def timing_markets(lam_a, lam_b, curve):
    """Mercados de tempo do gol a partir da curva empírica + λ. Não muda o 1X2."""
    L = lam_a + lam_b
    cdf = curve["cdf"]
    f45 = curve.get("f45") or cdf[44]

    def F(x):
        x = int(round(x))
        if x <= 0:
            return 0.0
        if x >= 90:
            return 1.0
        return cdf[x - 1]

    def before(x):
        return 1.0 - math.exp(-L * F(x))

    p1 = 1.0 - math.exp(-L * f45)
    p2 = 1.0 - math.exp(-L * (1.0 - f45))
    first_band = {nm: math.exp(-L * F(lo)) - math.exp(-L * F(hi)) for nm, lo, hi in _BANDS}
    return {"before": {"15": before(15), "30": before(30), "45": p1},
            "goal_1h": p1, "goal_2h": p2, "both_halves": p1 * p2, "no_goal": math.exp(-L),
            "first_band": first_band, "ht": _ht_result(lam_a * f45, lam_b * f45),
            "f45": f45, "n_goals": curve.get("n_goals"), "source": curve.get("source")}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Tempo do gol: curva empírica de minutos -> mercados.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("build-sb", help="constrói a curva do StatsBomb open-data LOCAL (sem rede)")
    a.add_argument("repo")
    a.add_argument("--out", default=str(DEFAULT_CURVE))
    b = sub.add_parser("build-csv", help="constrói a curva do goalscorers.csv (martj42, amostra ampla)")
    b.add_argument("csv")
    b.add_argument("--out", default=str(DEFAULT_CURVE))
    sub.add_parser("download", help="baixa o goalscorers.csv do martj42 (requer rede; sua máquina)")
    s = sub.add_parser("show", help="mostra a curva atual")
    s.add_argument("--curve", default=str(DEFAULT_CURVE))
    args = ap.parse_args(argv)
    if args.cmd == "build-sb":
        c = build_curve_from_statsbomb(args.repo, out_path=args.out)
        print(f"curva (StatsBomb): {c['n_goals']} gols, {c['n_matches']} jogos, f45={c['f45']} -> {args.out}")
        return 0
    if args.cmd == "build-csv":
        c = build_curve_from_goalscorers(args.csv, out_path=args.out)
        print(f"curva (martj42): {c['n_goals']} gols, f45={c['f45']} -> {args.out}")
        return 0
    if args.cmd == "download":
        print("baixando goalscorers.csv ->", download_goalscorers())
        return 0
    if args.cmd == "show":
        c = load_curve(args.curve)
        if not c:
            print("sem curva (rode build-sb ou build-csv).")
            return 1
        print(f"fonte {c['source']} · {c.get('n_goals')} gols · f45={c['f45']}\nbandas: {c['bands']}")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
