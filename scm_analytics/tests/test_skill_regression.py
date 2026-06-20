"""Teste de regressão de SKILL (audit P12): trava o Brier/IC do backtest REAL.

Diferente dos demais testes (coerência/invariantes/look-ahead), este pega regressão de
MODELAGEM: uma mudança de coeficiente que preserve a coerência mas DEGRADE a previsão é
barrada aqui. Requer o snapshot real `dados/scm.sqlite` (gitignored) → SKIP se ausente
(ex.: CI sem dados). Rode localmente após o pipeline (`predictor`).
"""
import pytest
from pathlib import Path
from scm import db
from scm.ingest import DEFAULT_DB
from scm.predictor import MODEL_VERSION
from scm.backtest_harness import evaluate, evaluate_vs_elo, evaluate_vs_lookup

DBP = Path(DEFAULT_DB)
pytestmark = pytest.mark.skipif(not DBP.exists(), reason="snapshot dados/scm.sqlite ausente")


@pytest.fixture(scope="module")
def conn():
    c = db.connect(str(DBP))
    if c.execute("SELECT COUNT(*) FROM predictions WHERE versao_modelo=?", (MODEL_VERSION,)).fetchone()[0] == 0:
        pytest.skip("sem previsões da versão atual — rode `python -m scm.predictor`")
    yield c
    c.close()


def test_beats_uniform_major(conn):
    m = evaluate(conn, MODEL_VERSION, only_major=True)
    assert m["brier"] < 0.60               # claramente abaixo do uniforme (0.667)
    assert m["bate_uniforme_com_ic"]       # IC do ganho vs uniforme não cruza zero


def test_beats_elo_public_major(conn):
    e = evaluate_vs_elo(conn, MODEL_VERSION, only_major=True)
    assert e["ic_lo"] > 0                   # bate o Elo (we+C1) com IC>0


def test_not_below_dr_ceiling_major(conn):
    lk = evaluate_vs_lookup(conn, MODEL_VERSION, only_major=True)
    assert lk["ic_hi"] >= 0                 # NÃO fica abaixo do teto não-paramétrico do dr
