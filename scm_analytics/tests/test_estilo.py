"""Testes do estilo — tendência de gols (alavanca do BTTS), com shrinkage e PIT."""
import pytest
from scm import db, estilo


def _M(c, i, h, a, hs, as_):
    hi = db.get_or_create_team(c, h); ai = db.get_or_create_team(c, a)
    c.execute("INSERT INTO matches(date,home_team_id,away_team_id,home_score,away_score,"
              "tournament,neutral,natural_key) VALUES(?,?,?,?,?,?,?,?)",
              (f"2010-{(i % 12) + 1:02d}-{(i % 27) + 1:02d}", hi, ai, hs, as_, "Friendly", 1, f"k{i}"))


@pytest.fixture
def conn():
    c = db.connect(":memory:"); db.init_schema(c)
    for i in range(40):
        _M(c, i, "Attackers", "Mid", 4, 3)        # 7 gols/jogo (ofensivo)
        _M(c, 100 + i, "Defenders", "Mid", 1, 0)  # 1 gol/jogo (defensivo)
    c.commit()
    yield c
    c.close()


def test_offensive_gt_one_gt_defensive(conn):
    st, gm = estilo.team_styles(conn)
    att = db.get_or_create_team(conn, "Attackers")
    de = db.get_or_create_team(conn, "Defenders")
    assert st[att] > 1.0 > st[de]
    assert estilo.CAP_LO <= st[de] and st[att] <= estilo.CAP_HI   # dentro dos limites


def test_shrinks_low_sample(conn):
    hi = db.get_or_create_team(conn, "Rookie"); ai = db.get_or_create_team(conn, "Mid")
    conn.execute("INSERT INTO matches(date,home_team_id,away_team_id,home_score,away_score,"
                 "tournament,neutral,natural_key) VALUES(?,?,?,?,?,?,?,?)",
                 ("2011-01-01", hi, ai, 9, 0, "Friendly", 1, "rook"))
    conn.commit()
    st, _ = estilo.team_styles(conn)
    assert abs(st[hi] - 1.0) < 0.15            # 1 jogo extremo -> encolhido a ~1.0


def test_pit_excludes_future(conn):
    st_pit, _ = estilo.team_styles(conn, before_date="2010-01-01")  # nada antes
    assert st_pit == {}


def test_gate_no_features_graceful(conn):
    r = estilo.gate_estilo(conn, cutoff="2015-01-01", only_major=False)
    assert r.get("n", 0) == 0                   # sem match_features -> não quebra
