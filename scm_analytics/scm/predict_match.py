"""predict_match — a porta da frente: prevê UM confronto específico.

Usa o Elo atual (`ratings_current`) das duas seleções + mando/altitude opcionais e o
predictor v0.2 (com altitude). Saída: P(V/E/D)+banda, λ, um leque de mercados (over/under,
totais por time, não-sofrer-gol, dupla chance, handicap, quem marca 1º), placares
prováveis e CONFIANÇA ancorada na confiabilidade medida no backtest.

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


def predict_match(conn, home, away, mando=0.0, city=None, sigma_ajuste=SIGMA_AJUSTE_DEFAULT, usar_estilo=False):
    a = _team(conn, home)
    b = _team(conn, away)
    if not a or not b:
        miss = home if not a else away
        return {"erro": "time não encontrado", "faltando": miss, "sugestoes": _suggest(conn, miss)}
    dr = a["elo"] - b["elo"] + mando
    sigma_dr = math.sqrt(a["sigma_r"] ** 2 + b["sigma_r"] ** 2 + 2 * sigma_ajuste ** 2)
    ga = gd_alt(city, a["name"], b["name"]) if city else 0.0
    ea = eb = 1.0
    if usar_estilo:
        from .estilo import team_styles
        st, _ = team_styles(conn)
        ea, eb = st.get(a["team_id"], 1.0), st.get(b["team_id"], 1.0)
    pr = predict(dr, sigma_dr, PredictParams(), estilo_a=ea, estilo_b=eb, gd_alt=ga)
    # banda recentrada no ponto do ensemble (largura = incerteza propagada da leitura Elo-direto)
    hw = (pr["band_pv_hi"] - pr["band_pv_lo"]) / 2.0
    pr["band_pv_lo"] = max(0.01, pr["p_v"] - hw)
    pr["band_pv_hi"] = min(0.99, pr["p_v"] + hw)
    sigma_r_avg = (a["sigma_r"] + b["sigma_r"]) / 2.0
    reliab, reliab_model = _reliab_from_meta(conn)
    conf = confidence(pr["p_v"], pr["p_e"], pr["p_d"], sigma_r_avg, reliab)
    mk = markets(pr["lambda_a"], pr["lambda_b"], PredictParams().max_goals)
    return {"home": a["name"], "away": b["name"], "elo_home": a["elo"], "elo_away": b["elo"],
            "sigma_home": a["sigma_r"], "sigma_away": b["sigma_r"], "dr": dr, "sigma_dr": sigma_dr,
            "gd_alt": ga, "estilo_a": ea, "estilo_b": eb,
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
    p.add_argument("--estilo", action="store_true", help="aplica estilo (tendência de gols) — candidato ao portão")
    args = p.parse_args(argv)
    if not Path(args.db).exists():
        print(f"[erro] {args.db} não existe. Rode ingest + elo_engine antes."); return 1
    conn = db.connect(args.db)
    r = predict_match(conn, args.home, args.away, args.mando, args.city, usar_estilo=args.estilo)
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
    if r.get("reliab_stale"):
        print("  ⚠ curva de confiança é de outra versão — rode 'python -m scm.calibrate_confidence'")
    print(f"  confiança: {r['conf']:.0f}/100 ({r['conf_label']})  ·  modelo {MODEL_VERSION}")
    print("  — probabilidade, não certeza; não é recomendação de aposta.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
