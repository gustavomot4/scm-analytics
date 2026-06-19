"""Testes do report — reliability, ECE, cobertura de banda."""
import pytest

from scm import db
from scm import elo_engine as elo
from scm import features_pit as fp
from scm import predictor as pred
from scm import report


def test_reliability_bins():
    items = [{"p_v": 0.75, "lo": 0.6, "hi": 0.9, "home_won": 1 if i < 75 else 0} for i in range(100)]
    bins = report.reliability_bins(items, n_bins=10)
    b7 = [x for x in bins if x["bin"] == 7][0]
    assert b7["pred_mean"] == pytest.approx(0.75)
    assert b7["obs_freq"] == pytest.approx(0.75)
    assert b7["n"] == 100


def test_calibration_error_zero_when_calibrated():
    items = [{"p_v": 0.5, "lo": 0.3, "hi": 0.7, "home_won": i % 2} for i in range(100)]
    assert report.calibration_error(items) == pytest.approx(0.0, abs=0.02)


def test_calibration_error_high_when_miscalibrated():
    # prevê 0.9 mas ninguém ganha -> erro ~0.9
    items = [{"p_v": 0.9, "lo": 0.85, "hi": 0.95, "home_won": 0} for _ in range(50)]
    assert report.calibration_error(items) > 0.8


def test_band_coverage_inside():
    items = [{"p_v": 0.5, "lo": 0.3, "hi": 0.7, "home_won": 1 if i < 50 else 0} for i in range(100)]
    c = report.band_coverage(items)
    assert c["obs_in_mean_band"] is True
    assert c["mean_band_width"] == pytest.approx(0.4)


def test_band_coverage_outside():
    items = [{"p_v": 0.9, "lo": 0.85, "hi": 0.95, "home_won": 0} for _ in range(50)]
    assert report.band_coverage(items)["obs_in_mean_band"] is False


def test_summary_integration():
    c = db.connect(":memory:"); db.init_schema(c)
    def M(date, h, a, hs, as_, t="FIFA World Cup", neutral=1):
        hi = db.get_or_create_team(c, h); ai = db.get_or_create_team(c, a)
        c.execute("""INSERT INTO matches (date,home_team_id,away_team_id,home_score,away_score,
                     tournament,neutral,natural_key) VALUES (?,?,?,?,?,?,?,?)""",
                  (date, hi, ai, hs, as_, t, neutral, f"{date}|{h}|{a}|{t}")); c.commit()
    M("2018-06-20", "Spain", "Iran", 1, 0)
    M("2021-07-10", "Argentina", "Brazil", 1, 0, "Copa América", 0)
    M("2022-12-18", "Argentina", "France", 3, 3)
    elo.run(c); fp.run(c); pred.run(c)
    s = report.summary(c, pred.MODEL_VERSION)
    assert s["metrics"]["n"] == 3
    assert "coverage" in s and "reliability" in s
    c.close()


def test_band_coverage_binned():
    # faixa 0.5 com banda larga contendo a freq observada -> coberta;
    # faixa 0.9 superconfiante com banda estreita e obs 0 -> fora.
    items = [{"p_v": 0.5, "lo": 0.3, "hi": 0.7, "home_won": 1 if i < 50 else 0} for i in range(100)]
    items += [{"p_v": 0.9, "lo": 0.88, "hi": 0.92, "home_won": 0} for _ in range(40)]
    cb = report.band_coverage_binned(items)
    assert cb["n_bins"] >= 2
    b5 = [r for r in cb["bins"] if r["bin"] == 5][0]
    b9 = [r for r in cb["bins"] if r["bin"] == 9][0]
    assert b5["in_band"] is True
    assert b9["in_band"] is False
    assert 0.0 <= cb["coverage_weighted"] <= 1.0
