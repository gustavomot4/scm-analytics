"""Fixtures compartilhadas (P-I/D-43) — reduz a duplicação de setup entre os testes.

`conn`: SQLite em memória com o schema criado. Testes que já definem o próprio `conn`
local continuam válidos (a fixture local tem precedência sobre a do conftest).
`mini_liga`: uma base pequena já com Elo reconstruído (Brazil forte, Bolivia fraca),
útil para testes de predict_match / registrar / desfalques.
"""
import pytest

from scm import db
from scm import elo_engine as elo


@pytest.fixture
def conn():
    c = db.connect(":memory:")
    db.init_schema(c)
    yield c
    c.close()


@pytest.fixture
def mini_liga():
    c = db.connect(":memory:")
    db.init_schema(c)

    def jogo(date, h, a, hs, as_):
        hi = db.get_or_create_team(c, h); ai = db.get_or_create_team(c, a)
        c.execute("""INSERT INTO matches(date,home_team_id,away_team_id,home_score,away_score,
                     tournament,neutral,natural_key) VALUES (?,?,?,?,?,?,1,?)""",
                  (date, hi, ai, hs, as_, "FIFA World Cup", f"{date}|{h}|{a}"))
    for k in range(12):
        jogo(f"201{k % 9}-06-{(k % 27) + 1:02d}", "Brazil", "Bolivia", 3, 0)
        jogo(f"201{k % 9}-09-{(k % 27) + 1:02d}", "Argentina", "Brazil", 1, 1)
    c.commit(); elo.run(c)
    yield c
    c.close()
