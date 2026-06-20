"""calibrate_binned — candidato (P-C): recalibração do FAVORITO por faixa de p_max, no portão.

A auditoria mediu SUPERCONFIANÇA na faixa [0,8–0,9] (obs 0,74 vs banda [0,84–0,92]). A
recalibração GLOBAL (temperatura/isotônica em todas as probs) já foi testada e REJEITADA
(D-40: T*=1,0 — nada a corrigir na média). Esta é DIFERENTE: ajusta só a prob do TOP pick POR
FAIXA de p_max (curva isotônica do TREINO), mantendo soma 1 (as outras 2 escalam proporcional).
Portão ΔBrier treino/teste, IC bootstrap. OFF por padrão — não altera o pipeline.

Uso:
    python -m scm.calibrate_binned --db dados/scm.sqlite [--major] [--cutoff 2018-01-01]
"""
from __future__ import annotations

import argparse
from pathlib import Path

from . import db
from .ingest import DEFAULT_DB
from .backtest_harness import brier, outcome_of, gate, MAJOR
from .calibrate_confidence import _isotonic

DEFAULT_CUTOFF = "2018-01-01"
_OIDX = {"V": 0, "E": 1, "D": 2}


def _top_idx(p) -> int:
    return max(range(3), key=lambda i: p[i])


def build_map(rows, n_bins: int = 10, min_n: int = 20):
    """Curva isotônica reliab(p_max) por faixa, do TREINO. rows = (pv,pe,pd,hs,as)."""
    agg = [[0, 0, 0.0] for _ in range(n_bins)]   # n, hits, sum_pmax
    for pv, pe, pd, hs, a in rows:
        p = (pv, pe, pd); pm = max(p); ti = _top_idx(p)
        o = _OIDX[outcome_of(hs, a)]
        b = min(n_bins - 1, int(pm * n_bins))
        agg[b][0] += 1; agg[b][1] += (1 if ti == o else 0); agg[b][2] += pm
    raw = [(c[2] / c[0], c[1] / c[0], c[0]) for c in agg if c[0] >= min_n]
    if len(raw) < 2:
        return None
    sm = _isotonic([r[1] for r in raw], [r[2] for r in raw])
    return sorted((raw[k][0], sm[k]) for k in range(len(raw)))


def apply_map(p, cmap):
    """Recalibra o TOP pick p/ reliab(p_max); escala as outras 2 mantendo soma 1."""
    pm = max(p); ti = _top_idx(p)
    if pm <= cmap[0][0]:
        r = cmap[0][1]
    elif pm >= cmap[-1][0]:
        r = cmap[-1][1]
    else:
        r = cmap[-1][1]
        for k in range(1, len(cmap)):
            if pm <= cmap[k][0]:
                (x0, y0), (x1, y1) = cmap[k - 1], cmap[k]
                t = (pm - x0) / (x1 - x0) if x1 > x0 else 0.0
                r = y0 + t * (y1 - y0); break
    r = min(0.96, max(0.04, r))
    rest = 1.0 - pm
    scale = (1.0 - r) / rest if rest > 1e-9 else 0.0
    out = [r if i == ti else p[i] * scale for i in range(3)]
    s = sum(out) or 1.0
    return [x / s for x in out]


def run_gate(conn, cutoff: str = DEFAULT_CUTOFF, only_major: bool = True,
             B: int = 10000, seed: int = 12345) -> dict:
    q = ("SELECT p.p_v, p.p_e, p.p_d, m.home_score hs, m.away_score a, m.date d, m.tournament t "
         "FROM predictions p JOIN matches m USING(match_id) WHERE m.home_score IS NOT NULL")
    rows = conn.execute(q).fetchall()
    if only_major:
        rows = [r for r in rows if r["t"] in MAJOR]
    tr = [(r["p_v"], r["p_e"], r["p_d"], r["hs"], r["a"]) for r in rows if r["d"] < cutoff]
    te = [r for r in rows if r["d"] >= cutoff]
    if len(tr) < 200 or len(te) < 100:
        return {"erro": "amostra insuficiente", "n_train": len(tr), "n_test": len(te)}
    cmap = build_map(tr)
    if not cmap:
        return {"erro": "suporte insuficiente p/ a curva de treino"}
    deltas = []
    for r in te:
        o = outcome_of(r["hs"], r["a"]); p = (r["p_v"], r["p_e"], r["p_d"])
        b0 = brier({"p_v": p[0], "p_e": p[1], "p_d": p[2]}, o)
        qq = apply_map(p, cmap)
        b1 = brier({"p_v": qq[0], "p_e": qq[1], "p_d": qq[2]}, o)
        deltas.append(b0 - b1)   # >0 = recal melhora
    g = gate(deltas, B=B, seed=seed)
    return {"n_test": len(te), "n_train": len(tr), "map": cmap, **g}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Recalibração do favorito por faixa (candidato P-C).")
    ap.add_argument("--db", default=str(DEFAULT_DB))
    ap.add_argument("--cutoff", default=DEFAULT_CUTOFF)
    ap.add_argument("--major", action="store_true", help="só torneios (WC/Euro/Copa América)")
    args = ap.parse_args(argv)
    if not Path(args.db).exists():
        print(f"[erro] {args.db} não existe. Rode o pipeline antes."); return 1
    conn = db.connect(args.db)
    r = run_gate(conn, args.cutoff, only_major=args.major)
    conn.close()
    if r.get("erro"):
        print("[!]", r["erro"], {k: v for k, v in r.items() if k != "map"}); return 1
    print(f"\n  RECALIBRAÇÃO POR FAIXA (candidato P-C) — teste ≥ {args.cutoff}, n_teste={r['n_test']}")
    print(f"  ΔBrier (recal − base, >0 = melhora) = {r['mean']:+.5f}  "
          f"IC95 [{r['ic_lo']:+.5f}, {r['ic_hi']:+.5f}]")
    print(f"  → {'ADOTAR ✓ (IC>0)' if r['keep'] else 'NÃO adotar (IC cruza/≤0) — modelo já ~calibrado'}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
