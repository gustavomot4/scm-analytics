"""calibrate: ajusta os coeficientes placeholder num split de TREINO e valida no TESTE.

Disciplina (camada2-planejamento §3.1–§3.3): grid search minimiza Brier no TREINO;
a adoção só vale se o ganho no TESTE (held-out) tiver IC que não cruza zero (portão).
NÃO altera os defaults automaticamente — reporta os coeficientes e o ganho.

`dr_adj`/`σ_dr` (de match_features) independem dos coeficientes varridos, então a varredura
roda sobre as features prontas. Estratos da propagação são precomputados (1x) por jogo.
"""
from __future__ import annotations

import argparse
import itertools
from statistics import NormalDist

from . import db
from .predictor import PredictParams, lambdas, poisson_reads, draw_prob, _clamp_norm
from .elo_engine import we
from .backtest_harness import brier, outcome_of, gate, MAJOR
from .ingest import DEFAULT_DB

# Grid de coeficientes (inclui os placeholders v0.1: 0.45 / 0.10 / 2.6 / 0.27 / 0.56)
GRID = {
    "theta_gd":  [0.30, 0.45, 0.60],
    "kappa_tm":  [0.05, 0.10, 0.15],
    "t_base":    [2.4, 2.6, 2.8],
    "draw_base": [0.24, 0.27, 0.30],
    "w_poisson": [0.45, 0.56, 0.65],
}


def load_rows(conn, before=None, after=None):
    q = ("SELECT mf.dr_adj AS dr, mf.sigma_dr AS sigma, m.home_score AS hs, m.away_score AS a "
         "FROM match_features mf JOIN matches m USING (match_id) "
         "WHERE m.tournament IN (%s)" % ",".join("?" * len(MAJOR)))
    params = list(MAJOR)
    if before:
        q += " AND m.date < ?"; params.append(before)
    if after:
        q += " AND m.date >= ?"; params.append(after)
    return [(r["dr"], r["sigma"], outcome_of(r["hs"], r["a"]))
            for r in conn.execute(q, params).fetchall()]


def precompute_strata(rows, S):
    out = []
    for dr, sigma, _ in rows:
        nd = NormalDist(dr, max(sigma, 1e-6))
        out.append([nd.inv_cdf((s + 0.5) / S) for s in range(S)])
    return out


def _elo_read(strata, p):
    from .predictor import ved_from_elo
    spv = spe = spd = 0.0
    for dr_s in strata:
        pv, pe, pd = ved_from_elo(dr_s, p)      # núcleo único (D-43)
        spv += pv; spe += pe; spd += pd
    S = len(strata)
    return (spv / S, spe / S, spd / S)


def _triple(dr, strata, p):
    la, lb = lambdas(dr, p)
    po = poisson_reads(la, lb, p.max_goals)
    cp = _clamp_norm((po["pv"], po["pe"], po["pd"]), p.clamp_lo, p.clamp_hi)
    ce = _clamp_norm(_elo_read(strata, p), p.clamp_lo, p.clamp_hi)
    mix = [p.w_poisson * cp[i] + p.w_elo * ce[i] for i in range(3)]
    return _clamp_norm(mix, p.clamp_lo, p.clamp_hi)


def mean_brier(rows, strata, p):
    tot = 0.0
    for (dr, _s, o), st in zip(rows, strata):
        pv, pe, pd = _triple(dr, st, p)
        tot += brier({"p_v": pv, "p_e": pe, "p_d": pd}, o)
    return tot / len(rows)


def _params(kw, S):
    return PredictParams(theta_gd=kw["theta_gd"], kappa_tm=kw["kappa_tm"], t_base=kw["t_base"],
                         draw_base=kw["draw_base"], w_poisson=kw["w_poisson"],
                         w_elo=1.0 - kw["w_poisson"], n_strata=S)


def calibrate(conn, cutoff: str, S: int = 64, B: int = 5000, seed: int = 12345) -> dict:
    train = load_rows(conn, before=cutoff)
    test = load_rows(conn, after=cutoff)
    if not train or not test:
        return {"erro": "treino/teste vazio", "n_train": len(train), "n_test": len(test)}
    st_tr = precompute_strata(train, S)
    st_te = precompute_strata(test, S)

    placeholder = PredictParams(n_strata=S)
    best = None
    for combo in itertools.product(*GRID.values()):
        p = _params(dict(zip(GRID.keys(), combo)), S)
        b = mean_brier(train, st_tr, p)
        if best is None or b < best[0]:
            best = (b, p, dict(zip(GRID.keys(), combo)))
    b_train, best_p, best_kw = best

    # TESTE (held-out): placeholder vs calibrado, pareado por jogo
    deltas, sc, sp = [], 0.0, 0.0
    for (dr, _s, o), st in zip(test, st_te):
        cal = _triple(dr, st, best_p)
        pl = _triple(dr, st, placeholder)
        bc = brier({"p_v": cal[0], "p_e": cal[1], "p_d": cal[2]}, o)
        bp = brier({"p_v": pl[0], "p_e": pl[1], "p_d": pl[2]}, o)
        sc += bc; sp += bp; deltas.append(bp - bc)
    g = gate(deltas, B=B, seed=seed)
    n = len(test)
    return {
        "cutoff": cutoff, "n_train": len(train), "n_test": n, "best": best_kw,
        "brier_train_placeholder": mean_brier(train, st_tr, placeholder),
        "brier_train_calib": b_train,
        "brier_test_placeholder": sp / n, "brier_test_calib": sc / n,
        "ganho_test": g["mean"], "ic_lo": g["ic_lo"], "ic_hi": g["ic_hi"],
        "adota": g["keep"],
    }


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Calibra coeficientes (treino) e valida (teste).")
    p.add_argument("--db", default=str(DEFAULT_DB))
    p.add_argument("--cutoff", default="2018-01-01", help="data de corte treino/teste (ISO)")
    args = p.parse_args(argv)
    conn = db.connect(args.db)
    r = calibrate(conn, args.cutoff)
    conn.close()
    if r.get("erro"):
        print("erro:", r["erro"], r); return 1
    print(f"cutoff {r['cutoff']} | treino n={r['n_train']} | teste n={r['n_test']}")
    print(f"melhores coeficientes: {r['best']}")
    print(f"Brier treino: placeholder {r['brier_train_placeholder']:.4f} -> calibrado {r['brier_train_calib']:.4f}")
    print(f"Brier TESTE:  placeholder {r['brier_test_placeholder']:.4f} -> calibrado {r['brier_test_calib']:.4f}")
    print(f"ganho no teste = {r['ganho_test']:+.4f}  IC95 [{r['ic_lo']:+.4f}, {r['ic_hi']:+.4f}]")
    print(f"ADOTAR? (IC não cruza 0) -> {'SIM' if r['adota'] else 'NÃO (ganho não significativo)'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
