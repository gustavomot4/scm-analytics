"""web — interface gráfica local (Flask) para previsão de confrontos.

100% local: `python -m scm.web` -> http://127.0.0.1:5000
Serve a página e uma API que reusa `predict_match` sobre o Elo já reconstruído.
Nada lê a internet no cálculo.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from . import db
from .predict_match import predict_match
from .predictor import MODEL_VERSION
from .ingest import DEFAULT_DB


def create_app(db_path=None):
    from flask import Flask, render_template, request, jsonify

    app = Flask(__name__)
    app.config["DB"] = str(db_path or DEFAULT_DB)
    from .simulate import DEFAULT_CONFIG
    app.config["CONFIG"] = str(DEFAULT_CONFIG)

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/api/teams")
    def teams():
        conn = db.connect(app.config["DB"])
        names = [r[0] for r in conn.execute(
            "SELECT t.name FROM ratings_current r JOIN teams t USING (team_id) ORDER BY t.name")]
        conn.close()
        return jsonify({"teams": names, "model": MODEL_VERSION})

    @app.get("/api/predict")
    def api_predict():
        home = request.args.get("home", "").strip()
        away = request.args.get("away", "").strip()
        city = request.args.get("city") or None
        try:
            mando = float(request.args.get("mando", 0) or 0)
        except ValueError:
            mando = 0.0
        odds = None
        try:
            oh = float(request.args.get("oh", 0) or 0)
            od = float(request.args.get("od", 0) or 0)
            oa = float(request.args.get("oa", 0) or 0)
            if oh > 1 and od > 1 and oa > 1:
                odds = (oh, od, oa)
        except ValueError:
            odds = None
        conn = db.connect(app.config["DB"])
        r = predict_match(conn, home, away, mando=mando, city=city, odds=odds)
        conn.close()
        if r.get("erro"):
            return jsonify({"erro": r["erro"], "sugestoes": r.get("sugestoes", [])})
        venue = f"Altitude — {city}" if city else (f"Mando +{mando:.0f}" if mando else "Sede neutra")
        return jsonify({
            "home": r["home"], "away": r["away"], "venue": venue,
            "elo_home": round(r["elo_home"]), "elo_away": round(r["elo_away"]),
            "dr": round(r["dr"]), "provisional": r["provisional"],
            "elo_diff": round(r["elo_home"] - r["elo_away"]), "form_diff": round(r["form_a"] - r["form_b"], 1),
            "mando": r["mando"], "gd_alt": round(r["gd_alt"], 2),
            "dr_desf": round(r["dr_desf"], 1), "gd_desf": round(r["gd_desf"], 2),
            "p_v": r["p_v"], "p_e": r["p_e"], "p_d": r["p_d"],
            "band_lo": r["band_pv_lo"], "band_hi": r["band_pv_hi"],
            "lambda_a": r["lambda_a"], "lambda_b": r["lambda_b"],
            "p_over25": r["p_over25"], "p_btts": r["p_btts"],
            "scores": r["poisson"]["top5"], "conf": r["conf"], "conf_label": r["conf_label"],
            "markets": r["markets"], "knockout": r.get("knockout"), "mercado": r.get("mercado"),
        })

    @app.get("/simulacao")
    def simulacao():
        return render_template("simulacao.html")

    @app.get("/bracket")
    def bracket_page():
        return render_template("bracket.html")

    @app.get("/api/bracket")
    def api_bracket():
        """Chaveamento mais provável (dos 16 avos à final) + tabela do Monte Carlo."""
        from .simulate import most_likely_bracket, run
        cfg_path = app.config["CONFIG"]
        if not Path(cfg_path).exists():
            return jsonify({"erro": "sorteio não encontrado — preencha dados/copa2026.json"})
        try:
            sims = int(request.args.get("sims", 5000) or 5000)
        except ValueError:
            sims = 5000
        sims = max(200, min(sims, 50000))
        conn = db.connect(app.config["DB"])
        bk = most_likely_bracket(conn, cfg_path)
        mc = run(conn, cfg_path, n_sims=sims)
        conn.close()
        return jsonify({
            "model": bk["model"], "n_sims": mc["n_sims"],
            "match": {str(k): v for k, v in bk["match"].items()},   # mid -> {a,b,winner,p_adv}
            "champion": bk["champion"], "finalists": list(bk["finalists"]),
            "third": bk["third"], "table": mc["table"],
        })

    @app.get("/api/simulate")
    def api_simulate():
        from .simulate import run, load_config, validate, get_elos
        try:
            sims = int(request.args.get("sims", 5000) or 5000)
        except ValueError:
            sims = 5000
        sims = max(200, min(sims, 50000))
        cfg_path = app.config["CONFIG"]
        if not Path(cfg_path).exists():
            return jsonify({"erro": "sorteio não encontrado — preencha dados/copa2026.json"})
        conn = db.connect(app.config["DB"])
        cfg, groups = load_config(cfg_path)
        warnings = validate(groups, get_elos(conn))
        res = run(conn, cfg_path, n_sims=sims)
        conn.close()
        res["warnings"] = warnings
        return jsonify(res)

    return app


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Interface web local de previsão.")
    p.add_argument("--db", default=str(DEFAULT_DB))
    p.add_argument("--port", type=int, default=5000)
    args = p.parse_args(argv)
    if not Path(args.db).exists():
        print(f"[erro] {args.db} não existe. Rode ingest + elo_engine antes.")
        return 1
    print(f"Interface em http://127.0.0.1:{args.port}   (Ctrl+C para sair)")
    create_app(args.db).run(host="127.0.0.1", port=args.port, debug=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
