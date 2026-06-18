"""calibrate_total — calibra o NÍVEL de gols (T_base) na métrica que ele afeta: BTTS/over.

O grid antigo (`calibrate.py`) media a Brier de 1X2, quase insensível a T_base — por isso
T_base nunca foi calibrado onde importa. Aqui medimos o **viés de calibração** de BTTS e
over 2.5 (previsto − real), escolhemos T_base no TREINO (date<cutoff) e validamos no TESTE
(≥cutoff), com **guarda** de que a Brier de 1X2 não piora (IC bootstrap pareado).
1 grau de liberdade, auditável. Sem rede; roda local.
"""
from __future__ import annotations

import argparse

from . import db
from .ingest import DEFAULT_DB

T_BASE_GRID = [2.2, 2.3, 2.4, 2.5, 2.6, 2.7]


def _rows(conn, cutoff, side, only_major):
    from .backtest_harness import MAJOR
    op = "<" if side == "train" else ">="
    q = (f"SELECT m.home_score hs, m.away_score s, f.dr_adj dr, f.sigma_dr sg, m.tournament t "
         f"FROM match_features f JOIN matches m USING (match_id) "
         f"WHERE m.home_score IS NOT NULL AND m.away_score IS NOT NULL AND m.date {op} ?")
    rows = conn.execute(q, (cutoff,)).fetchall()
    if only_major:
        rows = [r for r in rows if r["t"] in MAJOR]
    return rows


def _eval(rows, t_base):
    from .predictor import PredictParams, predict
    from .backtest_harness import brier, outcome_of
    p = PredictParams(t_base=t_base)
    sb = so = ab = ao = b1 = 0.0
    briers = []
    n = 0
    for r in rows:
        pr = predict(r["dr"], r["sg"], p)
        sb += pr["p_btts"]; so += pr["p_over25"]
        ab += 1.0 if (r["hs"] > 0 and r["s"] > 0) else 0.0
        ao += 1.0 if (r["hs"] + r["s"] >= 3) else 0.0
        bk = brier(pr, outcome_of(r["hs"], r["s"]))
        b1 += bk; briers.append(bk); n += 1
    if n == 0:
        return None
    return {"n": n, "btts_pred": sb / n, "btts_act": ab / n, "btts_bias": (sb - ab) / n,
            "over_pred": so / n, "over_act": ao / n, "over_bias": (so - ao) / n,
            "brier1x2": b1 / n, "briers": briers}


def calibrate_total(conn, cutoff="2015-01-01", grid=None, only_major=True, seed=12345):
    from .backtest_harness import brier, outcome_of, _boot_ci
    from .predictor import PredictParams, predict
    grid = grid or T_BASE_GRID
    tr = _rows(conn, cutoff, "train", only_major)
    te = _rows(conn, cutoff, "test", only_major)
    if not tr or not te:
        return {"n_train": len(tr), "n_test": len(te)}
    # escolhe no TREINO: minimiza |viés BTTS| + |viés over|
    scored = [(tb, _eval(tr, tb)) for tb in grid]
    best = min(scored, key=lambda x: abs(x[1]["btts_bias"]) + abs(x[1]["over_bias"]))[0]
    base_te = _eval(te, 2.6)
    cand_te = _eval(te, best)
    # guarda: ΔBrier 1X2 pareado (base − cand); >0 = cand melhor. IC não pode mostrar piora.
    p_base, p_cand = PredictParams(t_base=2.6), PredictParams(t_base=best)
    d1 = []
    for r in te:
        o = outcome_of(r["hs"], r["s"])
        d1.append(brier(predict(r["dr"], r["sg"], p_base), o)
                  - brier(predict(r["dr"], r["sg"], p_cand), o))
    lo, hi = _boot_ci(d1, B=3000, seed=seed)
    mean1 = sum(d1) / len(d1)
    nao_piora = hi > 0 or abs(mean1) < 1e-4 or lo > -0.0010   # 1X2 não regride de forma material
    melhora_btts = abs(cand_te["btts_bias"]) < abs(base_te["btts_bias"]) - 0.005
    return {"cutoff": cutoff, "best_t_base": best, "base": base_te, "cand": cand_te,
            "d_brier1x2_mean": mean1, "ic_lo": lo, "ic_hi": hi,
            "adotar": bool(melhora_btts and nao_piora)}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Calibra T_base na Brier de BTTS/over (treino/teste).")
    p.add_argument("--db", default=str(DEFAULT_DB))
    p.add_argument("--cutoff", default="2015-01-01")
    p.add_argument("--all", action="store_true", help="não restringe a torneios major")
    args = p.parse_args(argv)
    conn = db.connect(args.db)
    r = calibrate_total(conn, args.cutoff, only_major=not args.all)
    conn.close()
    if "best_t_base" not in r:
        print(f"[!] dados insuficientes (treino={r.get('n_train')}, teste={r.get('n_test')}). "
              f"Rode features_pit/predictor antes."); return 1
    b, c = r["base"], r["cand"]
    print(f"\n  CALIBRAÇÃO DO NÍVEL DE GOLS (T_base)  — teste ≥ {r['cutoff']}, n={c['n']}")
    print(f"  T_base escolhido no treino: {r['best_t_base']:.2f}  (atual 2.60)")
    print(f"  BTTS:  base {b['btts_pred']*100:.1f}% (viés {b['btts_bias']*100:+.1f}pp)  →  "
          f"cand {c['btts_pred']*100:.1f}% (viés {c['btts_bias']*100:+.1f}pp)   |  real {c['btts_act']*100:.1f}%")
    print(f"  Over2.5: base {b['over_pred']*100:.1f}% (viés {b['over_bias']*100:+.1f}pp)  →  "
          f"cand {c['over_pred']*100:.1f}% (viés {c['over_bias']*100:+.1f}pp)   |  real {c['over_act']*100:.1f}%")
    print(f"  Guarda 1X2: ΔBrier {r['d_brier1x2_mean']:+.4f}  IC95 [{r['ic_lo']:+.4f}, {r['ic_hi']:+.4f}] "
          f"(>0 = cand melhor; não pode regredir)")
    print(f"  → {'ADOTAR T_base=%.2f ✓ (melhora BTTS/over sem piorar 1X2)' % r['best_t_base'] if r['adotar'] else 'manter 2.60 (sem ganho claro)'}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
