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
_UPDATE = {"state": "idle", "step": "", "i": 0, "n": 5, "pct": 0, "message": "",
           "ts": None, "logs": [], "started": None}
_UPDATE_LOCK = threading.Lock()
# pct ao INICIAR cada etapa (features é a mais longa: 42→88). O front faz a barra "andar"
# suavemente até o teto de cada etapa enquanto ela roda.
_STEP_PCT = {1: 3, 2: 15, 3: 28, 4: 42, 5: 90}


def _log(msg):
    """Acrescenta uma linha de log (carimbo de hora), mantendo as últimas 40."""
    line = time.strftime("%H:%M:%S") + "  " + msg
    _UPDATE["logs"] = (list(_UPDATE.get("logs") or []) + [line])[-40:]


def _run_pipeline(db_path, download=True):
    """Refresh do sistema (botão Atualizar): snapshot martj42 -> Elo -> features -> previsões.

    Roda em THREAD (o servidor é threaded) e publica a etapa atual (i/n + rótulo) em `_UPDATE`
    p/ o front mostrar a barra de progresso. É a ÚNICA parte que toca a rede (snapshot), coerente
    com 'nada lê a internet no cálculo'. Reusa os run() dos módulos (mesma lógica da CLI)."""
    from . import ingest, elo_engine, features_pit, predictor

    def step(i, s):
        _UPDATE.update(i=i, step=s, pct=_STEP_PCT.get(i, _UPDATE.get("pct", 0)),
                       ts=time.strftime("%H:%M:%S"))
        _log(s)
    try:
        _UPDATE.update(state="running", i=0, pct=1, message="", logs=[], started=time.time())
        _log("Iniciando atualização…")
        if download:
            step(1, "Baixando dados novos (martj42)…")
            ingest.download_snapshot(dest=ingest.DEFAULT_CSV)
        step(2, "Ingerindo resultados no banco…")
        ingest.ingest(ingest.DEFAULT_CSV, db_path)
        step(3, "Reconstruindo o Elo…")
        c = db.connect(db_path); elo_engine.run(c); c.close()
        step(4, "Montando features dos jogos novos…")
        c = db.connect(db_path); features_pit.run(c, incremental=True); c.close()
        step(5, "Gerando previsões dos jogos novos…")
        c = db.connect(db_path); predictor.run(c, incremental=True); c.close()
        _UPDATE.update(state="done", i=5, pct=100, step="Base atualizada.",
                       ts=time.strftime("%H:%M:%S"))
        _log("✓ Base atualizada.")
    except Exception as e:   # rede/arquivo/etc. — reporta no painel
        _UPDATE.update(state="error", step="Falhou.", message=str(e))
        _log("✗ Erro: " + str(e))


# --- Simulação da Copa: cache + job em background com progresso (P3/D-73) ---
# A sim/bracket é cara (Monte Carlo); o sorteio+Elo só mudam após "Atualizar". Então cacheamos
# por (tipo, sims, impressão-digital dos dados). 1ª vez roda em thread publicando % (igual ao
# "Atualizar"); visitas/abas seguintes são INSTANTÂNEAS (cache).
_SIM = {"state": "idle", "pct": 0, "kind": "", "key": "", "msg": ""}
_SIM_LOCK = threading.Lock()
_SIM_CACHE = {}


def _sim_fingerprint(conn):
    from . import config as _cfg   # inclui os flags de simulação: trocar na página Experimentos invalida o cache
    r = conn.execute("SELECT COUNT(*), MAX(date) FROM matches").fetchone()
    return f"{r[0]}|{r[1]}|{MODEL_VERSION}|{getattr(_cfg,'SIM_SIGMA_MODE','per_game')}|{getattr(_cfg,'SIM_AD_BLEND',0.0)}"


def _run_sim_job(kind, sims, key, db_path, cfg_path):
    from .simulate import run, most_likely_bracket, load_config, validate, get_elos

    def progress(done, total):
        base = 5 if kind == "bracket" else 0
        _SIM["pct"] = min(99, base + int(done / max(total, 1) * (99 - base)))
    try:
        with db.session(db_path) as conn:
            if kind == "bracket":
                bk = most_likely_bracket(conn, cfg_path)
                _SIM["pct"] = 5
                mc = run(conn, cfg_path, n_sims=sims, progress=progress)
                result = {"model": bk["model"], "n_sims": mc["n_sims"],
                          "match": {str(k): v for k, v in bk["match"].items()},
                          "champion": bk["champion"], "finalists": list(bk["finalists"]),
                          "third": bk["third"], "table": mc["table"]}
            else:
                cfg, groups = load_config(cfg_path)
                warnings = validate(groups, get_elos(conn))
                result = run(conn, cfg_path, n_sims=sims, progress=progress)
                result["warnings"] = warnings
        _SIM_CACHE[key] = result
        _SIM.update(state="done", pct=100)
    except Exception as e:   # noqa: BLE001 — reporta no painel
        _SIM.update(state="error", msg=str(e))


# --- Página "Experimentos" (D-75): ativa flags de SIMULAÇÃO ao vivo + roda o portão na UI ---
# Catálogo: os de 'sim' têm toggle ao vivo (seguros); os de 'modelo' são SÓ LEITURA (mudá-los
# exige rebuild+versão, senão a produção diverge do backtest). Vereditos = resultados dos portões.
_EXP_SIM = [
    {"key": "SIM_SIGMA_MODE", "nome": "Incerteza correlacionada (σ por-time)", "tipo": "toggle",
     "valores": ["per_game", "per_team"], "gate": "inconclusivo",
     "veredito": "ΔBrier avanço IC95 cruza zero (D-74) — não comprova ganho", "gatekey": "simvar"},
    {"key": "SIM_AD_BLEND", "nome": "Mistura AD no λ da simulação", "tipo": "number",
     "gate": "adotado", "veredito": "major +0,0071 / all +0,0050, IC>0", "gatekey": None},
]
_EXP_MODELO = [
    {"nome": "Perna ataque/defesa (AD)", "gate": "adotado", "veredito": "+0,0039 IC>0 (v0.4)"},
    {"nome": "Altitude", "gate": "adotado", "veredito": "+0,049 nos jogos de altitude (D-18)"},
    {"nome": "Curva de empate empírica", "gate": "adotado", "veredito": "tail corrigido, Brier não regrediu (D-26)"},
    {"nome": "Tempo do gol", "gate": "adotado", "veredito": "±1,2pp previsto×observado (D-71)"},
    {"nome": "Prior de xG na perna AD", "gate": "rejeitado", "veredito": "+0,0002 ruído, IC cruza zero (D-50)"},
    {"nome": "Estilo (tendência de gols)", "gate": "rejeitado", "veredito": "ΔBrier-BTTS IC cruza zero (D-23)"},
    {"nome": "Dixon-Coles", "gate": "rejeitado", "veredito": "sem ganho (D-39/40)"},
    {"nome": "σ de Glicko", "gate": "rejeitado", "veredito": "cobertura de banda não passou (D-42)"},
    {"nome": "Calor (proxy WBGT)", "gate": "rejeitado", "veredito": "+0,0007 IC cruza zero (D-19)"},
    {"nome": "Reversão à média por recência", "gate": "rejeitado", "veredito": "piora o Brier (calibrate_recency)"},
]
_GATE = {"state": "idle", "which": "", "result": None, "msg": ""}
_GATE_LOCK = threading.Lock()


def _run_gate_job(which, db_path):
    try:
        with db.session(db_path) as conn:
            if which == "simvar":
                from .calibrate_simvar import run_gate
                r = run_gate(conn, sims=4000)
            else:
                raise ValueError(f"portão desconhecido: {which}")
        _GATE.update(state="done", result=r)
    except Exception as e:   # noqa: BLE001
        _GATE.update(state="error", msg=str(e))


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

    def _sim_start(kind):
        """Inicia (ou devolve do cache) a simulação. Retorna {done,result} | {running,pct} | {erro}.
        O front faz POLL do mesmo endpoint até vir {done}. 1 job por vez (local)."""
        cfg_path = app.config["CONFIG"]
        if not Path(cfg_path).exists():
            return jsonify({"erro": "sorteio não encontrado — preencha dados/copa2026.json"})
        try:
            sims = int(request.args.get("sims", 2000) or 2000)
        except ValueError:
            sims = 2000
        sims = max(200, min(sims, 50000))
        with db.session(app.config["DB"]) as conn:
            key = f"{kind}|{sims}|{_sim_fingerprint(conn)}"
        if key in _SIM_CACHE:
            return jsonify({"done": True, "result": _SIM_CACHE[key]})
        with _SIM_LOCK:
            if _SIM["state"] == "running":
                return jsonify({"running": True, "pct": _SIM["pct"] if _SIM["key"] == key else 0})
            _SIM.update(state="running", pct=0, kind=kind, key=key, msg="")
        threading.Thread(target=_run_sim_job, args=(kind, sims, key, app.config["DB"], cfg_path),
                         daemon=True).start()
        return jsonify({"running": True, "pct": 0})

    @app.get("/api/bracket")
    def api_bracket():
        return _sim_start("bracket")

    @app.get("/api/simulate")
    def api_simulate():
        return _sim_start("simulate")

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

    # --- Monitor (D-76): calibração/ECE/drift + skill vs mercado da Copa real (operacional) ---
    @app.get("/monitor")
    def monitor_page():
        return render_template("monitor.html")

    @app.get("/api/monitor")
    def api_monitor():
        from .monitor import summary
        with db.session(app.config["DB"]) as conn:
            return jsonify(summary(conn))

    # --- Experimentos (D-75): toggles de SIMULAÇÃO ao vivo + catálogo de modelo só-leitura ---
    @app.get("/experimentos")
    def experimentos_page():
        return render_template("experimentos.html")

    @app.get("/api/experimentos")
    def api_experimentos():
        from . import config as _cfg
        ovr = _cfg.current_overrides()
        sim = []
        for it in _EXP_SIM:
            sim.append({**it, "valor": ovr.get(it["key"])})
        return jsonify({"sim": sim, "modelo": _EXP_MODELO, "model": MODEL_VERSION})

    @app.post("/api/experimentos/toggle")
    def api_exp_toggle():
        """Liga/desliga um flag de SIMULAÇÃO (seguro: não toca em predictions/versão)."""
        from . import config as _cfg
        key = request.args.get("key", "")
        value = request.args.get("value", "")
        try:
            applied = _cfg.set_override(key, value)
        except ValueError as e:
            return jsonify({"erro": str(e)}), 400
        return jsonify({"ok": True, "key": key, "valor": applied})

    @app.post("/api/experimentos/gate")
    def api_exp_gate():
        """Roda um portão na UI (background, 1 por vez). Front faz POLL do mesmo endpoint."""
        which = request.args.get("which", "simvar")
        if _GATE["state"] == "running":
            return jsonify({"running": True})
        if _GATE["state"] == "done" and _GATE.get("which") == which and _GATE.get("result"):
            return jsonify({"done": True, "result": _GATE["result"]})
        with _GATE_LOCK:
            if _GATE["state"] == "running":
                return jsonify({"running": True})
            _GATE.update(state="running", which=which, result=None, msg="")
        threading.Thread(target=_run_gate_job, args=(which, app.config["DB"]), daemon=True).start()
        return jsonify({"running": True})

    @app.get("/api/experimentos/gate/status")
    def api_exp_gate_status():
        return jsonify(dict(_GATE))

    @app.post("/api/update")
    def api_update():
        """Botão Atualizar (D-69): dispara o refresh do pipeline em background (1 por vez)."""
        download = request.args.get("download", "1") != "0"
        with _UPDATE_LOCK:
            if _UPDATE["state"] == "running":
                return jsonify({"erro": "atualização já em andamento", **_UPDATE}), 409
            _UPDATE.update(state="running", step="Iniciando…", i=0, pct=1, message="", logs=["Iniciando…"], started=time.time())
        threading.Thread(target=_run_pipeline, args=(app.config["DB"], download), daemon=True).start()
        return jsonify({"started": True})

    @app.get("/api/update/status")
    def api_update_status():
        st = dict(_UPDATE)
        st["elapsed"] = int(time.time() - st["started"]) if st.get("started") and st["state"] in ("running", "done") else 0
        return jsonify(st)

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
    p.add_argument("--open", dest="open_browser", action="store_true",
                   help="abre o navegador automaticamente (usado pelo launcher)")
    args = p.parse_args(argv)
    if not Path(args.db).exists():
        print(f"[erro] {args.db} não existe. Rode ingest + elo_engine antes.")
        return 1
    url = f"http://127.0.0.1:{args.port}"
    print(f"Interface em {url}   (Ctrl+C para sair)")
    if getattr(args, "open_browser", False):
        import webbrowser
        threading.Thread(target=lambda: (time.sleep(1.5), webbrowser.open(url)), daemon=True).start()
    # threaded: permite o polling do /api/update/status enquanto o refresh roda em background
    create_app(args.db).run(host="127.0.0.1", port=args.port, debug=False, threaded=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
