"""Testes do predictor — reproduz execução manual + coerência + propagação."""
import pytest

from scm import db
from scm import elo_engine as elo
from scm import features_pit as fp
from scm import predictor as pred
from scm.predictor import PredictParams, poisson_reads, elo_direct_read, lambdas, predict


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


# ---------- reproduz execução manual (IRN x NZL, λ=1.40/0.78) ----------
def test_poisson_reproduces_manual():
    r = poisson_reads(1.40, 0.78)
    assert r["pv"] == pytest.approx(0.516, abs=0.004)
    assert r["pe"] == pytest.approx(0.275, abs=0.004)
    assert r["pd"] == pytest.approx(0.209, abs=0.004)
    assert r["over25"] == pytest.approx(0.372, abs=0.004)   # doc 0.371
    assert r["btts"] == pytest.approx(0.408, abs=0.004)
    assert r["top5"][0][0] == "1x0"                          # placar modal


def test_poisson_sums_to_one():
    r = poisson_reads(1.40, 0.78)
    assert r["pv"] + r["pe"] + r["pd"] == pytest.approx(1.0, abs=1e-3)


# ---------- coerência [0,1] ----------
def test_coherence_all_dr_sigma():
    p = PredictParams()
    for dr in (-600, -200, 0, 200, 600):
        for sigma in (10, 150, 300):
            r = predict(dr, sigma, p)
            for k in ("p_v", "p_e", "p_d"):
                assert 0.0 <= r[k] <= 1.0
            assert r["p_v"] + r["p_e"] + r["p_d"] == pytest.approx(1.0, abs=1e-9)
            assert r["band_pv_lo"] <= r["band_pv_hi"]


def test_draw_curve_coherent_extreme():
    # |dr| alto: P(D) não pode ficar negativo (cap da curva de empate)
    r = elo_direct_read(600, 50.0, PredictParams())
    assert r["pd"] >= 0.0 and r["pe"] >= 0.0 and r["pv"] <= 1.0


def test_lambda_floor():
    p = PredictParams()
    _, lb = lambdas(2000, p)        # dr enorme -> λ_B iria negativo sem piso
    assert lb == pytest.approx(p.lambda_min)


# ---------- propagação ----------
def test_propagation_shrinks_favorite():
    p = PredictParams()
    point = elo_direct_read(200, 0.0, p)["pv"]
    propagated = elo_direct_read(200, 150.0, p)["pv"]
    assert propagated < point        # Jensen: favorito encolhe sob incerteza


def test_band_brackets_point():
    p = PredictParams()
    r = elo_direct_read(150, 120.0, p)
    assert r["band_lo"] <= r["pv"] <= r["band_hi"]


# ---------- integração ----------
def test_run_integration(conn):
    _match(conn, "2018-06-20", "Spain", "Iran", 1, 0)
    _match(conn, "2021-07-10", "Argentina", "Brazil", 1, 0, "Copa América", neutral=0)
    _match(conn, "2022-12-18", "Argentina", "France", 3, 3)
    elo.run(conn)
    fp.run(conn)
    stats = pred.run(conn)
    assert stats["predictions"] == 3
    row = conn.execute("SELECT p_v, p_e, p_d FROM predictions LIMIT 1").fetchone()
    assert row["p_v"] + row["p_e"] + row["p_d"] == pytest.approx(1.0, abs=1e-9)


def test_run_idempotent(conn):
    _match(conn, "2018-06-20", "Spain", "Iran", 1, 0)
    elo.run(conn)
    fp.run(conn)
    pred.run(conn)
    pred.run(conn)                   # de novo: não duplica (PK match_id+versao)
    assert conn.execute("SELECT COUNT(*) FROM predictions").fetchone()[0] == 1


def test_run_applies_altitude(conn):
    # mesmo dr/σ, mas um jogo em La Paz (altitude) e outro ao nível do mar
    for date, city in [("2013-03-22", "La Paz"), ("2013-06-01", "Rio")]:
        h = db.get_or_create_team(conn, "Bolivia"); a = db.get_or_create_team(conn, "Brazil")
        conn.execute("""INSERT INTO matches (date,home_team_id,away_team_id,home_score,away_score,
                        tournament,city,neutral,natural_key) VALUES (?,?,?,?,?,?,?,0,?)""",
                     (date, h, a, 1, 1, "FIFA World Cup qualification", city, f"{date}|BOL|BRA|{city}"))
    conn.commit()
    elo.run(conn); fp.run(conn); pred.run(conn)
    pv = dict(conn.execute("""SELECT m.city, p.p_v FROM predictions p JOIN matches m USING(match_id)
                              WHERE p.versao_modelo=?""", (pred.MODEL_VERSION,)).fetchall())
    # em La Paz a Bolívia (mandante adaptada) deve ter P(V) MAIOR que no Rio
    assert pv["La Paz"] > pv["Rio"]
