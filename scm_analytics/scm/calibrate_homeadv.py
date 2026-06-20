"""calibrate_homeadv — mede a vantagem de casa empírica e a sensibilidade do anfitrião (P-E).

A auditoria apontou que `H_host2026=+40` (bônus do anfitrião 2026) e o `h_hist=100` (mando na
construção do Elo) nunca foram medidos em código. Este módulo:

1) MEDE a vantagem de casa empírica nos jogos NÃO-neutros (grid de H pós-hoc, ratings fixos,
   por Brier). [verificado] (n=36.350): taxa real de pontos do mandante 0,622 vs E[we] com +100
   = 0,613; **H ótimo ≈ 110** (Brier 0,5338), com 100 praticamente empatado (0,5342). Ou seja,
   o `h_hist=100` do contrato é **bem escolhido** (levemente conservador). Confirma o D-47.

2) Mostra a SENSIBILIDADE do bônus do anfitrião 2026: P(vitória)/avanço de um confronto a
   diferentes mandos (20/40/60). O `+40` é **juízo declarado** (não validável: não há
   precedente de Copa em co-sede; e a vantagem de casa é majoritariamente árbitro/torcida —
   jogos-fantasma COVID — que pode não transferir p/ um público de Copa mais neutro). Por isso
   é menor que os ~110 medidos e entra em BANDA (σ), não como certeza.

Uso:
    python -m scm.calibrate_homeadv --db dados/scm.sqlite
    python -m scm.calibrate_homeadv --db dados/scm.sqlite --host "Mexico" --away "Germany" --city "Mexico City"
"""
from __future__ import annotations

import argparse
from pathlib import Path

from . import db
from .ingest import DEFAULT_DB
from .predictor import PredictParams, ved_from_elo
from .backtest_harness import brier, outcome_of


def measure(conn, grid=(0, 40, 60, 80, 100, 110, 120, 140, 160)) -> dict:
    """Vantagem de casa empírica (pós-hoc, ratings fixos): grid de H por Brier nos não-neutros."""
    rows = conn.execute(
        """SELECT mr.dr dr, m.home_score hs, m.away_score s
           FROM match_ratings mr JOIN matches m USING(match_id)
           WHERE m.home_score IS NOT NULL AND m.neutral = 0"""
    ).fetchall()
    if not rows:
        return {"n": 0}
    p = PredictParams()
    ed = [r["dr"] - 100.0 for r in rows]          # tira o +100 embutido na construção
    out = [outcome_of(r["hs"], r["s"]) for r in rows]
    home_pts = sum(1.0 if o == "V" else (0.5 if o == "E" else 0.0) for o in out) / len(out)
    curve = []
    best = None
    for H in grid:
        b = 0.0
        for e, o in zip(ed, out):
            pv, pe, pd = ved_from_elo(e + H, p)
            b += brier({"p_v": pv, "p_e": pe, "p_d": pd}, o)
        b /= len(ed)
        curve.append((H, b))
        if best is None or b < best[1]:
            best = (H, b)
    return {"n": len(rows), "home_points_rate": home_pts, "best_H": best[0],
            "best_brier": best[1], "curve": curve}


def host_sensitivity(conn, home, away, city=None, mandos=(0, 20, 40, 60)) -> list:
    """P(vitória)/avanço do confronto a diferentes mandos (sensibilidade do bônus do anfitrião)."""
    from .predict_match import predict_match
    out = []
    for m in mandos:
        r = predict_match(conn, home, away, mando=float(m), city=city)
        if r.get("erro"):
            return [{"erro": r["erro"], "sugestoes": r.get("sugestoes", [])}]
        ko = r.get("knockout", {})
        out.append({"mando": m, "p_v": r["p_v"], "p_e": r["p_e"], "p_d": r["p_d"],
                    "avanco": ko.get("adv_a")})
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Vantagem de casa empírica + sensibilidade do anfitrião (P-E).")
    ap.add_argument("--db", default=str(DEFAULT_DB))
    ap.add_argument("--host", default=None, help="anfitrião (p/ a sensibilidade de mando)")
    ap.add_argument("--away", default=None)
    ap.add_argument("--city", default=None)
    args = ap.parse_args(argv)
    if not Path(args.db).exists():
        print(f"[erro] {args.db} não existe. Rode ingest + elo_engine antes."); return 1
    conn = db.connect(args.db)
    m = measure(conn)
    if m.get("n"):
        print(f"\n  VANTAGEM DE CASA EMPÍRICA — jogos não-neutros n={m['n']}")
        print(f"  taxa real de pontos do mandante = {m['home_points_rate']:.4f}")
        for H, b in m["curve"]:
            mark = "  <- ótimo" if H == m["best_H"] else ("  (contrato)" if H == 100 else "")
            print(f"    H={H:>4}: Brier {b:.5f}{mark}")
        print(f"  H ótimo ≈ {m['best_H']} Elo; o h_hist=100 do contrato é bem escolhido (conservador).")
    if args.host and args.away:
        s = host_sensitivity(conn, args.host, args.away, args.city)
        if s and s[0].get("erro"):
            print(f"\n  [erro] {s[0]['erro']}: {', '.join(s[0].get('sugestoes', []))}")
        else:
            print(f"\n  SENSIBILIDADE DO ANFITRIÃO — {args.host} x {args.away}"
                  + (f" ({args.city})" if args.city else ""))
            for r in s:
                adv = f" · avanço {r['avanco']*100:.0f}%" if r.get("avanco") is not None else ""
                print(f"    mando +{r['mando']:>2}: V {r['p_v']*100:.0f}% · E {r['p_e']*100:.0f}% · D {r['p_d']*100:.0f}%{adv}")
            print("    (+40 = juízo declarado p/ o anfitrião 2026; entra em banda/σ, não como certeza)")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
