"""Testes do candidato σ-Glicko (P-B/D-42): RD estilo Glicko-1, varia por seleção."""
import pytest

from scm import db
from scm import elo_engine as elo
from scm import sigma_glicko as SG


def test_g_decreasing_with_rd():
    assert SG._g(0.0) == pytest.approx(1.0, abs=1e-6)
    assert SG._g(50) > SG._g(150) > SG._g(350)


def test_inflate_grows_with_inactivity_and_caps():
    assert SG._inflate(50.0, 0.0) == pytest.approx(50.0)
    assert SG._inflate(50.0, 12.0) > 50.0                  # 1 ano parado -> RD sobe
    assert SG._inflate(300.0, 999.0) <= SG.RD_MAX + 1e-9   # teto


def test_run_produces_varying_rd():
    c = db.connect(":memory:"); db.init_schema(c)

    def M(date, h, a, hs, as_):
        hi = db.get_or_create_team(c, h); ai = db.get_or_create_team(c, a)
        c.execute("""INSERT INTO matches(date,home_team_id,away_team_id,home_score,away_score,
                     tournament,neutral,natural_key) VALUES (?,?,?,?,?,?,1,?)""",
                  (date, hi, ai, hs, as_, "FIFA World Cup", f"{date}|{h}|{a}"))
    # 'Ativa' joga muito; 'Rara' joga pouco e some -> RDs diferentes
    for k in range(15):
        M(f"2018-{(k % 12) + 1:02d}-{(k % 27) + 1:02d}", "Ativa", f"X{k}", 2, 0)
    M("2014-01-01", "Rara", "X0", 1, 1)
    M("2014-02-01", "Rara", "X1", 0, 0)
    c.commit(); elo.run(c)
    rd = SG.run(c)
    ativa = db.get_or_create_team(c, "Ativa"); rara = db.get_or_create_team(c, "Rara")
    c.close()
    assert rd[ativa] != rd[rara]                 # RD varia entre seleções (≠ σ_r fixo)
    assert rd[rara] > rd[ativa]                  # quem some há anos tem RD maior
    assert all(SG.RD_FLOOR <= v <= SG.RD_MAX for v in rd.values())
