"""Testes do simulador de torneio (Monte Carlo) — invariantes estruturais."""
import json, tempfile, os
import pytest
from scm import db
from scm import simulate as sim


def _db48():
    """DB em memória com 48 seleções (Elo decrescente) -> 12 grupos de 4."""
    c = db.connect(":memory:"); db.init_schema(c)
    names = [f"T{i:02d}" for i in range(48)]
    for i, n in enumerate(names):
        tid = db.get_or_create_team(c, n)
        c.execute("INSERT INTO ratings_current(team_id,elo,sigma_r,n_games,provisional) VALUES (?,?,?,?,0)",
                  (tid, 2100 - i * 12, 40.0, 100))
    c.commit()
    groups = {chr(65 + g): [names[g + 12 * pot] for pot in range(4)] for g in range(12)}
    return c, groups, names


def _write_cfg(groups, hosts=None):
    fd, path = tempfile.mkstemp(suffix=".json"); os.close(fd)
    json.dump({"groups": groups, "hosts": hosts or {}}, open(path, "w"))
    return path


def test_validate_flags_problems():
    elos = {"A": 1500}
    probs = sim.validate({"A": ["A", "B"]}, elos)         # 1 grupo, 2 times, sem Elo
    assert any("12 grupos" in p for p in probs)
    assert any("seleções" in p for p in probs)


def test_champion_and_advance_invariants():
    c, groups, names = _db48()
    path = _write_cfg(groups)
    res = sim.run(c, path, n_sims=400, seed=1)
    os.remove(path); c.close()
    s_ch = sum(r["p_champion"] for r in res["table"])
    s_adv = sum(r["p_advance"] for r in res["table"])
    assert s_ch == pytest.approx(1.0, abs=1e-9)            # 1 campeão por torneio
    assert s_adv == pytest.approx(32.0, abs=1e-9)          # 32 avançam ao mata-mata
    assert len(res["table"]) == 48


def test_stronger_team_more_likely_champion():
    c, groups, names = _db48()
    path = _write_cfg(groups)
    res = sim.run(c, path, n_sims=1500, seed=2)
    os.remove(path); c.close()
    p = {r["team"]: r["p_champion"] for r in res["table"]}
    assert p["T00"] > p["T47"]                              # mais forte > mais fraco
    assert res["table"][0]["p_champion"] >= res["table"][-1]["p_champion"]


def test_host_bonus_helps():
    c, groups, names = _db48()
    # dá mando alto a um time mediano e vê a chance subir vs sem mando
    base = sim.run(c, _write_cfg(groups), n_sims=1200, seed=3)
    pb = {r["team"]: r["p_champion"] for r in base["table"]}
    boosted = sim.run(c, _write_cfg(groups, hosts={"T30": 300}), n_sims=1200, seed=3)
    ph = {r["team"]: r["p_champion"] for r in boosted["table"]}
    c.close()
    assert ph["T30"] > pb["T30"]                            # mando aumenta a chance
