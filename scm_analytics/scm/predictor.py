"""predictor: features -> P(V/E/D)+banda, λ, over2.5, BTTS, placares (baseline congelado).

Lê `match_features` (dr_adj, σ_dr) -> GD=f(dr), T_m=g(dr)·estilo -> matriz Poisson +
leitura Elo-direto PROPAGADA -> ensemble (sem mercado no histórico). Grava `predictions`.

Formas/coeficientes: `camada1-apendice-formas-v5.md` (tudo [a calibrar]).
Propagação DETERMINÍSTICA por estratos de igual probabilidade (reprodutível; sem RNG).
over/BTTS/placares são Poisson-condicionais (achado A1). Coerência [0,1] pela curva de
empate restrita (cap por amostra).
"""
from __future__ import annotations

import argparse
import math
from dataclasses import dataclass
from pathlib import Path
from statistics import NormalDist
from typing import Optional

from . import db
from .elo_engine import we
from .ingest import DEFAULT_DB

MODEL_VERSION = "baseline-v0.1"


@dataclass(frozen=True)
class PredictParams:
    theta_gd: float = 0.45        # GD = θ·dr/100 [a calibrar]
    t_base: float = 2.6           # T_m = T_base + κ·|dr|/100 [a calibrar]
    kappa_tm: float = 0.10
    lambda_min: float = 0.15      # piso de λ (regularização honesta)
    max_goals: int = 10
    draw_base: float = 0.27       # curva de empate C1 (proxy [a calibrar]): ~0.27 em dr=0
    draw_scale: float = 510.0     #   -> ~0.15 em |dr|=300
    draw_eps: float = 0.02        # folga do cap de coerência
    n_strata: int = 200           # propagação determinística
    w_poisson: float = 0.56       # pesos sem odds (backtest histórico)
    w_elo: float = 0.44
    clamp_lo: float = 0.02
    clamp_hi: float = 0.96


def gd_of(dr: float, p: PredictParams) -> float:
    return p.theta_gd * dr / 100.0


def tm_of(dr: float, p: PredictParams, estilo_a: float = 1.0, estilo_b: float = 1.0) -> float:
    return (p.t_base + p.kappa_tm * abs(dr) / 100.0) * estilo_a * estilo_b


def lambdas(dr: float, p: PredictParams, estilo_a: float = 1.0, estilo_b: float = 1.0):
    gd = gd_of(dr, p)
    tm = tm_of(dr, p, estilo_a, estilo_b)
    la = max(p.lambda_min, (tm + gd) / 2.0)
    lb = max(p.lambda_min, (tm - gd) / 2.0)
    return la, lb


def _pois(k: int, lam: float) -> float:
    return math.exp(-lam) * lam ** k / math.factorial(k)


def poisson_reads(lam_a: float, lam_b: float, max_goals: int = 10) -> dict:
    """V/E/D, over2.5, BTTS, top-5 placares — tudo da matriz Poisson (Poisson-condicional)."""
    pv = pe = pd = over = 0.0
    cells = []
    pa = [_pois(i, lam_a) for i in range(max_goals + 1)]
    pb = [_pois(j, lam_b) for j in range(max_goals + 1)]
    for i in range(max_goals + 1):
        for j in range(max_goals + 1):
            pij = pa[i] * pb[j]
            cells.append(((i, j), pij))
            if i > j:
                pv += pij
            elif i == j:
                pe += pij
            else:
                pd += pij
            if i + j >= 3:
                over += pij
    btts = (1 - math.exp(-lam_a)) * (1 - math.exp(-lam_b))
    cells.sort(key=lambda c: -c[1])
    top5 = [(f"{i}x{j}", round(p, 4)) for (i, j), p in cells[:5]]
    return {"pv": pv, "pe": pe, "pd": pd, "over25": over, "btts": btts, "top5": top5}


def draw_prob(dr: float, p: PredictParams) -> float:
    """P(empate) empírico-proxy (C1): decai com |dr|. [a calibrar] vs martj42."""
    return p.draw_base * math.exp(-abs(dr) / p.draw_scale)


def elo_direct_read(dr: float, sigma_dr: float, p: PredictParams) -> dict:
    """Leitura Elo-direto PROPAGADA (estratos determinísticos de igual probabilidade).

    Cap por amostra garante P(V),P(D) ∈ [0,1]. Banda = percentis 16/84 de P(V).
    """
    nd = NormalDist(dr, max(sigma_dr, 1e-6))
    S = p.n_strata
    pvs = []
    spv = spe = spd = 0.0
    for s in range(S):
        dr_s = nd.inv_cdf((s + 0.5) / S)
        w = we(dr_s)
        m = min(w, 1.0 - w)
        pe = max(0.0, min(draw_prob(dr_s, p), 2.0 * m - p.draw_eps))
        pv = w - pe / 2.0
        pd = 1.0 - pv - pe
        pvs.append(pv)
        spv += pv
        spe += pe
        spd += pd
    pvs.sort()
    return {
        "pv": spv / S, "pe": spe / S, "pd": spd / S,
        "band_lo": pvs[int(0.16 * S)], "band_hi": pvs[int(0.84 * S)],
    }


def _clamp_norm(triple, lo, hi):
    v = [min(hi, max(lo, x)) for x in triple]
    s = sum(v)
    return [x / s for x in v]


def predict(dr: float, sigma_dr: float, p: PredictParams = PredictParams(),
            estilo_a: float = 1.0, estilo_b: float = 1.0) -> dict:
    la, lb = lambdas(dr, p, estilo_a, estilo_b)
    pois = poisson_reads(la, lb, p.max_goals)
    elo = elo_direct_read(dr, sigma_dr, p)
    cp = _clamp_norm((pois["pv"], pois["pe"], pois["pd"]), p.clamp_lo, p.clamp_hi)
    ce = _clamp_norm((elo["pv"], elo["pe"], elo["pd"]), p.clamp_lo, p.clamp_hi)
    mix = [p.w_poisson * cp[i] + p.w_elo * ce[i] for i in range(3)]
    final = _clamp_norm(mix, p.clamp_lo, p.clamp_hi)
    return {
        "p_v": final[0], "p_e": final[1], "p_d": final[2],
        "band_pv_lo": elo["band_lo"], "band_pv_hi": elo["band_hi"],
        "lambda_a": la, "lambda_b": lb,
        "p_over25": pois["over25"], "p_btts": pois["btts"],
        "poisson": pois, "elo": elo,
    }


def run(conn, params: PredictParams = PredictParams()) -> dict:
    db.init_schema(conn)
    if conn.execute("SELECT COUNT(*) FROM match_features").fetchone()[0] == 0:
        raise RuntimeError("match_features vazio — rode features_pit.run primeiro.")
    conn.execute("DELETE FROM predictions WHERE versao_modelo = ?", (MODEL_VERSION,))
    rows = conn.execute("SELECT match_id, dr_adj, sigma_dr FROM match_features").fetchall()
    n = 0
    for r in rows:
        pr = predict(r["dr_adj"], r["sigma_dr"], params)
        conn.execute(
            """INSERT OR REPLACE INTO predictions
               (match_id, versao_modelo, p_v, p_e, p_d, band_pv_lo, band_pv_hi,
                lambda_a, lambda_b, p_over25, p_btts)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (r["match_id"], MODEL_VERSION, pr["p_v"], pr["p_e"], pr["p_d"],
             pr["band_pv_lo"], pr["band_pv_hi"], pr["lambda_a"], pr["lambda_b"],
             pr["p_over25"], pr["p_btts"]),
        )
        n += 1
    conn.commit()
    return {"predictions": n}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Gera previsões (baseline) a partir das features.")
    p.add_argument("--db", default=str(DEFAULT_DB))
    args = p.parse_args(argv)
    if not Path(args.db).exists():
        print(f"[erro] SQLite não encontrado: {args.db}. Rode ingest + elo_engine + features_pit.")
        return 1
    conn = db.connect(args.db)
    stats = run(conn)
    print(f"previsões geradas: {stats['predictions']} jogos (versão {MODEL_VERSION})")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
