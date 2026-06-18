"""Testes de markets() — tudo derivado da mesma matriz Poisson."""
import math
import pytest
from scm.predictor import markets, poisson_reads, _pois


def test_over_under_complementary_and_monotone():
    mk = markets(1.6, 1.2)
    for ln in ("0.5", "1.5", "2.5", "3.5", "4.5"):
        assert mk["over"][ln] + mk["under"][ln] == pytest.approx(1.0, abs=1e-9)
    o = [mk["over"][l] for l in ("0.5", "1.5", "2.5", "3.5", "4.5")]
    assert all(o[i] >= o[i + 1] for i in range(len(o) - 1))   # over cai com a linha
    assert all(0.0 <= v <= 1.0 for v in o)


def test_first_to_score_competing_poisson():
    mk = markets(2.0, 0.8)
    f = mk["first_to_score"]
    assert f["a"] > f["b"]                                    # time mais ofensivo marca 1º mais
    assert f["a"] + f["b"] + f["none"] == pytest.approx(1.0, abs=1e-9)
    assert f["none"] == pytest.approx(math.exp(-(2.0 + 0.8)), abs=1e-9)
    # simétrico quando λ iguais
    s = markets(1.3, 1.3)["first_to_score"]
    assert s["a"] == pytest.approx(s["b"], abs=1e-9)


def test_clean_sheet_and_btts_match_poisson():
    la, lb = 1.7, 1.1
    mk = markets(la, lb)
    assert mk["clean_sheet_a"] == pytest.approx(_pois(0, lb), abs=1e-9)   # A não sofre = B faz 0
    assert mk["btts"] == pytest.approx(poisson_reads(la, lb)["btts"], abs=1e-9)


def test_total_goals_and_team_totals_sane():
    mk = markets(1.5, 1.5)
    assert sum(p for _, p in mk["total_goals"]) == pytest.approx(1.0, abs=2e-3)
    assert mk["team_a_over"]["0.5"] >= mk["team_a_over"]["1.5"] >= 0.0
    # over0.5 do time = 1 - P(0 gols) do time
    assert mk["team_a_over"]["0.5"] == pytest.approx(1 - _pois(0, 1.5), abs=1e-9)


def test_handicap_favorite_wins_by_two():
    mk = markets(2.4, 0.7)
    assert mk["handicap"]["a_-1.5"] > mk["handicap"]["b_-1.5"]    # favorito vence por 2+ mais
    assert 0.0 <= mk["handicap"]["a_-1.5"] <= 1.0
