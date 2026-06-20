"""registrar — registro prospectivo de previsões gerado por CÓDIGO (audit 06-19, P-G/D-38).

Fecha o laço de validação que faltava: a previsão é gravada ANTES do jogo (carimbando
`versao_modelo` + `hash_inputs`), e o resultado é preenchido DEPOIS — então dá para medir
o **Brier prospectivo real** da Copa, não só o histórico. Respeita o registro imutável
(D-07): `register` nunca sobrescreve uma linha já gravada; `settle` só preenche o
resultado de linhas ainda em aberto; as colunas de PREVISÃO nunca mudam.

Usa o `predict_match` (modelo `baseline-v0.3-altitude`, já com a forma recente — D-34).
Probabilidade, não certeza — não é recomendação de aposta.

Uso:
    python -m scm.registrar register "Mexico" "South Korea" --date 2026-06-20 --city "Mexico City"
    python -m scm.registrar settle   "Mexico" "South Korea" --date 2026-06-20 --score 2 1
    python -m scm.registrar report
"""
from __future__ import annotations

import argparse
import csv
import hashlib
from datetime import datetime, timezone
from pathlib import Path

from . import db
from .ingest import DEFAULT_DB
from .predict_match import predict_match
from .predictor import MODEL_VERSION
from .backtest_harness import brier, outcome_of, UNIFORM

DEFAULT_REG = Path(__file__).resolve().parent.parent / "dados" / "registro-auto.csv"
DEFAULT_DESF = Path(__file__).resolve().parent.parent / "dados" / "desfalques.json"
DEFAULT_FIXTURES = Path(__file__).resolve().parent.parent / "dados" / "fixtures.json"
FIELDS = ["ts_registro", "data_jogo", "home", "away", "versao_modelo", "hash_inputs",
          "mando", "city", "p_v", "p_e", "p_d", "lambda_a", "lambda_b",
          "p_over25", "p_btts", "conf", "resultado", "gols_home", "gols_away", "brier"]


def _hash_inputs(r, data_jogo, mando) -> str:
    """Carimbo reprodutível dos insumos da previsão (detecta mudança de modelo/Elo)."""
    base = (f"{r['home']}|{r['away']}|{data_jogo}|{MODEL_VERSION}|{r['elo_home']:.1f}|"
            f"{r['elo_away']:.1f}|{r['dr']:.2f}|{r['sigma_dr']:.2f}|{r['gd_alt']:.3f}|{mando:.1f}")
    return hashlib.sha256(base.encode("utf-8")).hexdigest()[:12]


def _read(path) -> list:
    p = Path(path)
    if not p.exists():
        return []
    with p.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def _write(path, rows) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in FIELDS})


def _key(home, away, data_jogo):
    return (home.strip().lower(), away.strip().lower(), data_jogo.strip())


def register(conn, home, away, data_jogo, mando=0.0, city=None, path=DEFAULT_REG) -> dict:
    """Grava a previsão pré-jogo (imutável). Recusa duplicar (mesmo jogo+versão).

    Auto-carrega, se existirem: desfalques de `dados/desfalques.json` (chave date|home|away)
    e odds do `odds_hist` (gravadas via `scm.odds`) — assim a rodada usa todos os dados
    disponíveis sem passagem manual. Sem esses dados, prevê só com Elo/forma/altitude/mando.
    """
    from .desfalques import load_for_match
    from .odds import market_read
    des = load_for_match(DEFAULT_DESF, home, away, data_jogo) or None
    mk = market_read(conn, home, away, data_jogo)
    odds = (1.0 / mk["p_v"], 1.0 / mk["p_e"], 1.0 / mk["p_d"]) if mk else None   # prob -> pseudo-odds
    r = predict_match(conn, home, away, mando=mando, city=city, desfalques=des, odds=odds)
    if r.get("erro"):
        return r
    rows = _read(path)
    for x in rows:
        if _key(x["home"], x["away"], x["data_jogo"]) == _key(home, away, data_jogo) \
                and x["versao_modelo"] == MODEL_VERSION:
            return {"erro": "já registrado (imutável)", "home": home, "away": away, "data_jogo": data_jogo}
    rec = {
        "ts_registro": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "data_jogo": data_jogo, "home": r["home"], "away": r["away"],
        "versao_modelo": MODEL_VERSION, "hash_inputs": _hash_inputs(r, data_jogo, mando),
        "mando": f"{mando:.0f}", "city": city or "",
        "p_v": f"{r['p_v']:.4f}", "p_e": f"{r['p_e']:.4f}", "p_d": f"{r['p_d']:.4f}",
        "lambda_a": f"{r['lambda_a']:.3f}", "lambda_b": f"{r['lambda_b']:.3f}",
        "p_over25": f"{r['p_over25']:.4f}", "p_btts": f"{r['p_btts']:.4f}",
        "conf": f"{r['conf']:.0f}", "resultado": "", "gols_home": "", "gols_away": "", "brier": "",
    }
    rows.append(rec)
    _write(path, rows)
    return rec


def settle(home, away, data_jogo, gols_home, gols_away, path=DEFAULT_REG) -> dict:
    """Preenche o resultado de linha(s) em aberto (não toca na previsão). Calcula o Brier."""
    rows = _read(path)
    o = outcome_of(gols_home, gols_away)
    changed = 0
    for x in rows:
        if _key(x["home"], x["away"], x["data_jogo"]) == _key(home, away, data_jogo) and not x["resultado"]:
            p = {"p_v": float(x["p_v"]), "p_e": float(x["p_e"]), "p_d": float(x["p_d"])}
            x["resultado"] = o
            x["gols_home"] = str(int(gols_home))
            x["gols_away"] = str(int(gols_away))
            x["brier"] = f"{brier(p, o):.4f}"
            changed += 1
    if changed:
        _write(path, rows)
    return {"preenchidos": changed, "resultado": o}


def report(path=DEFAULT_REG, versao=None) -> dict:
    """Brier prospectivo médio (linhas já com resultado) vs uniforme."""
    rows = [x for x in _read(path) if x.get("resultado")]
    if versao:
        rows = [x for x in rows if x["versao_modelo"] == versao]
    if not rows:
        return {"n": 0}
    briers = [float(x["brier"]) for x in rows]
    uni = sum(brier(UNIFORM, x["resultado"]) for x in rows) / len(rows)
    n = len(rows)
    n_open = len([x for x in _read(path) if not x.get("resultado")])
    return {"n": n, "n_abertas": n_open, "brier": sum(briers) / n,
            "brier_uniforme": uni, "ganho_vs_uniforme": uni - sum(briers) / n}


def dashboard_data(conn, path=DEFAULT_REG) -> dict:
    """Dados do painel prospectivo (D-66): resumo (Brier acumulado) + jogos (previsão do modelo
    vs RESULTADO vs MERCADO). Reusa `report` e `odds.market_read`. Só leitura; sem rede."""
    from .odds import market_read
    games = []
    for x in _read(path):
        try:
            mk = market_read(conn, x["home"], x["away"], x["data_jogo"])
        except Exception:
            mk = None
        games.append({
            "data_jogo": x.get("data_jogo", ""), "home": x.get("home", ""), "away": x.get("away", ""),
            "p_v": float(x["p_v"]), "p_e": float(x["p_e"]), "p_d": float(x["p_d"]),
            "conf": x.get("conf", ""), "versao": x.get("versao_modelo", ""),
            "resultado": x.get("resultado", ""), "gols_home": x.get("gols_home", ""),
            "gols_away": x.get("gols_away", ""), "brier": x.get("brier", ""),
            "mercado": ({"p_v": mk["p_v"], "p_e": mk["p_e"], "p_d": mk["p_d"]} if mk else None),
        })
    games.sort(key=lambda g: g["data_jogo"])
    return {"summary": report(path), "games": games, "model": MODEL_VERSION}


def register_batch(conn, fixtures, path=DEFAULT_REG) -> dict:
    """Registra uma LISTA de confrontos da rodada. fixtures: [{home,away,date,city?,mando?}].

    Idempotente (D-07): jogos já registrados são pulados, não duplicados.
    """
    ok = skip = err = 0
    for f in fixtures:
        r = register(conn, f["home"], f["away"], f["date"],
                     mando=float(f.get("mando", 0) or 0), city=f.get("city"), path=path)
        if r.get("erro") == "já registrado (imutável)":
            skip += 1
        elif r.get("erro"):
            err += 1
        else:
            ok += 1
    return {"registrados": ok, "ja_existiam": skip, "erros": err}


def settle_from_db(conn, path=DEFAULT_REG) -> dict:
    """Preenche o resultado das previsões em aberto cujo jogo JÁ tem placar no snapshot (martj42).

    Automatiza o "preencher depois": re-rode o `ingest --download` antes (na sua máquina) e
    chame isto — toda previsão registrada cujo confronto saiu vira resultado + Brier.
    """
    pend = [x for x in _read(path) if not x.get("resultado")]
    n = 0
    for x in pend:
        row = conn.execute(
            """SELECT m.home_score hs, m.away_score s FROM matches m
               JOIN teams th ON th.team_id = m.home_team_id
               JOIN teams ta ON ta.team_id = m.away_team_id
               WHERE m.date = ? AND lower(th.name) = lower(?) AND lower(ta.name) = lower(?)
                 AND m.home_score IS NOT NULL""",
            (x["data_jogo"], x["home"], x["away"])).fetchone()
        if row:
            settle(x["home"], x["away"], x["data_jogo"], row["hs"], row["s"], path)
            n += 1
    return {"preenchidos": n, "abertas_restantes": len(pend) - n}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Registro prospectivo de previsões (P-G).")
    sub = ap.add_subparsers(dest="cmd", required=True)
    pr = sub.add_parser("register", help="grava a previsão pré-jogo (imutável)")
    pr.add_argument("home"); pr.add_argument("away")
    pr.add_argument("--date", required=True, dest="data_jogo", help="data do jogo (YYYY-MM-DD)")
    pr.add_argument("--mando", type=float, default=0.0)
    pr.add_argument("--city", default=None)
    pr.add_argument("--db", default=str(DEFAULT_DB))
    pr.add_argument("--reg", default=str(DEFAULT_REG))
    ps = sub.add_parser("settle", help="preenche o resultado pós-jogo")
    ps.add_argument("home"); ps.add_argument("away")
    ps.add_argument("--date", required=True, dest="data_jogo")
    ps.add_argument("--score", nargs=2, type=int, required=True, metavar=("GH", "GA"))
    ps.add_argument("--reg", default=str(DEFAULT_REG))
    rp = sub.add_parser("report", help="Brier prospectivo acumulado")
    rp.add_argument("--reg", default=str(DEFAULT_REG))
    rp.add_argument("--versao", default=None)
    pb = sub.add_parser("register-batch", help="registra uma lista de confrontos (JSON da rodada)")
    pb.add_argument("fixtures", nargs="?", default=str(DEFAULT_FIXTURES),
                    help='JSON da rodada (default: dados/fixtures.json): [{"home","away","date","city?","mando?"}]')
    pb.add_argument("--db", default=str(DEFAULT_DB))
    pb.add_argument("--reg", default=str(DEFAULT_REG))
    pf = sub.add_parser("settle-from-db", help="preenche resultados pelo snapshot (martj42)")
    pf.add_argument("--db", default=str(DEFAULT_DB))
    pf.add_argument("--reg", default=str(DEFAULT_REG))
    args = ap.parse_args(argv)

    if args.cmd == "register":
        if not Path(args.db).exists():
            print(f"[erro] {args.db} não existe. Rode ingest + elo_engine antes."); return 1
        conn = db.connect(args.db)
        r = register(conn, args.home, args.away, args.data_jogo, args.mando, args.city, args.reg)
        conn.close()
        if r.get("erro"):
            print(f"[erro] {r['erro']}" + (f" — sugestões: {', '.join(r.get('sugestoes', []))}" if r.get("sugestoes") else ""))
            return 1
        print(f"registrado: {r['home']} x {r['away']} ({r['data_jogo']})  "
              f"V/E/D {float(r['p_v'])*100:.0f}/{float(r['p_e'])*100:.0f}/{float(r['p_d'])*100:.0f}%  "
              f"conf {r['conf']}  hash {r['hash_inputs']}  -> {args.reg}")
        return 0
    if args.cmd == "settle":
        res = settle(args.home, args.away, args.data_jogo, args.score[0], args.score[1], args.reg)
        print(f"resultado {res['resultado']}: {res['preenchidos']} linha(s) preenchida(s).")
        return 0 if res["preenchidos"] else 1
    if args.cmd == "report":
        r = report(args.reg, args.versao)
        if not r.get("n"):
            print("sem previsões com resultado ainda (registre e preencha após os jogos)."); return 1
        print(f"\n  REGISTRO PROSPECTIVO — n={r['n']} jogos com resultado ({r['n_abertas']} em aberto)")
        print(f"  Brier prospectivo: {r['brier']:.4f}   (uniforme {r['brier_uniforme']:.4f})")
        print(f"  ganho vs uniforme: {r['ganho_vs_uniforme']:+.4f}")
        print("  — probabilidade, não certeza; não é recomendação de aposta.\n")
        return 0
    if args.cmd == "register-batch":
        if not Path(args.db).exists():
            print(f"[erro] {args.db} não existe."); return 1
        if not Path(args.fixtures).exists():
            print(f"[erro] arquivo da rodada não encontrado: {args.fixtures}\n"
                  f"       copie dados/fixtures.json.example p/ dados/fixtures.json e preencha."); return 1
        import json as _json
        fixtures = _json.loads(Path(args.fixtures).read_text(encoding="utf-8"))
        conn = db.connect(args.db); r = register_batch(conn, fixtures, args.reg); conn.close()
        print(f"lote: {r['registrados']} registrados · {r['ja_existiam']} já existiam · {r['erros']} erros -> {args.reg}")
        return 0
    if args.cmd == "settle-from-db":
        if not Path(args.db).exists():
            print(f"[erro] {args.db} não existe."); return 1
        conn = db.connect(args.db); r = settle_from_db(conn, args.reg); conn.close()
        print(f"preenchidos {r['preenchidos']} resultado(s) pelo snapshot · {r['abertas_restantes']} ainda em aberto.")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
