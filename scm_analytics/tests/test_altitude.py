"""Testes do termo de altitude (E1) — gd_alt e o portão."""
import pytest

from scm import db
from scm import elo_engine as elo
from scm import features_pit as fp
from scm import altitude as alt


def test_gd_alt_sign_and_zero():
    # sede alta: time não-adaptado (away) é penalizado -> favorece o adaptado
    assert alt.gd_alt("La Paz", "Bolivia", "Brazil") == pytest.approx(0.5 * 3637 / 1000)
    assert alt.gd_alt("La Paz", "Brazil", "Bolivia") == pytest.approx(-0.5 * 3637 / 1000)
    # sede ao nível do mar: sem efeito
    assert alt.gd_alt("Rio", "Brazil", "Bolivia") == 0.0
    # dois adaptados na altitude: efeito ~0 (ambos penalizam 0)
    assert alt.gd_alt("La Paz", "Bolivia", "Bolivia") == 0.0


def test_city_variants():
    assert alt.venue_alt("BOGOTÁ") == 2640
    assert alt.venue_alt("bogota") == 2640
    assert alt.venue_alt("Lugar Desconhecido") == 0.0


def test_gate_altitude_counts_only_altitude_games():
    c = db.connect(":memory:"); db.init_schema(c)
    def M(date, home, away, hs, as_, city):
        hi = db.get_or_create_team(c, home); ai = db.get_or_create_team(c, away)
        c.execute("""INSERT INTO matches (date,home_team_id,away_team_id,home_score,away_score,
                     tournament,city,neutral,natural_key) VALUES (?,?,?,?,?,?,?,0,?)""",
                  (date, hi, ai, hs, as_, "FIFA World Cup qualification", city,
                   f"{date}|{home}|{away}"))
    # 3 jogos em La Paz (altitude morde) + 2 ao nível do mar (não morde)
    M("2013-03-22", "Bolivia", "Brazil", 2, 2, "La Paz")
    M("2013-09-06", "Bolivia", "Argentina", 1, 1, "La Paz")
    M("2015-10-08", "Bolivia", "Uruguay", 0, 2, "La Paz")
    M("2013-03-22", "Brazil", "Bolivia", 4, 0, "Rio")
    M("2014-06-01", "Argentina", "Bolivia", 3, 0, "Buenos Aires")
    c.commit()
    elo.run(c); fp.run(c)
    r = alt.gate_altitude(c, B=300)
    assert r["n_alt"] == 3          # só os 3 de La Paz
    assert "keep" in r
    c.close()
