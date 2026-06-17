"""Testes do elo_engine — funções puras + reconstrução (valores computáveis à mão)."""
import pytest

from scm import db
from scm import elo_engine as elo
from scm.elo_engine import EloParams, we, g_factor, k_factor, sigma_r


@pytest.fixture
def conn():
    c = db.connect(":memory:")
    db.init_schema(c)
    yield c
    c.close()


def _match(conn, date, home, away, hs, as_, tournament="Friendly", neutral=0):
    h = db.get_or_create_team(conn, home)
    a = db.get_or_create_team(conn, away)
    conn.execute(
        """INSERT INTO matches (date, home_team_id, away_team_id, home_score, away_score,
                                tournament, neutral, natural_key)
           VALUES (?,?,?,?,?,?,?,?)""",
        (date, h, a, hs, as_, tournament, neutral, f"{date}|{home}|{away}|{tournament}"),
    )
    conn.commit()


def _elo(conn, name):
    return conn.execute(
        "SELECT elo FROM ratings_current r JOIN teams t USING (team_id) WHERE t.name = ?",
        (name,),
    ).fetchone()[0]


# ---------- funções puras ----------
def test_we_aceite():
    assert abs(we(0) - 0.5) < 1e-9
    assert abs(we(100) - 0.640) < 0.005      # ACEITE: dr=100 -> W_e ≈ 0.64
    assert abs(we(-100) + we(100) - 1.0) < 1e-9
    assert we(400) > 0.90


def test_g_factor():
    assert g_factor(0) == 1.0 and g_factor(1) == 1.0
    assert g_factor(2) == 1.5
    assert g_factor(-3) == (11 + 3) / 8      # 1.75, usa |gd|
    assert g_factor(5) == 2.0


def test_k_factor():
    assert k_factor("FIFA World Cup") == 60
    assert k_factor("FIFA World Cup qualification") == 40   # 'qualif' vence 'world cup'
    assert k_factor("Friendly") == 20
    assert k_factor("UEFA Nations League") == 30
    assert k_factor("UEFA Euro") == 50
    assert k_factor("Copa América") == 50
    assert k_factor("Some Random Trophy") == 40


def test_sigma_decreasing():
    p = EloParams()
    assert sigma_r(0, p) > sigma_r(10, p) > sigma_r(50, p) >= p.sigma_floor
    assert abs(sigma_r(0, p) - p.sigma_provisional) < 1e-9


# ---------- reconstrução ----------
def test_single_update_neutral_friendly(conn):
    # neutro + amistoso (K=20), mandante vence 1-0 (G=1), ratings iguais
    _match(conn, "2000-01-01", "A", "B", 1, 0, "Friendly", neutral=1)
    elo.run(conn)
    assert abs(_elo(conn, "A") - 1510) < 1e-6   # delta = 20*1*(1-0.5) = 10
    assert abs(_elo(conn, "B") - 1490) < 1e-6


def test_mando_applied_nonneutral(conn):
    # não-neutro + Copa (K=60), EMPATE. dr = 0 + 100 = 100, W_e ≈ 0.640
    _match(conn, "2000-01-01", "A", "B", 1, 1, "FIFA World Cup", neutral=0)
    elo.run(conn)
    # delta = 60*1*(0.5 - 0.640) ≈ -8.40 (mandante perde por só empatar sendo favorito pelo mando)
    assert abs(_elo(conn, "A") - 1491.6) < 0.1


def test_zero_sum_conservation(conn):
    _match(conn, "2000-01-01", "A", "B", 2, 0, "FIFA World Cup")
    _match(conn, "2000-02-01", "B", "C", 1, 1, "Friendly", neutral=1)
    elo.run(conn)
    total = conn.execute("SELECT SUM(elo) FROM ratings_current").fetchone()[0]
    n = conn.execute("SELECT COUNT(*) FROM ratings_current").fetchone()[0]
    assert abs(total - n * 1500.0) < 1e-6       # init iguais + updates zero-sum


def test_point_in_time(conn):
    _match(conn, "2000-01-01", "A", "B", 1, 0, "Friendly", neutral=1)
    _match(conn, "2000-02-01", "A", "B", 1, 0, "Friendly", neutral=1)
    elo.run(conn)
    first = conn.execute(
        "SELECT home_elo_pre, away_elo_pre FROM match_ratings mr "
        "JOIN matches m USING (match_id) WHERE m.date = '2000-01-01'"
    ).fetchone()
    assert abs(first[0] - 1500) < 1e-9 and abs(first[1] - 1500) < 1e-9   # 1º jogo: ambos 1500
    second = conn.execute(
        "SELECT home_elo_pre FROM match_ratings mr "
        "JOIN matches m USING (match_id) WHERE m.date = '2000-02-01'"
    ).fetchone()
    assert second[0] > 1500     # 2º jogo: pré reflete SÓ o jogo anterior (point-in-time)


def test_rerun_idempotent(conn):
    _match(conn, "2000-01-01", "A", "B", 1, 0, "FIFA World Cup")
    elo.run(conn)
    ra1 = _elo(conn, "A")
    n1 = conn.execute("SELECT COUNT(*) FROM match_ratings").fetchone()[0]
    elo.run(conn)                                # roda de novo
    assert abs(_elo(conn, "A") - ra1) < 1e-9
    assert conn.execute("SELECT COUNT(*) FROM match_ratings").fetchone()[0] == n1 == 1
