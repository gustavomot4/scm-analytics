"""Teste do diagnóstico de BTTS — mede o viés (previsto vs real)."""
import pytest
from scm import db, report


@pytest.fixture
def conn():
    c = db.connect(":memory:"); db.init_schema(c)
    for i in range(100):
        h = db.get_or_create_team(c, f"H{i}"); a = db.get_or_create_team(c, f"A{i}")
        hs, as_ = (1, 1) if i < 50 else (1, 0)        # 50 BTTS, 50 não -> real 50%
        cur = c.execute("INSERT INTO matches(date,home_team_id,away_team_id,home_score,away_score,"
                        "tournament,neutral,natural_key) VALUES(?,?,?,?,?,?,?,?)",
                        (f"2020-01-{(i % 27) + 1:02d}", h, a, hs, as_, "Friendly", 1, f"k{i}"))
        c.execute("INSERT INTO predictions(match_id,versao_modelo,p_v,p_e,p_d,p_btts) "
                  "VALUES(?,?,?,?,?,?)", (cur.lastrowid, "t", 0.4, 0.3, 0.3, 0.60))
    c.commit()
    yield c
    c.close()


def test_btts_bias_measured(conn):
    r = report.btts_report(conn, "t")
    assert r["n"] == 100
    assert r["actual_rate"] == pytest.approx(0.50, abs=1e-9)
    assert r["mean_pred"] == pytest.approx(0.60, abs=1e-9)
    assert r["bias"] == pytest.approx(0.10, abs=1e-9)     # previu 60%, real 50% -> +10pp
    assert r["reliability"]                                # tem bins
