"""Testes da captura semi-auto da linha de fechamento (odds_close, D-77).

Instrumentação (sem portão). Relógio injetado (now_fn) → determinístico, sem rede, sem dormir.
Cobre: parse de kickoff, janela do `due` (incl. date-only e exclusão pós-captura), de-vig+store
em source='close', resolução de data e um passe do watcher (once=True).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta

import pytest

from scm import db, odds_close
from scm.ingest import DEFAULT_DB  # noqa: F401  (garante que o pacote importa)

NOW = datetime(2026, 6, 26, 23, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def conn(tmp_path):
    c = db.connect(str(tmp_path / "t.sqlite"))
    db.init_schema(c)
    return c


def _fixtures():
    return [
        {"home": "Spain", "away": "Uruguay", "date": "2026-06-26", "kickoff": "2026-06-26T23:03:00+00:00"},
        {"home": "A", "away": "B", "date": "2026-06-26", "kickoff": "2026-06-27T01:00:00+00:00"},  # +120 min
        {"home": "C", "away": "D", "date": "2026-06-26"},   # só data, hoje
        {"home": "E", "away": "F", "date": "2026-06-30"},   # só data, futuro
    ]


def test_parse_kickoff_variants():
    assert odds_close.parse_kickoff({"kickoff": "2026-06-26T19:00:00-04:00"}) == \
        datetime(2026, 6, 26, 19, 0, tzinfo=timezone(timedelta(hours=-4)))
    assert odds_close.parse_kickoff({"kickoff": "2026-06-26T23:00-00:00"}) is not None  # sem segundos
    assert odds_close.parse_kickoff({"date": "2026-06-26"}) is None                     # sem horário


def test_due_window_and_date_only(conn):
    d = odds_close.due(conn, _fixtures(), within_min=15, now=NOW)
    names = {f["home"] for f in d}
    assert "Spain" in names          # kickoff em +3 min
    assert "A" not in names          # +120 min, fora da janela
    assert "C" in names              # só data, hoje
    assert "E" not in names          # só data, futuro
    assert next(f for f in d if f["home"] == "Spain")["time_known"] is True
    assert next(f for f in d if f["home"] == "C")["time_known"] is False


def test_set_close_devig_store_and_exclusion(conn):
    fx = _fixtures()
    r = odds_close.set_close(conn, "Spain", "Uruguay", 1.85, 3.60, 4.20, fixtures=fx)
    assert abs(r["p_v"] + r["p_e"] + r["p_d"] - 1.0) < 1e-9    # de-vig soma 1
    assert r["p_v"] > r["p_d"] > r["p_e"]                       # favorito > azarão > empate aqui
    from scm.odds import market_read
    assert market_read(conn, "Spain", "Uruguay", "2026-06-26", source="close") is not None
    # após capturar, sai do 'due'
    assert "Spain" not in {f["home"] for f in odds_close.due(conn, fx, within_min=15, now=NOW)}


def test_set_close_requires_resolvable_date(conn):
    with pytest.raises(ValueError):
        odds_close.set_close(conn, "X", "Y", 2.0, 3.0, 4.0, fixtures=_fixtures())


def test_resolve_date(conn):
    assert odds_close.resolve_date(_fixtures(), "Spain", "Uruguay") == "2026-06-26"
    assert odds_close.resolve_date(_fixtures(), "X", "Y") is None


def test_watch_single_pass_alerts(tmp_path):
    fixp = tmp_path / "fx.json"
    fixp.write_text(json.dumps(_fixtures()), encoding="utf-8")
    dbp = tmp_path / "t.sqlite"
    db.init_schema(db.connect(str(dbp)))
    alerts = odds_close.watch(db_path=str(dbp), fixtures_path=str(fixp),
                              lead=15, now_fn=lambda: NOW, once=True)
    assert alerts == 2   # Spain (T-3) + C (date-only hoje); A e E ficam de fora
