"""Testes do features_pit — destaque: ANTI LOOK-AHEAD."""
import pytest

from scm import db
from scm import elo_engine as elo
from scm import features_pit as fp


@pytest.fixture
def conn():
    c = db.connect(":memory:")
    db.init_schema(c)
    yield c
    c.close()


def _match(conn, date, home, away, hs, as_, tournament="Friendly", neutral=1):
    h = db.get_or_create_team(conn, home)
    a = db.get_or_create_team(conn, away)
    conn.execute(
        """INSERT INTO matches (date, home_team_id, away_team_id, home_score, away_score,
                                tournament, neutral, natural_key)
           VALUES (?,?,?,?,?,?,?,?)""",
        (date, h, a, hs, as_, tournament, neutral, f"{date}|{home}|{away}|{tournament}"),
    )
    conn.commit()


def _feat(conn, date_):
    """Linha de match_features do jogo na data dada (como dict)."""
    row = conn.execute(
        """SELECT mf.* FROM match_features mf JOIN matches m USING (match_id)
           WHERE m.date = ?""",
        (date_,),
    ).fetchone()
    return dict(row) if row else None


def _build(conn):
    elo.run(conn)
    fp.run(conn)


def test_first_match_zero_form(conn):
    _match(conn, "2000-01-01", "A", "B", 1, 0)
    _build(conn)
    f = _feat(conn, "2000-01-01")
    assert f["form_home"] == 0.0 and f["form_away"] == 0.0   # nenhum jogo anterior
    assert f["n_home_pre"] == 0 and f["n_away_pre"] == 0


def test_form_sign_uses_only_past(conn):
    # A vence como igual (residual +0.5) no 1o jogo; no 2o, sua forma deve ser positiva
    _match(conn, "2000-01-01", "A", "B", 1, 0)
    _match(conn, "2000-02-01", "A", "C", 0, 0)
    _build(conn)
    f2 = _feat(conn, "2000-02-01")
    assert f2["form_home"] == pytest.approx(30.0)   # +0.5 residual -> cap +30
    assert f2["form_away"] == 0.0                    # C estreia


def test_dr_adj_equals_elo_plus_form(conn):
    _match(conn, "2000-01-01", "A", "B", 1, 0)
    _match(conn, "2000-02-01", "A", "C", 0, 0)
    _build(conn)
    f = _feat(conn, "2000-02-01")
    assert f["dr_adj"] == pytest.approx(f["dr_elo"] + f["form_home"] - f["form_away"])


def test_sigma_dr_combines(conn):
    _match(conn, "2000-01-01", "A", "B", 1, 0)
    _build(conn)
    f = _feat(conn, "2000-01-01")
    # estreia: σ_ajuste=0; σ_R(0)=200 cada -> σ_dr = sqrt(200²+200²)
    assert f["sigma_dr"] == pytest.approx((200.0 ** 2 + 200.0 ** 2) ** 0.5, rel=1e-6)


def test_idempotent(conn):
    _match(conn, "2000-01-01", "A", "B", 1, 0)
    _match(conn, "2000-02-01", "A", "C", 0, 0)
    _build(conn)
    a1 = _feat(conn, "2000-02-01")
    fp.run(conn)                       # roda de novo
    a2 = _feat(conn, "2000-02-01")
    assert a1 == a2
    assert conn.execute("SELECT COUNT(*) FROM match_features").fetchone()[0] == 2


def test_no_lookahead(conn):
    # 1) constrói com 2 jogos
    _match(conn, "2000-01-01", "A", "B", 1, 0)
    _match(conn, "2000-02-01", "A", "C", 0, 0)
    _build(conn)
    before_m1 = _feat(conn, "2000-01-01")
    before_m2 = _feat(conn, "2000-02-01")
    # 2) adiciona um jogo FUTURO com goleada e reconstrói
    _match(conn, "2000-03-01", "A", "D", 7, 0)
    _build(conn)
    after_m1 = _feat(conn, "2000-01-01")
    after_m2 = _feat(conn, "2000-02-01")
    # features dos jogos passados NÃO podem mudar por causa de um jogo futuro
    assert before_m1 == after_m1
    assert before_m2 == after_m2


def test_vol_mult_behavior():
    from scm.features_pit import vol_mult
    assert vol_mult(0.0, n_form=1) == 1.0          # poucos jogos -> neutro
    assert vol_mult(0.0, n_form=10) == 0.6         # consistente -> reduz (clamp)
    assert vol_mult(0.35, n_form=10) == pytest.approx(1.0, abs=1e-9)  # ~médio -> ~1
    assert vol_mult(2.0, n_form=10) == 1.6         # errático -> aumenta (clamp)
