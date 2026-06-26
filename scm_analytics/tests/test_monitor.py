"""Testes do monitor operacional — foco no novo bloco POR MERCADO (calibração + drift).

Instrumentação, não modelo (sem portão). Garante que o sinal de drift é POWER-AWARE:
não alarma com n pequeno, alarma só com gap real e n suficiente. Registro sintético em
CSV temporário (mesmo formato do registro-auto imutável); sem rede, sem DB.
"""
from __future__ import annotations

import csv

from scm import monitor

_COLS = ["data_jogo", "home", "away", "p_v", "p_e", "p_d", "p_over25",
         "p_btts", "resultado", "gols_home", "gols_away", "brier"]


def _row(pv, pe, pd, pov, pbtts, res, gh, ga):
    return {"data_jogo": "2026-06-20", "home": "A", "away": "B", "p_v": pv, "p_e": pe,
            "p_d": pd, "p_over25": pov, "p_btts": pbtts, "resultado": res,
            "gols_home": gh, "gols_away": ga, "brier": 0.1}


def _write(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=_COLS)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def _by_name(path):
    return {m["mercado"]: m for m in monitor.reliability_by_market(str(path))["markets"]}


def test_markets_present_and_outcomes_correct(tmp_path):
    reg = tmp_path / "reg.csv"
    # V (3x0): top pick acerta; 3 gols => over2.5 sim; away 0 => BTTS não
    _write(reg, [_row(0.8, 0.1, 0.1, 0.6, 0.4, "V", 3, 0) for _ in range(4)])
    m = _by_name(reg)
    assert set(m) == {"1X2 (top pick)", "Over 2.5", "BTTS"}
    assert m["1X2 (top pick)"]["obs"] == 1.0       # pick=V e resultado=V
    assert m["Over 2.5"]["obs"] == 1.0             # 3 gols > 2.5
    assert m["BTTS"]["obs"] == 0.0                 # away não marcou


def test_drift_is_power_aware_small_n(tmp_path):
    reg = tmp_path / "reg.csv"
    _write(reg, [_row(0.8, 0.1, 0.1, 0.6, 0.4, "V", 3, 0) for _ in range(4)])
    # n=4 < n_min: NUNCA alarma (não confunde ruído com deriva)
    assert all(x["flag"] == "n baixo" for x in monitor.reliability_by_market(str(reg))["markets"])


def test_drift_flags_real_miscalibration(tmp_path):
    reg = tmp_path / "reg.csv"
    # over2.5 previsto baixo (0.30) mas TODOS os 12 jogos vão a over => z grande => DRIFT
    _write(reg, [_row(0.5, 0.3, 0.2, 0.30, 0.5, "V", 3, 1) for _ in range(12)])
    m = _by_name(reg)
    assert m["Over 2.5"]["obs"] == 1.0
    assert m["Over 2.5"]["flag"] == "DRIFT"


def test_ok_when_calibrated(tmp_path):
    reg = tmp_path / "reg.csv"
    # BTTS previsto 0.5; 6 sim / 6 não => observado 0.5 == previsto => z~0 => ok
    rows = [_row(0.5, 0.3, 0.2, 0.5, 0.5, "V", 1, 1) for _ in range(6)] + \
           [_row(0.5, 0.3, 0.2, 0.5, 0.5, "V", 1, 0) for _ in range(6)]
    _write(reg, rows)
    assert _by_name(reg)["BTTS"]["flag"] == "ok"


def test_empty_registry_is_safe(tmp_path):
    reg = tmp_path / "reg.csv"
    _write(reg, [])
    out = monitor.reliability_by_market(str(reg))
    assert out["n"] == 0 and out["markets"] == []
