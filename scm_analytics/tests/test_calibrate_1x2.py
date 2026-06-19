"""Testes do candidato de recalibração 1X2 (funções puras; portão real roda no DB)."""
import pytest
from scm.calibrate_1x2 import temperature, fit_isotonic, apply_isotonic


def test_temperature_identity_at_one():
    p = [0.6, 0.25, 0.15]
    q = temperature(p, 1.0)
    assert q == pytest.approx(p, abs=1e-9)


def test_temperature_softens_with_T_gt_1():
    p = [0.85, 0.10, 0.05]
    q = temperature(p, 1.3)        # T>1 reduz a confiança do favorito
    assert q[0] < p[0] and abs(sum(q) - 1.0) < 1e-9


def test_isotonic_is_monotonic_and_in_range():
    cal = fit_isotonic([(0.1, 0.0), (0.2, 0.0), (0.4, 1.0), (0.5, 0.0), (0.8, 1.0)])
    ys = [apply_isotonic(cal, x) for x in (0.05, 0.15, 0.3, 0.45, 0.6, 0.9)]
    assert all(ys[i] <= ys[i + 1] + 1e-9 for i in range(len(ys) - 1))   # não-decrescente
    assert all(0.0 <= y <= 1.0 for y in ys)
