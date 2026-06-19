"""Testes da interface web (Flask test_client)."""
import pytest

from scm import db
from scm import elo_engine as elo
from scm import web


@pytest.fixture
def app(tmp_path):
    dbp = tmp_path / "w.sqlite"
    c = db.connect(str(dbp)); db.init_schema(c)
    for k in range(10):
        for h, a, hs, as_ in [("Brazil", "Bolivia", 3, 0), ("Argentina", "Brazil", 1, 1)]:
            hi = db.get_or_create_team(c, h); ai = db.get_or_create_team(c, a)
            c.execute("""INSERT OR IGNORE INTO matches (date,home_team_id,away_team_id,home_score,
                         away_score,tournament,city,neutral,natural_key) VALUES (?,?,?,?,?,?,?,1,?)""",
                      (f"201{k}-06-01", hi, ai, hs, as_, "FIFA World Cup", "Rio", f"201{k}|{h}|{a}"))
    c.commit(); elo.run(c); c.close()
    return web.create_app(str(dbp))


def test_teams_endpoint(app):
    d = app.test_client().get("/api/teams").get_json()
    assert "Brazil" in d["teams"] and d["model"].startswith("baseline")


def test_predict_endpoint(app):
    d = app.test_client().get("/api/predict?home=Brazil&away=Bolivia").get_json()
    assert d["p_v"] + d["p_e"] + d["p_d"] == pytest.approx(1.0, abs=1e-9)
    assert d["p_v"] > d["p_d"] and len(d["scores"]) == 5


def test_predict_unknown_team(app):
    d = app.test_client().get("/api/predict?home=Nope&away=Bolivia").get_json()
    assert "erro" in d


def test_index_page(app):
    html = app.test_client().get("/").get_data(as_text=True)
    assert "Prever um confronto" in html and "SCM Analytics" in html


def test_api_predict_includes_knockout():
    import json
    from scm import db, elo_engine as elo, features_pit as fp, predictor as pred
    from scm.web import create_app
    c = db.connect(":memory:"); db.init_schema(c)
    def M(date, h, a, hs, as_):
        hi = db.get_or_create_team(c, h); ai = db.get_or_create_team(c, a)
        c.execute("INSERT INTO matches (date,home_team_id,away_team_id,home_score,away_score,"
                  "tournament,neutral,natural_key) VALUES (?,?,?,?,?,?,?,?)",
                  (date, hi, ai, hs, as_, "Friendly", 0, f"{date}|{h}|{a}")); c.commit()
    for i in range(8):
        M(f"201{i}-03-01", "Spain", "Malta", 3, 0)
        M(f"201{i}-06-01", "Malta", "Spain", 0, 2)
    elo.run(c); fp.run(c); pred.run(c)
    # grava num arquivo temporário p/ o app abrir
    import tempfile, os
    fd, path = tempfile.mkstemp(suffix=".sqlite"); os.close(fd)
    disk = db.connect(path); c.backup(disk); disk.close(); c.close()
    app = create_app(path); cli = app.test_client()
    d = json.loads(cli.get("/api/predict?home=Spain&away=Malta").data)
    os.remove(path)
    assert "knockout" in d and abs(d["knockout"]["adv_a"] + d["knockout"]["adv_b"] - 1.0) < 1e-9
