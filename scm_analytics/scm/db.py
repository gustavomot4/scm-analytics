"""Camada de dados: schema SQLite e helpers de conexão.

Baseline da Camada 2. Sem dependências externas (sqlite3 stdlib).
Schema espelha a nota do vault: `03 - Dados/Esquema SQLite.md`.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Union

SCHEMA = """
CREATE TABLE IF NOT EXISTS teams (
    team_id         INTEGER PRIMARY KEY,
    name            TEXT NOT NULL UNIQUE,
    confederation   TEXT,
    home_altitude_m REAL
);
CREATE TABLE IF NOT EXISTS matches (
    match_id     INTEGER PRIMARY KEY,
    date         TEXT    NOT NULL,
    home_team_id INTEGER NOT NULL REFERENCES teams(team_id),
    away_team_id INTEGER NOT NULL REFERENCES teams(team_id),
    home_score   INTEGER NOT NULL,
    away_score   INTEGER NOT NULL,
    tournament   TEXT,
    city         TEXT,
    country      TEXT,
    neutral      INTEGER NOT NULL DEFAULT 0,
    natural_key  TEXT    NOT NULL UNIQUE
);
CREATE INDEX IF NOT EXISTS idx_matches_date ON matches(date);
CREATE INDEX IF NOT EXISTS idx_matches_home ON matches(home_team_id);
CREATE INDEX IF NOT EXISTS idx_matches_away ON matches(away_team_id);
-- compostos (home/away, date): aceleram a busca de forma point-in-time em features_pit
-- (a consulta filtra por time E date < t; o indice de coluna unica nao cobria o OR).
CREATE INDEX IF NOT EXISTS idx_matches_home_date ON matches(home_team_id, date);
CREATE INDEX IF NOT EXISTS idx_matches_away_date ON matches(away_team_id, date);
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT
);
CREATE TABLE IF NOT EXISTS ratings_current (
    team_id     INTEGER PRIMARY KEY REFERENCES teams(team_id),
    elo         REAL    NOT NULL,
    sigma_r     REAL    NOT NULL,
    n_games     INTEGER NOT NULL,
    provisional INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS match_ratings (
    match_id     INTEGER PRIMARY KEY REFERENCES matches(match_id),
    home_elo_pre REAL,
    away_elo_pre REAL,
    home_n_pre   INTEGER,
    away_n_pre   INTEGER,
    dr           REAL,
    we_home      REAL
);
CREATE TABLE IF NOT EXISTS match_features (
    match_id          INTEGER PRIMARY KEY REFERENCES matches(match_id),
    dr_elo            REAL,
    form_home         REAL,
    form_away         REAL,
    dr_adj            REAL,
    sigma_r_home      REAL,
    sigma_r_away      REAL,
    sigma_ajuste_home REAL,
    sigma_ajuste_away REAL,
    sigma_dr          REAL,
    n_home_pre        INTEGER,
    n_away_pre        INTEGER
);
CREATE TABLE IF NOT EXISTS predictions (
    match_id      INTEGER NOT NULL REFERENCES matches(match_id),
    versao_modelo TEXT    NOT NULL,
    p_v REAL, p_e REAL, p_d REAL,
    band_pv_lo REAL, band_pv_hi REAL,
    lambda_a REAL, lambda_b REAL,
    p_over25 REAL, p_btts REAL,
    PRIMARY KEY (match_id, versao_modelo)
);
-- odds de mercado (D-44 / P-H): probabilidades JÁ sem vig (de-vigged), por fonte.
-- 3a perna do ensemble (peso 0.20, contrato §3.8) quando houver; captura manual (sem
-- histórico gratuito). natural_key = date|home|away p/ casar jogos futuros sem match_id.
CREATE TABLE IF NOT EXISTS odds_hist (
    natural_key TEXT NOT NULL,
    match_id    INTEGER REFERENCES matches(match_id),
    p_home REAL, p_draw REAL, p_away REAL,
    source TEXT,
    asof   TEXT,
    PRIMARY KEY (natural_key, source)
);
-- xG por seleção (esqueleto, D-50): médias de xG pró/contra do StatsBomb Open Data
-- (cobertura parcial: 2018/2022/Euro). Prior de "estilo" menos ruidoso que gols brutos.
-- Candidato — NÃO entra em λ sem passar pelo portão. Ingerido por `scm.xg`.
CREATE TABLE IF NOT EXISTS team_xg (
    team_id   INTEGER PRIMARY KEY REFERENCES teams(team_id),
    xg_for    REAL,
    xg_against REAL,
    n_games   INTEGER,
    source    TEXT
);
"""


def connect(db_path: Union[str, Path]) -> sqlite3.Connection:
    """Abre conexão SQLite com row_factory e FKs ligadas. Use ':memory:' nos testes."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


def get_or_create_team(conn: sqlite3.Connection, name: str) -> int:
    """Retorna team_id, criando a seleção se necessário. Idempotente por `name`."""
    row = conn.execute("SELECT team_id FROM teams WHERE name = ?", (name,)).fetchone()
    if row is not None:
        return row["team_id"]
    cur = conn.execute("INSERT INTO teams(name) VALUES (?)", (name,))
    return int(cur.lastrowid)


def set_meta(conn: sqlite3.Connection, key: str, value: object) -> None:
    conn.execute(
        "INSERT INTO meta(key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, str(value)),
    )
    conn.commit()
