"""Testes do prior ataque/defesa não-Elo (P-A)."""
from dataclasses import replace

import pytest

from scm import db
from scm import elo_engine as elo
from scm.attack_defense import run_pit, fit, team_lambdas
from scm.predictor import predict, PredictParams


@pytest.fixture
def conn():
    c = db.connect(":memory:"); db.init_schema(c)

    def M(date, h, a, hs, as_, neutral=1, t="FIFA World Cup"):
        hi = db.get_or_create_team(c, h); ai = db.get_or_create_team(c, a)
        c.execute(
            """INSERT INTO matches(date,home_team_id,away_team_id,home_score,away_score,
               tournament,neutral,natural_key) VALUES (?,?,?,?,?,?,?,?)""",
            (date, hi, ai, hs, as_, t, neutral, f"{date}|{h}|{a}"))
    for k in range(15):
        M(f"20{10 + k:02d}-06-01", "Brazil", "Bolivia", 4, 0)
        M(f"20{10 + k:02d}-09-01", "Bolivia", "Brazil", 0, 3)
    c.commit(); elo.run(c)
    yield c
    c.close()


def test_pit_lambdas_positive(conn):
    pit = run_pit(conn)
    assert pit
    for la, lb in pit.values():
        assert la > 0 and lb > 0           # λ sempre positivos (clamp)


def test_strong_team_attacks_more(conn):
    atk, dfn = fit(conn)
    bid = db.get_or_create_team(conn, "Brazil")
    vid = db.get_or_create_team(conn, "Bolivia")
    assert atk[bid] > atk[vid]             # Brasil marca muito mais -> atk maior
    la, lb = team_lambdas(atk, dfn, bid, vid, neutral=True)
    assert la > lb                         # Brasil marca mais que a Bolívia


def test_ad_off_is_identical():
    """w_ad=0 (default): passar ad_ved NÃO muda nada (sem regressão no modelo validado)."""
    base = predict(200.0, 80.0)
    with_ad0 = predict(200.0, 80.0, ad_ved=(0.2, 0.3, 0.5))
    assert base["p_v"] == pytest.approx(with_ad0["p_v"], abs=1e-12)
    assert base["p_e"] == pytest.approx(with_ad0["p_e"], abs=1e-12)


def test_ad_on_changes_and_coherent():
    """w_ad>0: a perna AD muda o 1X2 e mantém coerência [0,1]/soma 1."""
    p = replace(PredictParams(), w_ad=0.40)
    base = predict(200.0, 80.0, PredictParams())
    on = predict(200.0, 80.0, p, ad_ved=(0.2, 0.3, 0.5))
    assert abs(on["p_v"] - base["p_v"]) > 1e-6
    assert on["p_v"] + on["p_e"] + on["p_d"] == pytest.approx(1.0, abs=1e-9)
    for k in ("p_v", "p_e", "p_d"):
        assert 0.0 <= on[k] <= 1.0


def test_xg_priors_empty_and_noop(conn):
    """Sem team_xg: xg_priors vazio e priors={} é IDÊNTICO a sem priors (no-regression, D-67)."""
    from scm.attack_defense import xg_priors, run_pit
    assert xg_priors(conn) == {}
    assert run_pit(conn) == run_pit(conn, priors={})
