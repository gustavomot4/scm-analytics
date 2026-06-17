"""Testes do calor (E3) — WBGT, redução do total e o portão (climatologia injetada)."""
import pytest

from scm import db
from scm import elo_engine as elo
from scm import features_pit as fp
from scm import heat
from scm.predictor import predict, PredictParams


def test_wbgt_monotonic_and_excess():
    assert heat.wbgt(40, 60) > heat.wbgt(40, 30) > heat.wbgt(20, 30)   # sobe com umidade e temp
    assert heat.excesso(20, 50) == 0.0                                  # ameno: sem excesso
    assert heat.excesso(42, 50) > 0.0                                   # quente: excesso > 0


def test_heat_reduces_total():
    p = PredictParams()
    base = predict(0.0, 50.0, p, heat_factor=1.0)
    hot = predict(0.0, 50.0, p, heat_factor=0.85)
    assert hot["lambda_a"] < base["lambda_a"]          # menos gols
    assert hot["p_over25"] < base["p_over25"]           # menos over 2.5


def test_match_excesso_lookup():
    clima = {"Doha": {"06": [42.0, 45.0]}, "Oslo": {"06": [18.0, 60.0]}}
    assert heat.match_excesso(clima, "Doha", "06") > 0
    assert heat.match_excesso(clima, "Oslo", "06") == 0.0
    assert heat.match_excesso(clima, "Cidade X", "06") == 0.0           # sem climatologia


def test_gate_heat_runs_with_injected_climatology():
    c = db.connect(":memory:"); db.init_schema(c)
    clima = {"Doha": {"06": [42.0, 45.0]}}      # quente
    def M(date, home, away, hs, as_, city):
        hi = db.get_or_create_team(c, home); ai = db.get_or_create_team(c, away)
        c.execute("""INSERT INTO matches (date,home_team_id,away_team_id,home_score,away_score,
                     tournament,city,neutral,natural_key) VALUES (?,?,?,?,?,?,?,1,?)""",
                  (date, hi, ai, hs, as_, "Friendly", city, f"{date}|{home}|{away}"))
    teams = ["A", "B", "C", "D"]
    for k in range(40):  # jogos em Doha (junho) espalhados 2010..2017 (cruza o cutoff 2014)
        a, b = teams[k % 4], teams[(k + 1) % 4]
        M(f"{2010 + k % 8:04d}-06-{(k % 27) + 1:02d}", a, b, k % 3, (k + 1) % 2, "Doha")
    c.commit()
    elo.run(c); fp.run(c)
    r = heat.gate_heat(c, clima=clima, B=300)
    assert r["n_hot"] == 40           # todos quentes (Doha junho)
    assert "keep" in r and "best_kappa" in r
    c.close()
