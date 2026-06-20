"""Testes do registrar — registro prospectivo gerado por código (P-G/D-38)."""
import csv
import os
import tempfile

import pytest

from scm import db
from scm import elo_engine as elo
from scm import registrar as R
from scm.predictor import MODEL_VERSION


def _conn():
    c = db.connect(":memory:"); db.init_schema(c)

    def M(date, h, a, hs, as_):
        hi = db.get_or_create_team(c, h); ai = db.get_or_create_team(c, a)
        c.execute("""INSERT INTO matches(date,home_team_id,away_team_id,home_score,away_score,
                     tournament,neutral,natural_key) VALUES (?,?,?,?,?,?,1,?)""",
                  (date, hi, ai, hs, as_, "FIFA World Cup", f"{date}|{h}|{a}"))
    for k in range(12):
        M(f"201{k % 9}-06-{(k % 27) + 1:02d}", "Brazil", "Bolivia", 3, 0)
        M(f"201{k % 9}-09-{(k % 27) + 1:02d}", "Argentina", "Brazil", 1, 1)
    c.commit(); elo.run(c)
    return c


def test_register_settle_report_flow():
    c = _conn(); path = tempfile.mktemp(suffix=".csv")
    try:
        r = R.register(c, "Brazil", "Bolivia", "2026-06-20", path=path)
        assert "erro" not in r
        assert r["versao_modelo"] == MODEL_VERSION and len(r["hash_inputs"]) == 12
        assert abs(float(r["p_v"]) + float(r["p_e"]) + float(r["p_d"]) - 1.0) < 1e-3  # arred. 4 casas no CSV

        # registro imutável: não duplica o mesmo jogo+versão
        dup = R.register(c, "Brazil", "Bolivia", "2026-06-20", path=path)
        assert dup.get("erro") == "já registrado (imutável)"

        # settle preenche uma vez; não repreenche
        s = R.settle("Brazil", "Bolivia", "2026-06-20", 3, 0, path=path)
        assert s["preenchidos"] == 1 and s["resultado"] == "V"
        assert R.settle("Brazil", "Bolivia", "2026-06-20", 3, 0, path=path)["preenchidos"] == 0

        rep = R.report(path=path)
        assert rep["n"] == 1 and rep["brier"] >= 0.0

        # a PREVISÃO permanece intacta após o settle (só resultado/brier são preenchidos)
        row = list(csv.DictReader(open(path, encoding="utf-8")))[0]
        assert row["p_v"] == r["p_v"] and row["resultado"] == "V" and row["brier"] != ""
    finally:
        if os.path.exists(path):
            os.remove(path)
        c.close()


def test_register_unknown_team_returns_error():
    c = _conn(); path = tempfile.mktemp(suffix=".csv")
    try:
        r = R.register(c, "Brasil", "Bolivia", "2026-06-20", path=path)   # 'Brasil' (pt) não existe
        assert r.get("erro") == "time não encontrado"
        assert not os.path.exists(path)        # nada gravado em caso de erro
    finally:
        if os.path.exists(path):
            os.remove(path)
        c.close()


def test_register_batch_and_settle_from_db():
    c = _conn(); path = tempfile.mktemp(suffix=".csv")
    try:
        real = c.execute("""SELECT m.date d, th.name h, ta.name a FROM matches m
                            JOIN teams th ON th.team_id=m.home_team_id
                            JOIN teams ta ON ta.team_id=m.away_team_id
                            WHERE th.name='Brazil' AND ta.name='Bolivia' LIMIT 1""").fetchone()
        fixtures = [{"home": real["h"], "away": real["a"], "date": real["d"]},     # já disputado
                    {"home": "Argentina", "away": "Brazil", "date": "2031-01-01"}]  # futuro
        rb = R.register_batch(c, fixtures, path=path)
        assert rb["registrados"] == 2
        assert R.register_batch(c, fixtures, path=path)["ja_existiam"] == 2   # idempotente
        sd = R.settle_from_db(c, path=path)
        assert sd["preenchidos"] == 1 and sd["abertas_restantes"] == 1       # só o disputado fecha
    finally:
        if os.path.exists(path):
            os.remove(path)
        c.close()
