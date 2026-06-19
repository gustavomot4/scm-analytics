"""Testes da Camada 3 — desfalques direcionais (P-F/D-41)."""
import pytest

from scm import db
from scm import elo_engine as elo
from scm import predict_match as pm
from scm.desfalques import team_penalty, match_deltas


def test_team_penalty_tiers_ordered():
    chave = team_penalty([{"setor": "defesa", "tier": "chave"}])[0]
    imp = team_penalty([{"setor": "defesa", "tier": "importante"}])[0]
    rod = team_penalty([{"setor": "defesa", "tier": "rodizio"}])[0]
    assert chave > imp > rod > 0


def test_match_deltas_directions():
    # ataque do mandante fora -> GD cai; defesa do visitante fora -> dr sobe
    ddr, dgd = match_deltas([{"setor": "ataque", "tier": "chave"}],
                            [{"setor": "defesa", "tier": "importante"}])
    assert dgd < 0 and ddr > 0
    # simétrico: zerar tudo -> deltas nulos
    assert match_deltas([], []) == (0.0, 0.0)


def test_setor_desconhecido_nao_inventa_efeito():
    assert team_penalty([{"setor": "massagista", "tier": "chave"}]) == (0.0, 0.0)


def _conn():
    c = db.connect(":memory:"); db.init_schema(c)

    def M(date, h, a, hs, as_):
        hi = db.get_or_create_team(c, h); ai = db.get_or_create_team(c, a)
        c.execute("""INSERT INTO matches(date,home_team_id,away_team_id,home_score,away_score,
                     tournament,neutral,natural_key) VALUES (?,?,?,?,?,?,1,?)""",
                  (date, hi, ai, hs, as_, "FIFA World Cup", f"{date}|{h}|{a}"))
    for k in range(12):
        M(f"201{k % 9}-06-{(k % 27) + 1:02d}", "Brazil", "Bolivia", 3, 0)
        M(f"201{k % 9}-09-{(k % 27) + 1:02d}", "Argentina", "Brazil", 1, 1)
    c.commit(); elo.run(c)
    return c


def test_predict_match_applies_attack_absence():
    c = _conn()
    base = pm.predict_match(c, "Brazil", "Bolivia")
    out = pm.predict_match(c, "Brazil", "Bolivia",
                           desfalques={"home": [{"setor": "ataque", "tier": "chave"}], "away": []})
    c.close()
    assert out["lambda_a"] < base["lambda_a"]      # Brasil sem atacante-chave marca menos
    assert out["p_v"] < base["p_v"]
    assert out["p_v"] + out["p_e"] + out["p_d"] == pytest.approx(1.0, abs=1e-9)
