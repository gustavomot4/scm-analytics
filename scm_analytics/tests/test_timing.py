"""Testes de timing — tempo do gol (D-71). Curva sintética determinística + módulo real.

Modelo: processo de Poisson não-homogêneo. Não toca em λ/1X2 (releitura).
"""
import math
import pytest
from scm.timing import timing_markets, _parse_minute, _ht_result, load_curve


def _curve(f45=0.5):
    # CDF linear F(t)=t/90 (gols uniformes no tempo) -> f45=0.5; determinístico p/ checagem
    return {"cdf": [t / 90.0 for t in range(1, 91)], "f45": f45, "n_goals": 1000, "source": "synthetic"}


def test_first_band_plus_no_goal_is_one():
    tm = timing_markets(1.4, 1.1, _curve())
    assert sum(tm["first_band"].values()) + tm["no_goal"] == pytest.approx(1.0, abs=1e-9)


def test_no_goal_is_poisson_zero():
    la, lb = 1.3, 0.9
    assert timing_markets(la, lb, _curve())["no_goal"] == pytest.approx(math.exp(-(la + lb)), abs=1e-12)


def test_both_halves_is_product_independent():
    tm = timing_markets(1.7, 1.2, _curve())
    assert tm["both_halves"] == pytest.approx(tm["goal_1h"] * tm["goal_2h"], abs=1e-12)


def test_symmetric_halves_when_f45_half():
    tm = timing_markets(2.0, 0.6, _curve(0.5))           # f45=0.5 => intensidade igual nos 2 tempos
    assert tm["goal_1h"] == pytest.approx(tm["goal_2h"], abs=1e-12)


def test_before_monotone_and_equals_goal_1h_at_45():
    tm = timing_markets(1.5, 1.5, _curve())
    assert tm["before"]["15"] <= tm["before"]["30"] <= tm["before"]["45"]
    assert tm["before"]["45"] == pytest.approx(tm["goal_1h"], abs=1e-12)


def test_ht_result_sums_to_one_and_favorite_leads():
    ht = timing_markets(1.8, 1.0, _curve())["ht"]
    assert ht["home"] + ht["draw"] + ht["away"] == pytest.approx(1.0, abs=1e-9)
    assert ht["home"] > ht["away"]
    assert _ht_result(0.0, 0.0)["draw"] == pytest.approx(1.0, abs=1e-12)   # 0x0 sempre empate no HT


def test_parse_minute():
    assert _parse_minute("23") == 23
    assert _parse_minute("67") == 67
    assert _parse_minute("45+2") == 45      # acréscimos do 1ºT -> 45
    assert _parse_minute("90+3") == 90      # acréscimos do 2ºT -> 90
    assert _parse_minute("120") == 90       # prorrogação capada
    assert _parse_minute("") is None
    assert _parse_minute("x") is None


def test_load_curve_missing_returns_none():
    assert load_curve("/nao/existe/goal_timing.json") is None
