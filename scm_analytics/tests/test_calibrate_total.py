"""Testes do calibrate_total — calibra T_base na métrica de BTTS/over."""
import pytest
from scm import db
from scm import calibrate_total as ct


def test_eval_returns_sane_rates():
    rows = [{"hs": 2, "s": 1, "dr": 50, "sg": 120, "t": "x"} for _ in range(20)]
    e = ct._eval(rows, 2.6)
    assert e["n"] == 20
    assert 0.0 < e["btts_pred"] < 1.0 and 0.0 < e["over_pred"] < 1.0
    assert "btts_bias" in e and "brier1x2" in e


def test_lower_tbase_lowers_btts_and_over():
    rows = [{"hs": 1, "s": 1, "dr": 0, "sg": 100, "t": "x"} for _ in range(10)]
    hi = ct._eval(rows, 2.7)
    lo = ct._eval(rows, 2.3)
    assert lo["btts_pred"] < hi["btts_pred"]      # menos gols -> menos ambos-marcam
    assert lo["over_pred"] < hi["over_pred"]       # e menos over


def test_calibrate_total_graceful_without_data():
    c = db.connect(":memory:"); db.init_schema(c)
    r = ct.calibrate_total(c, only_major=False)
    assert "best_t_base" not in r                  # sem features -> não quebra
    c.close()
