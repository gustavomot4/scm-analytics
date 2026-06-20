"""web — interface gráfica local (Flask) para previsão de confrontos.

100% local: `python -m scm.web` -> http://127.0.0.1:5000
Serve a página e uma API que reusa `predict_match` sobre o Elo já reconstruído.
Nada lê a internet no cálculo.
"""
from __future__ import annotations

import argparse
import threading
import time
from pathlib import Path

from . import db
from .predict_match import predict_match
from .predictor import MODEL_VERSION
from .ingest import DEFAULT_DB

# Estado do botão "Atualizar dados" (refresh do pipeline). Local, um job por vez.
# i/n = etapa atual / total (p/ a barra de progresso); step = rótulo legível.
_UPDATE = {"state": "idle", "step": "", "i": 0, "n": 5, "message": "", "ts": None}
_UPDATE_LOCK = threading.Lock()


def _run_pipeline(db_path, download=True):
    """Refresh do sistema (botão Atualizar): snapshot martj42 -> Elo -> features -> previsões.

    Roda em THREAD (o servidor é threaded) e publica a etapa atual (i/n + rótulo) em `_UPDATE`
    p/ o front mostrar a barra de progresso. É a ÚNICA parte que toca a rede (snapshot), coerente
    com 'nada lê a internet no cálculo'. Reusa os run() dos módulos (mesma lógica da CLI)."""
    from . import ingest, elo_engine, features_pit, predictor

    def step(i, s):
        _UPDATE.update(i=i, step=s, ts=time.strftime("%H:%M:%S"))
    try:
        _UPDATE.update(state="running", i=0, message="")
        if download:
            step(1, "Baixando dados novos (martj42)…")
            ingest.download_snapshot(dest=ingest.DEFAULT_CSV)
        step(2, "Ingerindo resultados no banco…")
        ingest.ingest(ingest.DEFAULT_CSV, db_path)
        step(3, "Reconstruindo o Elo…")
        c = db.connect(db_path); elo_engine.run(c); c.close()
        step(4, "Montando features (a etapa mais longa, ~1 min)…")
        c = db.connect(db_path); features_pit.run(c); c.close()
        step(5, "Gerando previsões…")
        c = db.connect(db_path); predictor.run(c); c.close()
        _UPDATE.update(state="done", i=5, step="Base atualizada.", ts=time.strftime("%H:%M:%S"))
    except Exception as e:   # rede/arquivo/etc. — reporta no painel
        _UPDATE.update(state="error", step="Falhou.", message=str(e))


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
        with db.session(app.config["DB"]) as conn:   # P-I: fecha sempre, mesmo em erro
            r = predict_match(conn, home, away, mando=mando, city=city, odds=odds)
        if r.get("erro"):
            return jsonify({"erro": r["erro"], "sugestoes": r.get("sugestoes", [])})
        venue = f"Altitude — {city}" if city else (f"Mando +{mando:.0f}" if mando else "Sede neutra")
        return jsonify({
            "home": r["home"], "away": r["away"], "venue": venue,
            "elo_home": round(r["elo_home"]), "elo_away": round(r["elo_away"]),
            "dr": round(r["dr"]), "provisional": r["provisional"],
            "elo_diff": round(r["elo_home"] - r["elo_away"]), "form_diff": round(r["form_a"] - r["form_b"], 1),
            "mando": r["mando"], "gd_alt": round(r["gd_alt"], 2),
            "dr_desf": round(r["dr_desf"], 1),
            "datk_home": round(r.get("datk_home", 0.0), 3), "datk_away": round(r.get("datk_away", 0.0), 3),
            "p_v": r["p_v"], "p_e": r["p_e"], "p_d": r["p_d"],
            "band_lo": r["band_pv_lo"], "band_hi": r["band_pv_hi"],
            "lambda_a": r["lambda_a"], "lambda_b": r["lambda_b"],
            "p_over25": r["p_over25"], "p_btts": r["p_btts"],
            "scores": r["poisson"]["top5"], "conf": r["conf"], "conf_label": r["conf_label"],
            "markets": r["markets"], "knockout": r.get("knockout"), "mercado": r.get("mercado"),
            "p_model": r.get("p_model"),
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
        with db.session(app.config["DB"]) as conn:   # P-I
            bk = most_likely_bracket(conn, cfg_path)
            mc = run(conn, cfg_path, n_sims=sims)
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
        with db.session(app.config["DB"]) as conn:   # P-I
            cfg, groups = load_config(cfg_path)
            warnings = validate(groups, get_elos(conn))
            res = run(conn, cfg_path, n_sims=sims)
        res["warnings"] = warnings
        return jsonify(res)

    @app.get("/prospectivo")
    def prospectivo_page():
        return render_template("prospectivo.html")

    @app.get("/api/prospectivo")
    def api_prospectivo():
        """Painel prospectivo (D-66): Brier real da Copa + previsão vs resultado vs mercado."""
        from .registrar import dashboard_data
        with db.session(app.config["DB"]) as conn:
            data = dashboard_data(conn)
        return jsonify(data)

    @app.post("/api/update")
    def api_update():
        """Botão Atualizar (D-69): dispara o refresh do pipeline em background (1 por vez)."""
        download = request.args.get("download", "1") != "0"
        with _UPDATE_LOCK:
            if _UPDATE["state"] == "running":
                return jsonify({"erro": "atualização já em andamento", **_UPDATE}), 409
            _UPDATE.update(state="running", step="Iniciando…", i=0, message="")
        threading.Thread(target=_run_pipeline, args=(app.config["DB"], download), daemon=True).start()
        return jsonify({"started": True})

    @app.get("/api/update/status")
    def api_update_status():
        return jsonify(_UPDATE)

    # --- Registro prospectivo pela interface (D-71): mesmas ações da CLI, sem terminal ---
    @app.post("/api/registrar/register-batch")
    def api_register_batch():
        """Registra a rodada de dados/fixtures.json (mesma ação do `registrar register-batch`)."""
        import json as _json
        from .registrar import register_batch, DEFAULT_FIXTURES
        fx = Path(DEFAULT_FIXTURES)
        if not fx.exists():
            return jsonify({"erro": "dados/fixtures.json não encontrado — copie dados/fixtures.json.example "
                                    "e preencha a rodada (ou use o formulário 'Registrar um jogo')."}), 400
        try:
            fixtures = _json.loads(fx.read_text(encoding="utf-8"))
        except Exception as e:
            return jsonify({"erro": "fixtures.json inválido: " + str(e)}), 400
        with db.session(app.config["DB"]) as conn:
            return jsonify(register_batch(conn, fixtures))

    @app.post("/api/registrar/register")
    def api_register_one():
        """Registra UM confronto (mesma ação do `registrar register`). Imutável, carimba versão+hash."""
        from .registrar import register
        home = request.args.get("home", "").strip()
        away = request.args.get("away", "").strip()
        date = request.args.get("date", "").strip()
        city = request.args.get("city") or None
        try:
            mando = float(request.args.get("mando", 0) or 0)
        except ValueError:
            mando = 0.0
        if not (home and away and date):
            return jsonify({"erro": "informe Time A, Time B e a data (YYYY-MM-DD)."}), 400
        with db.session(app.config["DB"]) as conn:
            r = register(conn, home, away, date, mando=mando, city=city)
        if r.get("erro") == "já registrado (imutável)":
            return jsonify({"ja_existia": True, "home": home, "away": away, "data_jogo": date})
        if r.get("erro"):
            return jsonify(r), 400
        return jsonify({"ok": True, "home": r["home"], "away": r["away"],
                        "data_jogo": r["data_jogo"], "hash": r["hash_inputs"]})

    @app.post("/api/registrar/settle")
    def api_settle():
        """Preenche os resultados das previsões em aberto pelo snapshot (= `registrar settle-from-db`)."""
        from .registrar import settle_from_db
        with db.session(app.config["DB"]) as conn:
            return jsonify(settle_from_db(conn))

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
    # threaded: permite o polling do /api/update/status enquanto o refresh roda em background
    create_app(args.db).run(host="127.0.0.1", port=args.port, debug=False, threaded=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
