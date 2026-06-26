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


# --- mercados NOVOS (expansão 2026-06-25): partições, par/ímpar, win-to-nil, grade, retrocompat ---
def test_extended_over_lines_and_oddeven():
    mk = markets(1.9, 1.3)
    lines = ("0.5", "1.5", "2.5", "3.5", "4.5", "5.5", "6.5")
    for ln in lines:
        assert mk["over"][ln] + mk["under"][ln] == pytest.approx(1.0, abs=1e-9)
    o = [mk["over"][l] for l in lines]
    assert all(o[i] >= o[i + 1] for i in range(len(o) - 1))
    assert mk["odd_even"]["odd"] + mk["odd_even"]["even"] == pytest.approx(1.0, abs=1e-9)


def test_partitions_sum_to_one():
    mk = markets(1.6, 1.2)
    assert sum(mk["total_exato"].values()) == pytest.approx(1.0, abs=1e-3)
    assert sum(mk["win_margin"].values()) == pytest.approx(1.0, abs=1e-3)
    assert sum(mk["result_btts"].values()) == pytest.approx(1.0, abs=1e-3)
    assert sum(mk["result_over25"].values()) == pytest.approx(1.0, abs=1e-3)
    assert mk["dnb"]["a"] + mk["dnb"]["b"] == pytest.approx(1.0, abs=1e-9)


def test_zero_zero_consistency():
    la, lb = 1.4, 1.1
    mk = markets(la, lb)
    assert mk["result_btts"]["draw_no"] == pytest.approx(_pois(0, la) * _pois(0, lb), abs=1e-9)


def test_win_to_nil_bounds():
    mk = markets(2.4, 0.7)
    assert mk["win_to_nil"]["a"] > mk["win_to_nil"]["b"]            # favorito vence sem sofrer mais
    assert mk["win_to_nil"]["a"] <= mk["double_chance"]["12"]       # vencer-sem-sofrer ⊆ "algum vence"
    assert mk["win_to_nil"]["a"] <= mk["double_chance"]["1X"]


def test_multigols_and_score_grid_shape():
    mk = markets(1.5, 1.5)
    assert all(0.0 <= v <= 1.0 for v in mk["multigols"].values())
    g = mk["score_grid"]
    assert len(g) == 6 and all(len(r) == 6 for r in g)
    assert 0.0 < sum(sum(r) for r in g) <= 1.0 + 1e-9


def test_backward_compat_keys_present():
    mk = markets(1.5, 1.2)
    for k in ("over", "under", "btts", "team_a_over", "team_b_over", "clean_sheet_a",
              "clean_sheet_b", "double_chance", "handicap", "first_to_score", "total_goals"):
        assert k in mk
    assert "a_-1.5" in mk["handicap"] and "b_-1.5" in mk["handicap"]
    assert "1X" in mk["double_chance"]
