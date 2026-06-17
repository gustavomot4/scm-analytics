"""Testes do backtest_harness — métricas, portão (aceita/rejeita) e determinismo."""
import math
import pytest

from scm import db
from scm import elo_engine as elo
from scm import features_pit as fp
from scm import predictor as pred
from scm import backtest_harness as bh
from scm.backtest_harness import brier, logloss, rps, gate, UNIFORM, outcome_of


@pytest.fixture
def conn():
    c = db.connect(":memory:")
    db.init_schema(c)
    yield c
    c.close()


def _match(conn, date, home, away, hs, as_, tournament="FIFA World Cup", neutral=1):
    h = db.get_or_create_team(conn, home)
    a = db.get_or_create_team(conn, away)
    conn.execute(
        """INSERT INTO matches (date, home_team_id, away_team_id, home_score, away_score,
                                tournament, neutral, natural_key)
           VALUES (?,?,?,?,?,?,?,?)""",
        (date, h, a, hs, as_, tournament, neutral, f"{date}|{home}|{away}|{tournament}"),
    )
    conn.commit()


# ---------- métricas (valores à mão) ----------
def test_brier_known():
    assert brier({"p_v": 1, "p_e": 0, "p_d": 0}, "V") == 0.0
    assert brier(UNIFORM, "V") == pytest.approx(2 / 3, abs=1e-9)        # 0.6667
    assert brier({"p_v": 0, "p_e": 0, "p_d": 1}, "V") == pytest.approx(2.0)  # pior caso


def test_logloss_rps_known():
    assert logloss({"p_v": 1, "p_e": 0, "p_d": 0}, "V") == pytest.approx(0.0, abs=1e-9)
    assert logloss(UNIFORM, "E") == pytest.approx(math.log(3), abs=1e-9)
    assert rps({"p_v": 1, "p_e": 0, "p_d": 0}, "V") == pytest.approx(0.0)


def test_outcome_of():
    assert outcome_of(2, 0) == "V" and outcome_of(1, 1) == "E" and outcome_of(0, 1) == "D"


# ---------- portão ----------
def test_gate_accepts_informative():
    import random
    rng = random.Random(7)
    deltas = [0.05 + rng.gauss(0, 0.01) for _ in range(200)]   # ganho consistente
    g = gate(deltas)
    assert g["keep"] is True and g["ic_lo"] > 0


def test_gate_rejects_null():
    import random
    rng = random.Random(7)
    deltas = [rng.gauss(0, 0.05) for _ in range(200)]          # ruído em torno de zero
    g = gate(deltas)
    assert g["keep"] is False and g["ic_lo"] < 0 < g["ic_hi"]


def test_gate_deterministic():
    deltas = [0.01 * i for i in range(-50, 51)]
    assert gate(deltas, seed=42) == gate(deltas, seed=42)      # mesma seed -> mesmo IC


# ---------- integração ----------
def test_evaluate_integration(conn):
    _match(conn, "2018-06-20", "Spain", "Iran", 1, 0)
    _match(conn, "2021-07-10", "Argentina", "Brazil", 1, 0, "Copa América", neutral=0)
    _match(conn, "2022-12-18", "Argentina", "France", 3, 3)
    elo.run(conn); fp.run(conn); pred.run(conn)
    m = bh.evaluate(conn, pred.MODEL_VERSION, B=2000)
    assert m["n"] == 3
    assert 0.0 <= m["brier"] <= 2.0
    assert "bate_uniforme_com_ic" in m            # invariante calculado (valor depende dos dados)
