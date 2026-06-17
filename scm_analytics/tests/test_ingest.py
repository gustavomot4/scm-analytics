"""Testes do módulo ingest — aceite M1: contagens, sem nulos, idempotência, flag neutro.

Sem rede: usa fixture fiel ao schema do martj42 (results.csv) e SQLite em memória.
"""
import pytest

from scm import db, ingest

# Fixture fiel ao martj42: 4 jogos disputados + 1 fixture futura (sem placar, deve ser pulada)
FIXTURE = """date,home_team,away_team,home_score,away_score,tournament,city,country,neutral
1872-11-30,Scotland,England,0,0,Friendly,Glasgow,Scotland,False
2022-12-18,Argentina,France,3,3,FIFA World Cup,Lusail,Qatar,True
2022-12-14,Argentina,Croatia,3,0,FIFA World Cup,Lusail,Qatar,True
2021-07-10,Argentina,Brazil,1,0,Copa América,Rio de Janeiro,Brazil,False
2026-06-11,Mexico,,,,FIFA World Cup,Mexico City,Mexico,False
"""


@pytest.fixture
def csv_file(tmp_path):
    p = tmp_path / "results.csv"
    p.write_text(FIXTURE, encoding="utf-8")
    return p


@pytest.fixture
def conn():
    c = db.connect(":memory:")
    db.init_schema(c)
    yield c
    c.close()


def _count(conn, table):
    return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def test_counts(csv_file, conn):
    stats = ingest.load_results(csv_file, conn)
    assert stats["rows"] == 5
    assert stats["skipped"] == 1            # a linha de 2026 (sem placar)
    assert _count(conn, "matches") == 4
    assert _count(conn, "teams") == 6       # Mexico não entra (linha pulada)


def test_no_null_keys(csv_file, conn):
    ingest.load_results(csv_file, conn)
    bad = conn.execute(
        "SELECT COUNT(*) FROM matches WHERE date IS NULL OR home_team_id IS NULL "
        "OR away_team_id IS NULL OR home_score IS NULL OR away_score IS NULL"
    ).fetchone()[0]
    assert bad == 0
    bad_team = conn.execute("SELECT COUNT(*) FROM teams WHERE name IS NULL OR name = ''").fetchone()[0]
    assert bad_team == 0


def test_idempotent(csv_file, conn):
    ingest.load_results(csv_file, conn)
    m1, t1 = _count(conn, "matches"), _count(conn, "teams")
    stats2 = ingest.load_results(csv_file, conn)   # segunda carga idêntica
    assert (_count(conn, "matches"), _count(conn, "teams")) == (m1, t1) == (4, 6)
    assert stats2["inserted"] == 0                 # nada novo na 2ª carga


def test_neutral_parsed(csv_file, conn):
    ingest.load_results(csv_file, conn)
    final = conn.execute(
        "SELECT neutral FROM matches WHERE tournament = 'FIFA World Cup' AND date = '2022-12-18'"
    ).fetchone()[0]
    friendly = conn.execute("SELECT neutral FROM matches WHERE date = '1872-11-30'").fetchone()[0]
    assert final == 1 and friendly == 0


def test_skips_unplayed(csv_file, conn):
    ingest.load_results(csv_file, conn)
    assert conn.execute("SELECT COUNT(*) FROM teams WHERE name = 'Mexico'").fetchone()[0] == 0
