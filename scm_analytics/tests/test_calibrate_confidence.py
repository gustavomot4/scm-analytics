"""Testes do calibrate_confidence — curva de confiabilidade isotônica + store em meta."""
import json
import pytest
from scm import db
from scm import calibrate_confidence as cc


def _mk_match(c, idx, hs, as_):
    h = db.get_or_create_team(c, f"H{idx}"); a = db.get_or_create_team(c, f"A{idx}")
    cur = c.execute("""INSERT INTO matches (date,home_team_id,away_team_id,home_score,away_score,
                       tournament,neutral,natural_key) VALUES (?,?,?,?,?,?,?,?)""",
                    (f"2020-01-{(idx % 27) + 1:02d}", h, a, hs, as_, "Friendly", 1, f"k{idx}"))
    return cur.lastrowid


@pytest.fixture
def conn():
    c = db.connect(":memory:"); db.init_schema(c)
    i = 0
    # faixa ALTA (p_max≈0.9): 80% de acerto (home vence)
    for k in range(100):
        win = k < 80
        mid = _mk_match(c, i, 2 if win else 0, 0 if win else 2); i += 1
        c.execute("INSERT INTO predictions (match_id,versao_modelo,p_v,p_e,p_d) VALUES (?,?,?,?,?)",
                  (mid, "t", 0.90, 0.05, 0.05))
    # faixa BAIXA (p_max≈0.40): 45% de acerto
    for k in range(100):
        win = k < 45
        mid = _mk_match(c, i, 1 if win else 0, 0 if win else 1); i += 1
        c.execute("INSERT INTO predictions (match_id,versao_modelo,p_v,p_e,p_d) VALUES (?,?,?,?,?)",
                  (mid, "t", 0.40, 0.30, 0.30))
    c.commit()
    yield c
    c.close()


def test_isotonic_non_decreasing():
    out = cc._isotonic([0.8, 0.2, 0.6], [10, 10, 10])      # viola no meio
    assert all(out[i] <= out[i + 1] + 1e-9 for i in range(len(out) - 1))


def test_curve_increases_and_stored(conn):
    res = cc.calibrate(conn, store=True)
    curve = res["curve"]
    assert len(curve) >= 2
    assert curve[-1][1] >= curve[0][1]                      # reliab sobe com p_max
    assert curve[-1][1] == pytest.approx(0.80, abs=0.06)    # faixa alta ~80%
    row = conn.execute("SELECT value FROM meta WHERE key='confidence_reliab'").fetchone()
    assert row and json.loads(row[0])                       # gravou em meta


def test_predict_match_reads_calibrated_curve(conn):
    cc.calibrate(conn, store=True)
    from scm import predict_match as pm
    f, model = pm._reliab_from_meta(conn)
    assert f is not None
    assert f(0.90) >= f(0.40)                               # curva monotônica é usada


def test_curve_stored_with_model_version(conn):
    import json
    from scm.predictor import MODEL_VERSION
    cc.calibrate(conn, store=True)
    raw = conn.execute("SELECT value FROM meta WHERE key='confidence_reliab'").fetchone()[0]
    data = json.loads(raw)
    assert isinstance(data, dict) and data["model"] == MODEL_VERSION and data["curve"]
