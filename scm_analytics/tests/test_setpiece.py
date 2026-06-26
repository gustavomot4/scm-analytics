"""Testes de setpiece — cartões/escanteios (D-72): histórico + baseline da competição.

Decisão (portão LOO): SEM previsão por seleção. O over/under é a MÉDIA da competição
(2·μ), não depende das taxas dos times — estes testes travam justamente isso.
"""
import math
import pytest
from scm.setpiece import match_setpiece, _pois_over, load_rates


def _data(mu_c=1.8, mu_k=4.5):
    return {"rates": {
        "brazil": {"name": "Brazil", "cards_for": 1.5, "cards_against": 2.0,
                   "corners_for": 7.0, "corners_against": 3.0, "n": 14},
        "argentina": {"name": "Argentina", "cards_for": 2.1, "cards_against": 2.9,
                      "corners_for": 5.5, "corners_against": 2.8, "n": 17}},
        "mu_cards": mu_c, "mu_corners": mu_k}


def test_none_when_team_missing_or_no_data():
    d = _data()
    assert match_setpiece("Brazil", "Narnia", d) is None
    assert match_setpiece("Narnia", "Brazil", d) is None
    assert match_setpiece("Brazil", "Argentina", None) is None


def test_descriptive_passthrough():
    sp = match_setpiece("Brazil", "Argentina", _data())
    assert sp["home"]["cards"] == 1.5 and sp["home"]["corners"] == 7.0 and sp["home"]["n"] == 14
    assert sp["away"]["cards"] == 2.1 and sp["away"]["n"] == 17


def test_overunder_is_competition_baseline_not_team():
    d = _data(mu_c=1.8, mu_k=4.5)
    sp = match_setpiece("Brazil", "Argentina", d)
    assert sp["media_jogo"]["cards"] == pytest.approx(3.6, abs=1e-9)     # 2·μ
    assert sp["media_jogo"]["corners"] == pytest.approx(9.0, abs=1e-9)
    # trocar a ORDEM/taxas dos times não muda o over/under -> prova de que é baseline, não por time
    sp2 = match_setpiece("Argentina", "Brazil", d)
    assert sp2["over_cards"] == sp["over_cards"] and sp2["over_corners"] == sp["over_corners"]


def test_over_lines_monotone_and_bounded():
    sp = match_setpiece("Brazil", "Argentina", _data())
    oc = [sp["over_cards"][k] for k in ("2.5", "3.5", "4.5", "5.5")]
    ok = [sp["over_corners"][k] for k in ("7.5", "8.5", "9.5", "10.5", "11.5")]
    assert all(oc[i] >= oc[i + 1] for i in range(len(oc) - 1))
    assert all(ok[i] >= ok[i + 1] for i in range(len(ok) - 1))
    assert all(0.0 <= v <= 1.0 for v in oc + ok)


def test_pois_over_matches_poisson():
    lam = 3.6
    assert _pois_over(lam, 0.5) == pytest.approx(1 - math.exp(-lam), abs=1e-12)      # over 0.5 = ≥1
    cdf3 = sum(math.exp(-lam) * lam ** k / math.factorial(k) for k in range(4))
    assert _pois_over(lam, 3.5) == pytest.approx(1 - cdf3, abs=1e-12)


def test_load_rates_missing_returns_none():
    assert load_rates("/nao/existe/setpiece.csv") is None
