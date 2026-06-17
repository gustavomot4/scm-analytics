"""predict_match — a porta da frente: prevê UM confronto específico.

Usa o Elo atual (`ratings_current`) das duas seleções + mando/altitude opcionais e o
predictor v0.2 (com altitude). Saída: P(V/E/D)+banda, λ, over/under 2.5, ambos marcam,
placares prováveis e confiança.

Para jogos HIPOTÉTICOS não há forma recente computada → usa o Elo puro (que já reflete a
força de longo prazo); a incerteza de forma/escalação entra como `σ_ajuste` padrão.
Probabilidade, não certeza — não é recomendação de aposta.
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path

from . import db
from .predictor import PredictParams, predict, MODEL_VERSION
from .altitude import gd_alt
from .ingest import DEFAULT_DB

SIGMA_AJUSTE_DEFAULT = 40.0   # incerteza de forma/escalação p/ jogo futuro [a calibrar]
SIGMA_REF = 250.0


def _team(conn, name):
    return conn.execute(
        """SELECT t.name, r.elo, r.sigma_r, r.n_games, r.provisional
           FROM ratings_current r JOIN teams t USING (team_id)
           WHERE lower(t.name) = lower(?)""", (name,)).fetchone()


def _suggest(conn, name):
    like = f"%{(name or '')[:3]}%"
    return [r[0] for r in conn.execute(
        "SELECT t.name FROM ratings_current r JOIN teams t USING (team_id) "
        "WHERE t.name LIKE ? ORDER BY r.elo DESC LIMIT 8", (like,))]


def confidence(p_v, p_e, p_d, sigma_dr, sigma_ref=SIGMA_REF):
    sep = max(0.0, (max(p_v, p_e, p_d) - 1 / 3) / (2 / 3))
    g = 1.0 - min(0.6, sigma_dr / sigma_ref)
    return 100.0 * (0.5 + 0.5 * sep) * g


def predict_match(conn, home, away, mando=0.0, city=None, sigma_ajuste=SIGMA_AJUSTE_DEFAULT):
    a = _team(conn, home)
    b = _team(conn, away)
    if not a or not b:
        miss = home if not a else away
        return {"erro": "time não encontrado", "faltando": miss, "sugestoes": _suggest(conn, miss)}
    dr = a["elo"] - b["elo"] + mando
    sigma_dr = math.sqrt(a["sigma_r"] ** 2 + b["sigma_r"] ** 2 + 2 * sigma_ajuste ** 2)
    ga = gd_alt(city, a["name"], b["name"]) if city else 0.0
    pr = predict(dr, sigma_dr, PredictParams(), gd_alt=ga)
    # banda recentrada no ponto do ensemble (largura = incerteza propagada da leitura Elo-direto)
    hw = (pr["band_pv_hi"] - pr["band_pv_lo"]) / 2.0
    pr["band_pv_lo"] = max(0.01, pr["p_v"] - hw)
    pr["band_pv_hi"] = min(0.99, pr["p_v"] + hw)
    return {"home": a["name"], "away": b["name"], "elo_home": a["elo"], "elo_away": b["elo"],
            "sigma_home": a["sigma_r"], "sigma_away": b["sigma_r"], "dr": dr, "sigma_dr": sigma_dr,
            "gd_alt": ga, "provisional": bool(a["provisional"] or b["provisional"]),
            "conf": confidence(pr["p_v"], pr["p_e"], pr["p_d"], sigma_dr), **pr}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Prevê um confronto (Elo atual + mando/altitude).")
    p.add_argument("home", help="time mandante / time A (favorito primeiro, por convenção)")
    p.add_argument("away", help="time visitante / time B")
    p.add_argument("--db", default=str(DEFAULT_DB))
    p.add_argument("--mando", type=float, default=0.0,
                   help="mando em Elo p/ o 1º time (0=neutro/Copa; ~40 anfitrião 2026; ~60-100 casa)")
    p.add_argument("--city", default=None, help="cidade-sede (p/ altitude; ex.: 'Mexico City', 'La Paz')")
    args = p.parse_args(argv)
    if not Path(args.db).exists():
        print(f"[erro] {args.db} não existe. Rode ingest + elo_engine antes."); return 1
    conn = db.connect(args.db)
    r = predict_match(conn, args.home, args.away, args.mando, args.city)
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
    print(f"\n  {r['home']}  vs  {r['away']}      [sede: {sede}]")
    print(f"  Elo: {r['home']} {r['elo_home']:.0f} (σ{r['sigma_home']:.0f}) · "
          f"{r['away']} {r['elo_away']:.0f} (σ{r['sigma_away']:.0f})  |  dr={r['dr']:+.0f}  σ_dr={r['sigma_dr']:.0f}"
          + ("  ⚠ rating provisório" if r["provisional"] else ""))
    print(f"  P({r['home']}) {r['p_v']*100:.1f}%   ·   Empate {r['p_e']*100:.1f}%   ·   "
          f"P({r['away']}) {r['p_d']*100:.1f}%      (banda {r['home']} {r['band_pv_lo']*100:.0f}–{r['band_pv_hi']*100:.0f}%)")
    print(f"  λ: {r['home']} {r['lambda_a']:.2f} · {r['away']} {r['lambda_b']:.2f}   |   "
          f"over 2.5: {r['p_over25']*100:.0f}%   ·   ambos marcam: {r['p_btts']*100:.0f}%")
    print("  placares: " + " · ".join(f"{s} {pp*100:.0f}%" for s, pp in r["poisson"]["top5"]))
    lbl = "alta" if r["conf"] >= 65 else ("média" if r["conf"] >= 40 else "baixa")
    print(f"  confiança: {r['conf']:.0f}/100 ({lbl})  ·  modelo {MODEL_VERSION}")
    print("  — probabilidade, não certeza; não é recomendação de aposta.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
