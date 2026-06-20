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

MODEL_VERSION = "baseline-v0.4-ad"

# Curva de empate empírica C1 (P_E por faixa de |dr|), CONGELADA do martj42 (n=49.423,
# dr pré-jogo de match_ratings). Substitui o proxy fechado que a auditoria v5 proibiu
# (camada1-revisao-v5 §1 V6 / camada1-apendice-formas-v5 §3). Reconstruível por
# build_draw_curve(); fallback p/ o proxy se use_empirical_draw=False.
# CAVEAT (audit N-B): esta tabela foi ajustada IN-SAMPLE (conjunto inteiro, inclui os jogos
# avaliados no backtest) — leve vazamento na componente P(E). Para um backtest 100% PIT,
# rebuild com build_draw_curve(conn, before_date=<cutoff>). Efeito de 2ª ordem.
DRAW_CURVE = ((20, 0.2847), (60, 0.2710), (100, 0.2629), (140, 0.2567), (180, 0.2451),
              (225, 0.2303), (275, 0.2091), (350, 0.1644), (450, 0.1208), (600, 0.0554))


@dataclass(frozen=True)
class PredictParams:
    theta_gd: float = 0.45        # GD = θ·dr/100 [a calibrar]
    # Forma do saldo f(dr) — candidato P-D (audit): "linear" (default, validado) ou "sat"
    # (saturante GD_max·tanh(dr/escala)). A linear faz λ_B<0 no tail (dr≳740) e o piso passa a
    # MODELAR; a saturante mantém λ_B>0 sem clamp. Default inalterado → precisa do PORTÃO p/ adotar.
    gd_form: str = "linear"
    gd_max: float = 3.0           # asíntota do saldo (saturante) [a calibrar]
    gd_scale: float = 667.0       # escala de dr (inclinação em 0 ≈ θ/100; casa a linear em |dr|≲300)
    t_base: float = 2.6           # T_m = T_base + κ·|dr|/100 [a calibrar]
    kappa_tm: float = 0.10
    lambda_min: float = 0.15      # piso de λ (regularização honesta)
    max_goals: int = 10
    draw_base: float = 0.27       # curva de empate C1 (proxy [a calibrar]): ~0.27 em dr=0
    draw_scale: float = 510.0     #   -> ~0.15 em |dr|=300
    draw_eps: float = 0.02        # folga do cap de coerência
    use_empirical_draw: bool = True   # C1 empírica (DRAW_CURVE); False -> proxy fechado
    draw_curve: tuple = DRAW_CURVE    # tabela P_E(|dr|) congelada
    n_strata: int = 200           # propagação determinística
    w_poisson: float = 0.56       # pesos sem odds (backtest histórico)
    w_elo: float = 0.44
    w_ad: float = 0.30            # perna ataque/defesa não-Elo (P-A) — ADOTADA v0.4 (portão +0.0039,
                                  #   IC[+0.0028,+0.0051]); fonte independente de gols (corr ~0.95 vs 0.997)
    clamp_lo: float = 0.02
    clamp_hi: float = 0.96
    eps_ko: float = 0.03         # mata-mata: leve vantagem do + forte no desempate [a calibrar]


def gd_of(dr: float, p: PredictParams) -> float:
    # forma saturante (candidato P-D): mantém λ_B>0 no tail sem depender do piso. Default linear
    # (validado). tanh(dr/escala)·GD_max ≈ θ·dr/100 perto de 0 (onde há dados) e satura no tail.
    if getattr(p, "gd_form", "linear") == "sat":
        return p.gd_max * math.tanh(dr / p.gd_scale)
    return p.theta_gd * dr / 100.0


def tm_of(dr: float, p: PredictParams, estilo_a: float = 1.0, estilo_b: float = 1.0,
          heat_factor: float = 1.0) -> float:
    return (p.t_base + p.kappa_tm * abs(dr) / 100.0) * estilo_a * estilo_b * heat_factor


def lambdas(dr: float, p: PredictParams, estilo_a: float = 1.0, estilo_b: float = 1.0,
            gd_alt: float = 0.0, heat_factor: float = 1.0,
            datk_a: float = 0.0, datk_b: float = 0.0):
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
    # δ_ata (D-53): desfalque OFENSIVO corta o λ do PRÓPRIO time (contrato §8 passo 6:
    # λ_T = λ_T0·(1−δ_ata_T)) e NÃO infla o rival. Antes a Camada 3 roteava o ataque pelo
    # canal de GD (soma-zero em λ), o que SUBIA o λ do adversário — invertia a regra do
    # contrato (audit N-A, verificado: rival +13%). Corte multiplicativo + piso simples (não
    # reconserva T_m: uma ausência ofensiva DEVE reduzir o total daquele time).
    if datk_a:
        la = max(lmin, la * (1.0 - datk_a))
    if datk_b:
        lb = max(lmin, lb * (1.0 - datk_b))
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
    """P(empate) pela curva empírica C1 (interpolação linear em |dr|).

    Usa a tabela congelada do martj42 (DRAW_CURVE) — a forma do contrato
    (camada1-apendice-formas-v5 §3). Fallback p/ o proxy fechado se desativada.
    """
    if getattr(p, "use_empirical_draw", True) and p.draw_curve:
        x = abs(dr)
        pts = p.draw_curve
        if x <= pts[0][0]:
            return pts[0][1]
        if x >= pts[-1][0]:
            return pts[-1][1]
        for k in range(1, len(pts)):
            if x <= pts[k][0]:
                x0, y0 = pts[k - 1]
                x1, y1 = pts[k]
                t = (x - x0) / (x1 - x0) if x1 > x0 else 0.0
                return y0 + t * (y1 - y0)
        return pts[-1][1]
    return p.draw_base * math.exp(-abs(dr) / p.draw_scale)


def build_draw_curve(conn, edges=(0, 40, 80, 120, 160, 200, 250, 300, 400, 500),
                     before_date=None):
    """Reconstrói a curva empírica P_E(|dr|) do match_ratings (dr pré-jogo). Transparência/rebuild.

    CAVEAT (audit N-B): a `DRAW_CURVE` congelada no módulo foi ajustada no conjunto INTEIRO,
    inclusive nos jogos depois avaliados no backtest — um leve vazamento in-sample na
    componente P(E) (o Elo e a forma são point-in-time; a curva de empate não era). Para um
    backtest 100% PIT, passe `before_date` (cutoff do treino) e congele a curva resultante; o
    ganho passa a ser fora de amostra. Efeito de 2ª ordem (a curva tem poucos g.l.), mas a
    ressalva fica declarada.
    """
    import bisect
    if before_date:
        rows = conn.execute("SELECT mr.dr, m.home_score, m.away_score "
                            "FROM match_ratings mr JOIN matches m USING (match_id) "
                            "WHERE m.date < ?", (before_date,)).fetchall()
    else:
        rows = conn.execute("SELECT mr.dr, m.home_score, m.away_score "
                            "FROM match_ratings mr JOIN matches m USING (match_id)").fetchall()
    agg = [[0, 0] for _ in range(len(edges))]
    for dr, hs, a in rows:
        k = min(bisect.bisect_right(edges, abs(dr)) - 1, len(edges) - 1)
        agg[k][0] += 1
        agg[k][1] += 1 if hs == a else 0
    out = []
    for k in range(len(edges)):
        n, d = agg[k]
        if n == 0:
            continue
        center = (edges[k] + edges[k + 1]) / 2 if k + 1 < len(edges) else edges[k] + 100
        out.append((center, round(d / n, 4), n))
    return out


_STD_Q_CACHE: dict = {}


def _std_quantiles(S: int):
    """Quantis da Normal padrão (s+0.5)/S, calculados 1x e cacheados por S.

    Identidade exata: NormalDist(mu,sd).inv_cdf(q) = mu + sd*NormalDist(0,1).inv_cdf(q).
    Evita ~S chamadas caras de inv_cdf POR JOGO (só S no total). Resultado idêntico.
    """
    q = _STD_Q_CACHE.get(S)
    if q is None:
        snd = NormalDist(0.0, 1.0)
        q = [snd.inv_cdf((s + 0.5) / S) for s in range(S)]
        _STD_Q_CACHE[S] = q
    return q


def ved_from_elo(dr_s: float, p: PredictParams):
    """V/E/D de UMA amostra dr_s pela leitura Elo-direto (we + curva C1 + cap de coerência).

    NÚCLEO ÚNICO (D-43): reusado por `elo_direct_read`, `backtest_harness.elo_baseline_read`
    e `calibrate._elo_read` — antes a mesma fórmula vivia copiada em 3 lugares (risco de
    divergirem). Matematicamente idêntico ao código anterior (verificado em grade).
    """
    w = we(dr_s)
    m = min(w, 1.0 - w)
    pe = max(0.0, min(draw_prob(dr_s, p), 2.0 * m - p.draw_eps))
    pv = w - pe / 2.0
    return pv, pe, 1.0 - pv - pe


def elo_direct_read(dr: float, sigma_dr: float, p: PredictParams) -> dict:
    """Leitura Elo-direto PROPAGADA (estratos determinísticos de igual probabilidade).

    Cap por amostra garante P(V),P(D) ∈ [0,1]. Banda = percentis 16/84 de P(V).
    """
    sigma = max(sigma_dr, 1e-6)
    S = p.n_strata
    zq = _std_quantiles(S)
    pvs = []
    spv = spe = spd = 0.0
    for z in zq:
        dr_s = dr + sigma * z
        pv, pe, pd = ved_from_elo(dr_s, p)
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


def knockout_advance(p_v: float, p_e: float, p_d: float, dr: float,
                     p: PredictParams = PredictParams(), eps: float = None) -> dict:
    """Probabilidade de AVANÇAR num jogo de mata-mata (contrato §3.2).

    Se empatar no tempo normal, vai a prorrogação/pênaltis. O desempate é ~moeda,
    com leve vantagem do mais forte:
        avanço_A = P(V) + P(E)·(0.5 + ε·sinal(dr))
        avanço_B = P(D) + P(E)·(0.5 − ε·sinal(dr))
    ε≈0.03 [a calibrar]. É uma RELEITURA do 1X2 do ensemble (não um novo modelo, como
    os mercados D-21) — soma 1 por construção; não altera as predições armazenadas.
    Simplificação declarada: prorrogação e pênaltis entram juntos no termo de empate
    (ε absorve a pequena vantagem do mais forte no tempo extra + disputa).
    """
    e = p.eps_ko if eps is None else eps
    sign = (dr > 0) - (dr < 0)              # sinal(dr) ∈ {-1, 0, +1}
    share_a = min(1.0, max(0.0, 0.5 + e * sign))   # fração do empate que vai p/ A
    adv_a = p_v + p_e * share_a
    adv_b = p_d + p_e * (1.0 - share_a)    # 1−share_a garante soma exata = 1
    return {"adv_a": adv_a, "adv_b": adv_b, "draw_share_a": share_a, "eps": e}


def predict(dr: float, sigma_dr: float, p: PredictParams = PredictParams(),
            estilo_a: float = 1.0, estilo_b: float = 1.0, gd_alt: float = 0.0,
            heat_factor: float = 1.0, datk_a: float = 0.0, datk_b: float = 0.0,
            ad_ved=None) -> dict:
    la, lb = lambdas(dr, p, estilo_a, estilo_b, gd_alt=gd_alt, heat_factor=heat_factor,
                     datk_a=datk_a, datk_b=datk_b)
    pois = poisson_reads(la, lb, p.max_goals)
    elo = elo_direct_read(dr, sigma_dr, p)
    cp = _clamp_norm((pois["pv"], pois["pe"], pois["pd"]), p.clamp_lo, p.clamp_hi)
    ce = _clamp_norm((elo["pv"], elo["pe"], elo["pd"]), p.clamp_lo, p.clamp_hi)
    # ensemble: Poisson + Elo (+ AD não-Elo, P-A — só quando w_ad>0 E ad_ved dado). A
    # normalização por wsum mantém o caso w_ad=0 IDÊNTICO ao anterior (wsum=0.56+0.44=1.0).
    ws = p.w_poisson + p.w_elo
    if ad_ved is not None and p.w_ad > 0:
        ca = _clamp_norm(ad_ved, p.clamp_lo, p.clamp_hi)
        ws += p.w_ad
        mix = [(p.w_poisson * cp[i] + p.w_elo * ce[i] + p.w_ad * ca[i]) / ws for i in range(3)]
    else:
        mix = [(p.w_poisson * cp[i] + p.w_elo * ce[i]) / ws for i in range(3)]
    final = _clamp_norm(mix, p.clamp_lo, p.clamp_hi)
    ko = knockout_advance(final[0], final[1], final[2], dr, p)
    return {
        "p_v": final[0], "p_e": final[1], "p_d": final[2],
        "band_pv_lo": elo["band_lo"], "band_pv_hi": elo["band_hi"],
        "lambda_a": la, "lambda_b": lb,
        "p_over25": pois["over25"], "p_btts": pois["btts"],
        "knockout": ko,
        "poisson": pois, "elo": elo,
    }


def run(conn, params: PredictParams = PredictParams()) -> dict:
    from .factors import gd_alt  # termo puro (arquitetura: ciclo predictor↔altitude quebrado)
    db.init_schema(conn)
    if conn.execute("SELECT COUNT(*) FROM match_features").fetchone()[0] == 0:
        raise RuntimeError("match_features vazio — rode features_pit.run primeiro.")
    ad_pit = None
    if params.w_ad > 0:                       # perna AD não-Elo (P-A): só quando ligada (w_ad>0)
        from .attack_defense import run_pit   # puro (sem ciclo); λ PRÉ-jogo (PIT)
        ad_pit = run_pit(conn)
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
        ad_ved = None
        if ad_pit is not None:
            lah, lbh = ad_pit.get(r["match_id"], (None, None))
            if lah is not None:
                ar = poisson_reads(lah, lbh, params.max_goals)
                ad_ved = (ar["pv"], ar["pe"], ar["pd"])
        pr = predict(r["dr_adj"], r["sigma_dr"], params, gd_alt=ga, ad_ved=ad_ved)
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
