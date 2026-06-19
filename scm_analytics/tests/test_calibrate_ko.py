"""Teste do calibrador de ε (mata-mata) com fixture sintética."""
import tempfile, os
from scm import db
from scm import calibrate_ko as ck


def test_eps_hat_from_synthetic_shootouts():
    c = db.connect(":memory:"); db.init_schema(c)
    def M(date, h, a, dr):
        hi = db.get_or_create_team(c, h); ai = db.get_or_create_team(c, a)
        c.execute("INSERT INTO matches(date,home_team_id,away_team_id,home_score,away_score,"
                  "tournament,neutral,natural_key) VALUES (?,?,?,1,1,'FIFA World Cup',1,?)",
                  (date, hi, ai, f"{date}|{h}|{a}"))
        mid = c.execute("SELECT match_id FROM matches WHERE natural_key=?", (f"{date}|{h}|{a}",)).fetchone()[0]
        c.execute("INSERT INTO match_ratings(match_id,dr) VALUES (?,?)", (mid, dr)); c.commit()
    # 4 disputas: A mais forte (dr>0) em todas; vence 3 de 4 -> taxa 0.75 -> eps 0.25
    M("2018-07-01", "A", "B", 200); M("2018-07-02", "C", "D", 150)
    M("2018-07-03", "E", "F", 300); M("2018-07-04", "G", "H", 120)
    fd, path = tempfile.mkstemp(suffix=".csv"); os.close(fd)
    open(path, "w").write("date,home_team,away_team,winner,first_shooter\n"
        "2018-07-01,A,B,A,A\n2018-07-02,C,D,C,C\n2018-07-03,E,F,E,E\n2018-07-04,G,H,H,H\n")
    r = ck.calibrate(c, path); os.remove(path); c.close()
    assert r["n"] == 4
    assert abs(r["stronger_win_rate"] - 0.75) < 1e-9
    assert abs(r["eps_hat"] - 0.25) < 1e-9
