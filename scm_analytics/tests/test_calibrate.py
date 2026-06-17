"""Testes do calibrate — split treino/teste, grid (best ≤ placeholder no treino), portão."""
import random
import pytest

from scm import db
from scm import elo_engine as elo
from scm import features_pit as fp
from scm import calibrate as cal


@pytest.fixture
def conn_with_data():
    c = db.connect(":memory:"); db.init_schema(c)
    rng = random.Random(3)
    teams = [f"T{i}" for i in range(8)]
    strength = {t: rng.gauss(0, 200) for t in teams}
    for k in range(84):
        a, b = rng.sample(teams, 2)
        pa = 1 / (1 + 10 ** (-(strength[a] - strength[b]) / 400))
        r = rng.random()
        hs, as_ = (1, 0) if r < pa * 0.8 else ((1, 1) if r < pa * 0.8 + 0.2 else (0, 1))
        date = f"{2008 + k // 6:04d}-{(k % 12) + 1:02d}-{(k % 28) + 1:02d}"
        ai = db.get_or_create_team(c, a); bi = db.get_or_create_team(c, b)
        c.execute("""INSERT OR IGNORE INTO matches (date,home_team_id,away_team_id,home_score,
                     away_score,tournament,neutral,natural_key) VALUES (?,?,?,?,?,?,1,?)""",
                  (date, ai, bi, hs, as_, "FIFA World Cup", f"{date}|{a}|{b}"))
    c.commit()
    elo.run(c); fp.run(c)
    yield c
    c.close()


def test_split_nonempty(conn_with_data):
    tr = cal.load_rows(conn_with_data, before="2018-01-01")
    te = cal.load_rows(conn_with_data, after="2018-01-01")
    assert len(tr) > 0 and len(te) > 0


def test_calibrate_train_not_worse_than_placeholder(conn_with_data):
    r = cal.calibrate(conn_with_data, "2018-01-01", S=16, B=300)
    # o grid inclui os placeholders -> o melhor do treino não pode ser pior
    assert r["brier_train_calib"] <= r["brier_train_placeholder"] + 1e-9
    assert set(r["best"]) == {"theta_gd", "kappa_tm", "t_base", "draw_base", "w_poisson"}
    assert isinstance(r["adota"], bool)
    assert r["n_train"] > 0 and r["n_test"] > 0


def test_gate_decides_adoption(conn_with_data):
    r = cal.calibrate(conn_with_data, "2018-01-01", S=16, B=300)
    # adota sse IC do ganho no teste não cruza zero (lo>0)
    assert r["adota"] == (r["ic_lo"] > 0)
