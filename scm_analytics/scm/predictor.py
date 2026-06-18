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

MODEL_VERSION = "baseline-v0.2.1-altitude"


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


def tm_of(dr: float, p: PredictParams, estilo_a: float = 1.0, estilo_b: float = 1.0,
          heat_factor: float = 1.0) -> float:
    return (p.t_base + p.kappa_tm * abs(dr) / 100.0) * estilo_a * estilo_b * heat_factor


def lambdas(dr: float, p: PredictParams, estilo_a: float = 1.0, estilo_b: float = 1.0,
            gd_alt: float = 0.0, heat_factor: float = 1.0):
    gd = gd_of(dr, p) + gd_alt
    tm = tm_of(dr, p, estilo_a, estilo_b, heat_factor=heat_factor)
    la = (tm + gd) / 2.0
    lb = (tm - gd) / 2.0
    # piso de λ CONSERVANDO o total T_m (P01): se o piso eleva o azarão acima de
    # (tm−λ), desconta do favorito p/ manter λ_A+λ_B = T_m sempre que tm ≥ 2·λ_min.
    lmin = p.lambda_min
    if lb < lmin:
        lb = lmin
        la = max(lmin, tm - lb)
    elif la < lmin:
        la = lmin
        lb = max(lmin, tm - la)
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
            estilo_a: float = 1.0, estilo_b: float = 1.0, gd_alt: float = 0.0,
            heat_factor: float = 1.0) -> dict:
    la, lb = lambdas(dr, p, estilo_a, estilo_b, gd_alt=gd_alt, heat_factor=heat_factor)
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
    from .altitude import gd_alt  # import tardio (evita ciclo predictor<->altitude)
    db.init_schema(conn)
    if conn.execute("SELECT COUNT(*) FROM match_features").fetchone()[0] == 0:
        raise RuntimeError("match_features vazio — rode features_pit.run primeiro.")
    conn.execute("DELETE FROM predictions WHERE versao_modelo = ?", (MODEL_VERSION,))
    rows = conn.execute(
        """SELECT mf.match_id, mf.dr_adj, mf.sigma_dr, m.city,
                  th.name AS home, ta.name AS away
           FROM match_features mf JOIN matches m USING (match_id)
           JOIN teams th ON th.team_id = m.home_team_id
           JOIN teams ta ON ta.team_id = m.away_team_id"""
    ).fetchall()
    n = 0
    for r in rows:
        ga = gd_alt(r["city"], r["home"], r["away"])
        pr = predict(r["dr_adj"], r["sigma_dr"], params, gd_alt=ga)
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


def markets(lam_a: float, lam_b: float, max_goals: int = 10) -> dict:
    """Mercados derivados da MESMA matriz Poisson (nada novo no modelo).

    over/under (0.5–4.5), totais por time, não-sofrer-gol (clean sheet),
    dupla chance, handicap (vencer por 2+), distribuição do total e
    'quem marca primeiro' via Poisson concorrente:
        P(A 1º) = λ_A/(λ_A+λ_B) · (1 − P(0 gol));  P(0 gol) = e^-(λ_A+λ_B).
    O 'quem marca 1º' assume taxa de gols constante no tempo (aproximação).
    """
    pa = [_pois(i, lam_a) for i in range(max_goals + 1)]
    pb = [_pois(j, lam_b) for j in range(max_goals + 1)]
    total = [0.0] * (2 * max_goals + 1)
    hcap_a2 = hcap_b2 = 0.0
    for i in range(max_goals + 1):
        for j in range(max_goals + 1):
            pij = pa[i] * pb[j]
            total[i + j] += pij
            if i - j >= 2:
                hcap_a2 += pij
            elif j - i >= 2:
                hcap_b2 += pij
    pv = sum(pa[i] * pb[j] for i in range(max_goals + 1) for j in range(i))            # i>j
    pe = sum(pa[k] * pb[k] for k in range(max_goals + 1))
    pd = max(0.0, 1.0 - pv - pe)

    def over(line):
        return sum(total[k] for k in range(len(total)) if k > line)

    lines = (0.5, 1.5, 2.5, 3.5, 4.5)
    a0, b0 = pa[0], pb[0]
    s = lam_a + lam_b
    no_goal = math.exp(-s)
    first_a = (lam_a / s) * (1 - no_goal) if s > 1e-9 else 0.0
    first_b = (lam_b / s) * (1 - no_goal) if s > 1e-9 else 0.0
    tg = [(str(k), total[k]) for k in range(5)] + [("5+", sum(total[5:]))]
    return {
        "over": {str(l): over(l) for l in lines},
        "under": {str(l): 1.0 - over(l) for l in lines},
        "btts": (1 - a0) * (1 - b0),
        "team_a_over": {"0.5": 1 - a0, "1.5": max(0.0, 1 - a0 - pa[1])},
        "team_b_over": {"0.5": 1 - b0, "1.5": max(0.0, 1 - b0 - pb[1])},
        "clean_sheet_a": b0,   # A não sofre gol  = B faz 0
        "clean_sheet_b": a0,   # B não sofre gol  = A faz 0
        "double_chance": {"1X": pv + pe, "12": pv + pd, "X2": pe + pd},
        "handicap": {"a_-1.5": hcap_a2, "b_-1.5": hcap_b2},   # vencer por 2+ gols
        "first_to_score": {"a": first_a, "b": first_b, "none": no_goal},
        "total_goals": tg,
    }
