"""Testes do predict_match — porta da frente."""
import pytest

from scm import db
from scm import elo_engine as elo
from scm import predict_match as pm


@pytest.fixture
def conn():
    c = db.connect(":memory:"); db.init_schema(c)
    # alguns jogos p/ gerar ratings: Brazil forte, San Marino fraco; Bolivia na altitude
    def M(date, h, a, hs, as_, city="Rio", neutral=1):
        hi = db.get_or_create_team(c, h); ai = db.get_or_create_team(c, a)
        c.execute("""INSERT INTO matches (date,home_team_id,away_team_id,home_score,away_score,
                     tournament,city,neutral,natural_key) VALUES (?,?,?,?,?,?,?,?,?)""",
                  (date, hi, ai, hs, as_, "FIFA World Cup", city, neutral, f"{date}|{h}|{a}"))
    for k in range(12):
        M(f"201{k%9}-06-{(k%27)+1:02d}", "Brazil", "Bolivia", 3, 0)
        M(f"201{k%9}-09-{(k%27)+1:02d}", "Argentina", "Brazil", 1, 1)
    c.commit(); elo.run(c)
    yield c
    c.close()


def test_favorite_has_higher_prob(conn):
    r = pm.predict_match(conn, "Brazil", "Bolivia")
    assert "erro" not in r
    assert r["p_v"] + r["p_e"] + r["p_d"] == pytest.approx(1.0, abs=1e-9)
    assert r["p_v"] > r["p_d"]            # Brazil (Elo maior) favorito


def test_unknown_team_suggests(conn):
    r = pm.predict_match(conn, "Atlantida", "Bolivia")   # nome inexistente (sem alias)
    assert r["erro"] == "time não encontrado"
    assert "faltando" in r


def test_pt_alias_resolves(conn):
    # 'Brasil' (pt) AGORA resolve via _PT_ALIAS -> 'Brazil' (não é mais erro)
    r = pm.predict_match(conn, "Brasil", "Bolivia")
    assert "erro" not in r and r["home"] == "Brazil"


def test_altitude_boosts_home(conn):
    base = pm.predict_match(conn, "Bolivia", "Brazil")                 # neutro
    alt = pm.predict_match(conn, "Bolivia", "Brazil", city="La Paz")   # em La Paz
    assert alt["gd_alt"] > 0
    assert alt["p_v"] > base["p_v"]       # altitude favorece a Bolívia (mandante adaptada)


def test_mando_boosts_home(conn):
    base = pm.predict_match(conn, "Bolivia", "Brazil")
    mando = pm.predict_match(conn, "Bolivia", "Brazil", mando=80)
    assert mando["dr"] > base["dr"] and mando["p_v"] > base["p_v"]


def test_confidence_escapes_old_cap_and_orders(conn):
    # massacre entre times maduros deve dar confiança ALTA (acima do antigo teto ~68)
    blow = pm.confidence(0.95, 0.03, 0.02, sigma_r_avg=40.0)
    toss = pm.confidence(0.37, 0.33, 0.30, sigma_r_avg=40.0)
    assert blow > toss
    assert blow > 68            # sem o teto artificial antigo
    assert pm.conf_label(blow) == "alta"


def test_confidence_drops_with_rating_uncertainty(conn):
    mature = pm.confidence(0.90, 0.06, 0.04, sigma_r_avg=40.0)
    provis = pm.confidence(0.90, 0.06, 0.04, sigma_r_avg=160.0)
    assert provis < mature       # rating incerto → confiança menor


def test_predict_match_exposes_markets(conn):
    r = pm.predict_match(conn, "Brazil", "Bolivia")
    assert "markets" in r and "over" in r["markets"] and "first_to_score" in r["markets"]
    assert 0.0 <= r["markets"]["over"]["2.5"] <= 1.0


def test_difflib_suggests_brazil(conn):
    r = pm.predict_match(conn, "Brazl", "Bolivia")        # erro de digitação (não bate alias)
    assert r["erro"] == "time não encontrado"
    assert "Brazil" in r["sugestoes"]                     # difflib aproxima


def test_estilo_preview_in_range(conn):
    from scm.estilo import CAP_LO, CAP_HI
    r = pm.predict_match(conn, "Brazil", "Bolivia", usar_estilo=True)
    assert CAP_LO <= r["estilo_a"] <= CAP_HI and CAP_LO <= r["estilo_b"] <= CAP_HI


def test_reliab_stale_flag(conn):
    import json
    db.set_meta(conn, "confidence_reliab",
                json.dumps({"model": "versao-antiga", "curve": [[0.4, 0.4], [0.9, 0.9]]}))
    conn.commit()
    r = pm.predict_match(conn, "Brazil", "Bolivia")
    assert r["reliab_stale"] is True


def test_dr_includes_recent_form():
    """D-34: a porta da frente aplica a forma recente ao dr (igual ao backtest dr_adj).

    Cenário com upset recente (Davi bate Golias 2x) → forma != 0; o dr retornado deve ser
    Elo + (forma_A − forma_B), não o Elo puro (antes o ponto de forma era descartado).
    """
    from datetime import date as D, timedelta as TD
    from scm.features_pit import team_form, FeatureParams
    c = db.connect(":memory:"); db.init_schema(c)

    def M(date, h, a, hs, as_):
        hi = db.get_or_create_team(c, h); ai = db.get_or_create_team(c, a)
        c.execute("""INSERT INTO matches(date,home_team_id,away_team_id,home_score,away_score,
                     tournament,neutral,natural_key) VALUES(?,?,?,?,?,?,1,?)""",
                  (date, hi, ai, hs, as_, "FIFA World Cup", f"{date}|{h}|{a}|{hs}{as_}"))
    for k in range(20):
        M(f"2016-{(k % 12) + 1:02d}-10", "Golias", f"Fraco{k % 5}", 4, 0)
        M(f"2017-{(k % 12) + 1:02d}-10", "Davi", f"Fraco{k % 5}", 1, 1)
    M("2018-10-01", "Davi", "Golias", 2, 0)
    M("2018-11-01", "Davi", "Golias", 1, 0)
    c.commit(); elo.run(c)

    ref = (D.fromisoformat(c.execute("SELECT MAX(date) FROM matches").fetchone()[0])
           + TD(days=1)).isoformat()
    da = db.get_or_create_team(c, "Davi"); go = db.get_or_create_team(c, "Golias")
    fa = team_form(c, da, ref, FeatureParams())[0]
    fb = team_form(c, go, ref, FeatureParams())[0]
    eloA = c.execute("SELECT elo FROM ratings_current WHERE team_id=?", (da,)).fetchone()[0]
    eloB = c.execute("SELECT elo FROM ratings_current WHERE team_id=?", (go,)).fetchone()[0]
    r = pm.predict_match(c, "Davi", "Golias")
    c.close()
    assert r["dr"] == pytest.approx((eloA - eloB) + (fa - fb), abs=1e-9)
    assert abs(fa - fb) > 1.0          # a forma de fato move o dr neste cenário
