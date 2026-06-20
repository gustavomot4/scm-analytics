"""predict_match — a porta da frente: prevê UM confronto específico.

Usa o Elo atual (`ratings_current`) das duas seleções + mando/altitude opcionais e o
predictor v0.2 (com altitude). Saída: P(V/E/D)+banda, λ, um leque de mercados (over/under,
totais por time, não-sofrer-gol, dupla chance, handicap, quem marca 1º), placares
prováveis e CONFIANÇA ancorada na confiabilidade medida no backtest.

dr ALINHADO AO BACKTEST (D-34): aplica a forma recente (forma_home − forma_away) ao dr,
igual ao `features_pit.dr_adj`. Confiança usa σ_R ESCALADO por consistência (D-35).

Probabilidade, não certeza — não é recomendação de aposta.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from . import db
from .predictor import PredictParams, predict, markets, MODEL_VERSION
from .altitude import gd_alt
from .ingest import DEFAULT_DB

SIGMA_AJUSTE_DEFAULT = 40.0   # incerteza de forma/escalação p/ jogo futuro (entra na banda)
SIGMA_R_REF = 200.0           # escala de maturidade do rating p/ a confiança [a calibrar]


def _team(conn, name):
    return conn.execute(
        """SELECT t.team_id, t.name, r.elo, r.sigma_r, r.n_games, r.provisional
           FROM ratings_current r JOIN teams t USING (team_id)
           WHERE lower(t.name) = lower(?)""", (name,)).fetchone()


def _suggest(conn, name):
    import difflib
    names = [r[0] for r in conn.execute(
        "SELECT t.name FROM ratings_current r JOIN teams t USING (team_id)")]
    close = difflib.get_close_matches(name or "", names, n=6, cutoff=0.5)
    if close:
        return close
    like = f"%{(name or '')[:3]}%"
    return [r[0] for r in conn.execute(
        "SELECT t.name FROM ratings_current r JOIN teams t USING (team_id) "
        "WHERE t.name LIKE ? ORDER BY r.elo DESC LIMIT 6", (like,))]


def _reliab_from_meta(conn):
    """Curva reliab(p_max) gravada por calibrate_confidence; None → usa p_max (modelo calibrado)."""
    try:
        row = conn.execute("SELECT value FROM meta WHERE key='confidence_reliab'").fetchone()
    except Exception:
        return None, None
    if not row or not row[0]:
        return None, None
    data = json.loads(row[0])
    if isinstance(data, dict):
        model, curve = data.get("model"), data.get("curve", [])
    else:
        model, curve = None, data          # formato antigo (sem versão)
    pts = sorted((float(p), float(h)) for p, h in curve)
    if len(pts) < 2:
        return None, model

    def f(pm):
        if pm <= pts[0][0]:
            return pts[0][1]
        if pm >= pts[-1][0]:
            return pts[-1][1]
        for k in range(1, len(pts)):
            if pm <= pts[k][0]:
                (x0, y0), (x1, y1) = pts[k - 1], pts[k]
                t = (pm - x0) / (x1 - x0) if x1 > x0 else 0.0
                return y0 + t * (y1 - y0)
        return pts[-1][1]
    return f, model


def maturity(sigma_r_avg, sigma_r_ref=SIGMA_R_REF):
    """Quanto confiar no rating: cai com a incerteza média σ_R (provisório → menor)."""
    return 1.0 - min(0.5, sigma_r_avg / sigma_r_ref)


def confidence(p_v, p_e, p_d, sigma_r_avg, reliab=None, sigma_r_ref=SIGMA_R_REF):
    """Confiança 0–100 = confiabilidade medida da previsão × maturidade do rating.

    reliab(p_max): curva empírica de acerto do backtest (calibrate_confidence). Sem ela,
    usa p_max — honesto porque o reliability diagram mostrou o modelo bem calibrado.
    Não tem mais teto artificial: massacre entre times maduros → confiança alta de verdade.
    """
    p_max = max(p_v, p_e, p_d)
    rel = reliab(p_max) if reliab else p_max
    rel = min(1.0, max(0.0, rel))
    return 100.0 * rel * maturity(sigma_r_avg, sigma_r_ref)


def conf_label(c):
    return "alta" if c >= 60 else ("média" if c >= 40 else "baixa")


def predict_match(conn, home, away, mando=0.0, city=None, sigma_ajuste=None, usar_estilo=False,
                  desfalques=None, odds=None):
    a = _team(conn, home)
    b = _team(conn, away)
    if not a or not b:
        miss = home if not a else away
        return {"erro": "time não encontrado", "faltando": miss, "sugestoes": _suggest(conn, miss)}
    # σ informativo: σ_ajuste vem da DISPERSÃO DE FORMA real de cada seleção (não um valor
    # fixo); σ_R é escalado pela (in)consistência recente (vol_mult). Assim a banda e a
    # confiança variam por confronto. banda_mando entra quando há mando (anfitrião).
    from .features_pit import team_form, vol_mult, FeatureParams
    from datetime import date as _date, timedelta as _td
    fp = FeatureParams()
    # data de referência = dia seguinte ao último jogo da base (recência sensata;
    # uma data distante no futuro zeraria os pesos 0.9^meses -> desvio=0 espúrio).
    _ref = conn.execute("SELECT MAX(date) FROM matches").fetchone()[0]
    try:
        ref_date = (_date.fromisoformat(_ref) + _td(days=1)).isoformat()
    except (TypeError, ValueError):
        ref_date = "2027-01-01"
    form_a, dev_a, n_fa = team_form(conn, a["team_id"], ref_date, fp)
    form_b, dev_b, n_fb = team_form(conn, b["team_id"], ref_date, fp)
    # dr ALINHADO AO BACKTEST (D-34): features_pit grava dr_adj = dr_elo + (forma_home −
    # forma_away). A porta da frente agora aplica a MESMA forma recente ao dr — antes o ponto
    # de forma era DESCARTADO (só a dispersão entrava em σ), então a previsão entregue diferia
    # do modelo validado no backtest. forma já vem capada em ±form_cap (contrato).
    dr = a["elo"] - b["elo"] + (form_a - form_b) + mando
    if sigma_ajuste is None:
        sa_a = fp.sigma_ajuste_c * dev_a
        sa_b = fp.sigma_ajuste_c * dev_b
    else:
        sa_a = sa_b = float(sigma_ajuste)
    sr_a = a["sigma_r"] * vol_mult(dev_a, n_fa)
    sr_b = b["sigma_r"] * vol_mult(dev_b, n_fb)
    banda_mando2 = 20.0 ** 2 if mando else 0.0
    sigma_dr = math.sqrt(sr_a ** 2 + sr_b ** 2 + sa_a ** 2 + sa_b ** 2 + banda_mando2)
    ga = gd_alt(city, a["name"], b["name"]) if city else 0.0
    # Camada 3 (D-41): desfalques direcionais — ataque corta GD; defesa/goleiro mexe no dr.
    dr_desf = gd_desf = 0.0
    if desfalques:
        from .desfalques import match_deltas
        dr_desf, gd_desf = match_deltas(desfalques.get("home", []), desfalques.get("away", []))
        dr += dr_desf
        ga += gd_desf
    ea = eb = 1.0
    if usar_estilo:
        from .estilo import team_styles
        st, _ = team_styles(conn)
        ea, eb = st.get(a["team_id"], 1.0), st.get(b["team_id"], 1.0)
    pr = predict(dr, sigma_dr, PredictParams(), estilo_a=ea, estilo_b=eb, gd_alt=ga)
    # 3ª perna do ensemble (D-44): se houver odds, mistura o 1X2 com o mercado (peso 0.20,
    # contrato §3.8). odds = (odd_casa, odd_empate, odd_fora) decimais. Mercados λ ficam do modelo.
    mercado = None
    if odds:
        from .odds import implied_probs, blend as _blend
        mercado = implied_probs(*odds)
        bl = _blend({"p_v": pr["p_v"], "p_e": pr["p_e"], "p_d": pr["p_d"]}, mercado)
        pr["p_v"], pr["p_e"], pr["p_d"] = bl["p_v"], bl["p_e"], bl["p_d"]
    # banda recentrada no ponto do ensemble (largura = incerteza propagada da leitura Elo-direto)
    hw = (pr["band_pv_hi"] - pr["band_pv_lo"]) / 2.0
    pr["band_pv_lo"] = max(0.01, pr["p_v"] - hw)
    pr["band_pv_hi"] = min(0.99, pr["p_v"] + hw)
    # confiança usa o σ_R ESCALADO pela consistência recente (sr_a/sr_b já têm vol_mult),
    # não o σ_R bruto (D-35): antes a "maturidade" era ~0,8 fixa p/ toda seleção madura
    # (σ_R satura ~40), tornando a confiança função quase pura de p_max.
    sigma_r_avg = (sr_a + sr_b) / 2.0
    reliab, reliab_model = _reliab_from_meta(conn)
    conf = confidence(pr["p_v"], pr["p_e"], pr["p_d"], sigma_r_avg, reliab)
    mk = markets(pr["lambda_a"], pr["lambda_b"], PredictParams().max_goals)
    return {"home": a["name"], "away": b["name"], "elo_home": a["elo"], "elo_away": b["elo"],
            "sigma_home": a["sigma_r"], "sigma_away": b["sigma_r"], "dr": dr, "sigma_dr": sigma_dr,
            "gd_alt": ga, "dr_desf": dr_desf, "gd_desf": gd_desf, "mercado": mercado,
            "estilo_a": ea, "estilo_b": eb,
            "provisional": bool(a["provisional"] or b["provisional"]),
            "reliab_stale": bool(reliab_model and reliab_model != MODEL_VERSION),
            "conf": conf, "conf_label": conf_label(conf), "markets": mk, **pr}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Prevê um confronto (Elo atual + mando/altitude).")
    p.add_argument("home", help="time mandante / time A (favorito primeiro, por convenção)")
    p.add_argument("away", help="time visitante / time B")
    p.add_argument("--db", default=str(DEFAULT_DB))
    p.add_argument("--mando", type=float, default=0.0,
                   help="mando em Elo p/ o 1º time (0=neutro/Copa; ~40 anfitrião 2026; ~60-100 casa)")
    p.add_argument("--city", default=None, help="cidade-sede (p/ altitude; ex.: 'Mexico City', 'La Paz')")
    p.add_argument("--estilo", action="store_true",
                   help="[EXPERIMENTAL] aplica estilo (tendência de gols) — REJEITADO pelo portão (D-23); "
                        "fora do modelo padrão, só para inspeção")
    p.add_argument("--mata-mata", dest="mata_mata", action="store_true",
                   help="jogo eliminatório: mostra a probabilidade de AVANÇAR (empate→prorrog./pênaltis)")
    p.add_argument("--odds", nargs=3, type=float, default=None, metavar=("CASA", "EMPATE", "FORA"),
                   help="odds decimais de mercado (ex.: 2.10 3.30 3.60): mistura no 1X2 (peso 0.20, §3.8)")
    args = p.parse_args(argv)
    if not Path(args.db).exists():
        print(f"[erro] {args.db} não existe. Rode ingest + elo_engine antes."); return 1
    conn = db.connect(args.db)
    r = predict_match(conn, args.home, args.away, args.mando, args.city, usar_estilo=args.estilo,
                      odds=tuple(args.odds) if args.odds else None)
    conn.close()
    if r.get("erro"):
        sg = ", ".join(r["sugestoes"]) or "—"
        print(f"[erro] {r['erro']}: '{r['faltando']}'. Nomes parecidos: {sg}"); return 1
    if r["gd_alt"]:
        sede = f"{args.city} — altitude (GD_alt {r['gd_alt']:+.2f})"
    elif args.mando:
        sede = f"mando +{args.mando:.0f} p/ {r['home']}"
    else:
        sede = "neutra"
    mk = r["markets"]
    A, B = r["home"], r["away"]
    print(f"\n  {A}  vs  {B}      [sede: {sede}]")
    print(f"  Elo: {A} {r['elo_home']:.0f} (σ{r['sigma_home']:.0f}) · "
          f"{B} {r['elo_away']:.0f} (σ{r['sigma_away']:.0f})  |  dr={r['dr']:+.0f}  σ_dr={r['sigma_dr']:.0f}"
          + ("  ⚠ rating provisório" if r["provisional"] else ""))
    print(f"  1X2:  {A} {r['p_v']*100:.1f}%  ·  Empate {r['p_e']*100:.1f}%  ·  {B} {r['p_d']*100:.1f}%"
          f"      (banda {A} {r['band_pv_lo']*100:.0f}–{r['band_pv_hi']*100:.0f}%)")
    if r.get("mercado"):
        m = r["mercado"]
        print(f"  mercado (de-vig): {A} {m['p_v']*100:.1f}%  ·  Empate {m['p_e']*100:.1f}%  ·  {B} {m['p_d']*100:.1f}%"
              f"   → já misturado 20% no 1X2 acima")
    print(f"  λ: {A} {r['lambda_a']:.2f} · {B} {r['lambda_b']:.2f}"
          + (f"   |  estilo {A} {r['estilo_a']:.2f} · {B} {r['estilo_b']:.2f}" if (r.get('estilo_a',1.0)!=1.0 or r.get('estilo_b',1.0)!=1.0) else ""))
    print(f"  over/under:  0.5 {mk['over']['0.5']*100:.0f}%  ·  1.5 {mk['over']['1.5']*100:.0f}%  ·  "
          f"2.5 {mk['over']['2.5']*100:.0f}%  ·  3.5 {mk['over']['3.5']*100:.0f}%   (under = 100−over)")
    print(f"  ambos marcam: {mk['btts']*100:.0f}%   ·   não sofre: {A} {mk['clean_sheet_a']*100:.0f}% / "
          f"{B} {mk['clean_sheet_b']*100:.0f}%")
    print(f"  marca 1º:  {A} {mk['first_to_score']['a']*100:.0f}%  ·  "
          f"{B} {mk['first_to_score']['b']*100:.0f}%  ·  sem gol {mk['first_to_score']['none']*100:.0f}%")
    print(f"  dupla chance:  1X {mk['double_chance']['1X']*100:.0f}%  ·  "
          f"12 {mk['double_chance']['12']*100:.0f}%  ·  X2 {mk['double_chance']['X2']*100:.0f}%   |   "
          f"vencer por 2+:  {A} {mk['handicap']['a_-1.5']*100:.0f}%  ·  {B} {mk['handicap']['b_-1.5']*100:.0f}%")
    print("  placares: " + " · ".join(f"{s} {pp*100:.0f}%" for s, pp in r["poisson"]["top5"]))
    if args.mata_mata and r.get("knockout"):
        ko = r["knockout"]
        print(f"  MATA-MATA (avanço):  {A} {ko['adv_a']*100:.0f}%  ·  {B} {ko['adv_b']*100:.0f}%"
              f"   (empate→prorrogação/pênaltis; ε={ko['eps']:.2f})")
    if r.get("reliab_stale"):
        print("  ⚠ curva de confiança é de outra versão — rode 'python -m scm.calibrate_confidence'")
    print(f"  confiança: {r['conf']:.0f}/100 ({r['conf_label']})  ·  modelo {MODEL_VERSION}")
    print("  — probabilidade, não certeza; não é recomendação de aposta.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
