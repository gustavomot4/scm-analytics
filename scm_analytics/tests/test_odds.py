"""Testes do esqueleto de odds (P-H/D-44): de-vig, blend, store/read e ensemble de mercado."""
import pytest

from scm import db
from scm import elo_engine as elo
from scm import predict_match as pm
from scm.odds import implied_probs, blend, store, market_read, W_MARKET


def test_implied_probs_devig_sums_to_one():
    m = implied_probs(2.00, 3.50, 4.00)
    assert m["p_v"] + m["p_e"] + m["p_d"] == pytest.approx(1.0, abs=1e-9)
    assert m["p_v"] > m["p_d"]                 # menor odd = maior prob


def test_implied_probs_rejects_invalid():
    with pytest.raises(ValueError):
        implied_probs(1.0, 3.5, 4.0)


def test_blend_between_model_and_market():
    model = {"p_v": 0.60, "p_e": 0.25, "p_d": 0.15}
    market = {"p_v": 0.40, "p_e": 0.30, "p_d": 0.30}
    b = blend(model, market, w=W_MARKET)
    assert b["p_v"] + b["p_e"] + b["p_d"] == pytest.approx(1.0, abs=1e-9)
    assert market["p_v"] < b["p_v"] < model["p_v"]      # puxa em direção ao mercado


def test_store_and_read_roundtrip():
    c = db.connect(":memory:"); db.init_schema(c)
    m = implied_probs(2.0, 3.4, 3.8)
    store(c, "Brazil", "Argentina", "2026-06-20", m, source="manual")
    got = market_read(c, "Brazil", "Argentina", "2026-06-20")
    c.close()
    assert got is not None and got["p_v"] == pytest.approx(m["p_v"], abs=1e-9)


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


def test_predict_match_blends_market():
    c = _conn()
    base = pm.predict_match(c, "Brazil", "Bolivia")
    # mercado pessimista p/ o Brasil (odd alta na casa) deve puxar p_v para baixo
    out = pm.predict_match(c, "Brazil", "Bolivia", odds=(3.0, 3.3, 2.2))
    c.close()
    assert out["mercado"] is not None
    assert out["p_v"] < base["p_v"]
    assert out["p_v"] + out["p_e"] + out["p_d"] == pytest.approx(1.0, abs=1e-9)
