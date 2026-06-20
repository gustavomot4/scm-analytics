"""calibrate_form — candidato (P-D): forma saturante de GD (tanh) vs linear, atrás do portão.

A forma linear GD=θ·dr/100 faz λ_B=(T_m−GD)/2 ficar NEGATIVO no tail (dr≳740); o piso o trava e
passa a MODELAR (audit P-D, verificado: dr=900 → λ_B bruto −0,275). A saturante
GD_max·tanh(dr/escala) (apêndice formas v5) mantém λ_B>0 sem depender do clamp. Aqui o PORTÃO
compara as duas no backtest (ΔBrier pareado por jogo, IC bootstrap), como os demais candidatos.

OFF por padrão. Para ADOTAR (se o IC>0): use PredictParams(gd_form="sat") no `predictor` e
re-rode o pipeline (features já servem; muda só o predictor). Probabilidade, não certeza.

Uso:
    python -m scm.calibrate_form --db dados/scm.sqlite [--major]
"""
from __future__ import annotations

import argparse
from dataclasses import replace
from pathlib import Path

from . import db
from .ingest import DEFAULT_DB
from .predictor import PredictParams, predict
from .backtest_harness import brier, outcome_of, gate, MAJOR
from .factors import gd_alt


def run_gate(conn, only_major: bool = True, B: int = 10000, seed: int = 12345) -> dict:
    q = ("SELECT mf.dr_adj dr, mf.sigma_dr sg, m.home_score hs, m.away_score a, m.city city, "
         "th.name home, ta.name away FROM match_features mf JOIN matches m USING(match_id) "
         "JOIN teams th ON th.team_id=m.home_team_id JOIN teams ta ON ta.team_id=m.away_team_id "
         "WHERE m.home_score IS NOT NULL")
    params = []
    if only_major:
        q += " AND m.tournament IN (%s)" % ",".join("?" * len(MAJOR))
        params = list(MAJOR)
    rows = conn.execute(q, params).fetchall()
    lin = PredictParams()
    sat = replace(lin, gd_form="sat")
    deltas = []
    for r in rows:
        ga = gd_alt(r["city"], r["home"], r["away"])
        o = outcome_of(r["hs"], r["a"])
        b0 = brier(predict(r["dr"], r["sg"], lin, gd_alt=ga), o)
        b1 = brier(predict(r["dr"], r["sg"], sat, gd_alt=ga), o)
        deltas.append(b0 - b1)   # >0 = saturante melhora o Brier
    if not deltas:
        return {"n": 0}
    g = gate(deltas, B=B, seed=seed)
    return {"n": len(deltas), **g}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Portão da forma saturante de GD (candidato P-D).")
    ap.add_argument("--db", default=str(DEFAULT_DB))
    ap.add_argument("--major", action="store_true", help="só torneios (WC/Euro/Copa América)")
    args = ap.parse_args(argv)
    if not Path(args.db).exists():
        print(f"[erro] {args.db} não existe. Rode o pipeline antes."); return 1
    conn = db.connect(args.db)
    r = run_gate(conn, only_major=args.major)
    conn.close()
    if not r.get("n"):
        print("sem dados (rode o pipeline)."); return 1
    print(f"\n  FORMA SATURANTE de GD (candidato P-D) — n={r['n']}")
    print(f"  ΔBrier (sat − linear, >0 = sat melhora) = {r['mean']:+.5f}  "
          f"IC95 [{r['ic_lo']:+.5f}, {r['ic_hi']:+.5f}]")
    print(f"  → {'ADOTAR sat ✓ (IC>0)' if r['keep'] else 'NÃO adotar — mantém linear (IC cruza/≤0)'}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
