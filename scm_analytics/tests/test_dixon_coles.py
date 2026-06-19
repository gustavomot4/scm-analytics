"""Testes do candidato Dixon-Coles (funções puras; o portão real roda no DB do usuário)."""
import pytest
from scm.dixon_coles import tau, dc_reads, _norm_const


def test_tau_identity_outside_low_scores():
    # τ = 1 fora das 4 células de placar baixo
    assert tau(2, 0, 1.4, 0.8, -0.1) == 1.0
    assert tau(3, 5, 1.4, 0.8, -0.1) == 1.0


def test_tau_rho_negative_boosts_draws():
    la, lb, rho = 1.3, 1.1, -0.10
    assert tau(0, 0, la, lb, rho) > 1.0     # reforça 0x0
    assert tau(1, 1, la, lb, rho) > 1.0     # reforça 1x1
    assert tau(0, 1, la, lb, rho) < 1.0     # corta 0x1
    assert tau(1, 0, la, lb, rho) < 1.0     # corta 1x0


def test_rho_zero_is_plain_poisson():
    r = dc_reads(1.5, 1.0, 0.0)
    assert _norm_const(1.5, 1.0, 0.0) == pytest.approx(1.0)
    assert r["pv"] + r["pe"] + r["pd"] == pytest.approx(1.0, abs=1e-4)  # truncamento da matriz em 10 gols (igual ao poisson_reads)


def test_reads_coherent_and_sum_one():
    for rho in (-0.12, -0.05, 0.0, 0.03):
        r = dc_reads(1.6, 0.9, rho)
        assert r["pv"] + r["pe"] + r["pd"] == pytest.approx(1.0, abs=1e-4)  # truncamento da matriz em 10 gols (igual ao poisson_reads)
        for k in ("pv", "pe", "pd", "btts"):
            assert 0.0 <= r[k] <= 1.0


def test_rho_negative_raises_draw_prob():
    # ρ<0 (correção DC) aumenta P(empate) vs Poisson independente
    base = dc_reads(1.4, 1.2, 0.0)["pe"]
    dc = dc_reads(1.4, 1.2, -0.10)["pe"]
    assert dc > base
