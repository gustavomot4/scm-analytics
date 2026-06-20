"""factors — termos PUROS de λ/dr e constantes de domínio (sem I/O, sem ciclo de import).

Audit (arquitetura): a lógica de PREDIÇÃO usada em produção (o termo de altitude `gd_alt`)
vivia em `altitude.py`, que TAMBÉM importa `predictor` e `backtest_harness` para rodar os
PORTÕES — o que criava um ciclo de import (`predictor` precisava de um `import tardio` de
`altitude` dentro de `run()`). Aqui ficam só os termos puros (sem dependências pesadas):
`predictor` importa daqui no TOPO (sem ciclo), e `altitude.py` mantém apenas os portões de
avaliação, reexportando estes nomes p/ compatibilidade (`from .altitude import gd_alt` segue
funcionando).

Contrato: altitude (E1) em `02 - Modelos/Ajustes ambientais.md` / `camada1-planejamento-v5 §3.13`.
"""
from __future__ import annotations

import unicodedata
from typing import Optional

from .config import THETA_ALT  # fonte única dos coeficientes (arquitetura); McSharry BMJ 2007


def _norm(s) -> str:
    """minúsculas + sem acentos (casa 'Bogotá'/'bogota'/'Ciudad de México' etc.)."""
    s = unicodedata.normalize("NFKD", (s or "").strip().lower())
    return "".join(ch for ch in s if not unicodedata.combining(ch))


# Elevação (m) das cidades-sede de altitude. Fatos públicos aproximados — [verificar via
# Open-Meteo Elevation]. Limiar prático ~1500 m (Monterrey 540 m = nível do mar). Inclui as
# sedes ALTAS da Copa 2026: Cidade do México (2240) e Guadalajara/Zapopan (1566).
CITY_ALT = {
    "la paz": 3637, "el alto": 4150, "oruro": 3706, "potosi": 4070, "cochabamba": 2558,
    "sucre": 2810, "quito": 2850, "bogota": 2640, "cusco": 3399, "cuzco": 3399,
    "arequipa": 2335, "pasto": 2527,
    "mexico city": 2240, "ciudad de mexico": 2240, "toluca": 2660, "puebla": 2135,
    "guadalajara": 1566, "zapopan": 1566,
}
# Altitude "de casa" das seleções adaptadas (m). Default 0 (litoral). [verificar]
TEAM_HOME_ALT = {"Bolivia": 3637, "Ecuador": 2850, "Colombia": 2640, "Mexico": 2240}
# Sedes de altitude da CONCACAF (México); o restante de CITY_ALT é CONMEBOL.
MX_CITIES = {"mexico city", "ciudad de mexico", "toluca", "puebla", "guadalajara", "zapopan"}


def venue_alt(city) -> float:
    return float(CITY_ALT.get(_norm(city), 0.0))


def team_alt(name) -> float:
    return float(TEAM_HOME_ALT.get(name, 0.0))


def gd_alt(city, home_team, away_team, theta: float = THETA_ALT) -> float:
    """Termo de saldo por altitude (E1, McSharry): favorece quem está adaptado à sede alta.

        pen(T) = max(0, elev_sede − elev_casa_T)
        GD_alt = θ_alt · (pen_away − pen_home) / 1000
    """
    v = venue_alt(city)
    pen_home = max(0.0, v - team_alt(home_team))
    pen_away = max(0.0, v - team_alt(away_team))
    return theta * (pen_away - pen_home) / 1000.0


def confederation_of(city) -> Optional[str]:
    """'CONCACAF' / 'CONMEBOL' / None (sem altitude) p/ a cidade-sede."""
    if venue_alt(city) <= 0:
        return None
    return "CONCACAF" if _norm(city) in MX_CITIES else "CONMEBOL"


def seed_team_altitudes(conn) -> int:
    """Popula teams.home_altitude_m a partir de TEAM_HOME_ALT (audit N-D: coluna existia no
    schema mas nunca era preenchida). Idempotente; retorna nº de seleções atualizadas. A coluna
    passa a ser o store canônico/consultável; o dict segue como fallback do caminho sem `conn`
    (gd_alt não recebe conexão). Rode `python -m scm.altitude --seed-db` após o ingest."""
    n = 0
    for name, alt in TEAM_HOME_ALT.items():
        n += conn.execute("UPDATE teams SET home_altitude_m=? WHERE name=?",
                          (float(alt), name)).rowcount
    conn.commit()
    return n


def load_elevations(conn, csv_path) -> dict:
    """Ingere elevações de um CSV (snapshot, N-D/#7b) -> `venues` + `teams.home_altitude_m`.

    CSV: `type,name,elevation_m` (type ∈ {venue, team}). Faz das elevações um dado em BANCO,
    auditável e extensível, em vez de só dos dicts no código (gere o CSV uma vez via Open-Meteo
    Elevation / Wikidata — nada lê a internet no cálculo). O runtime ainda usa CITY_ALT/
    TEAM_HOME_ALT por velocidade (gd_alt sem conn); o DB é o store de referência. Idempotente."""
    import csv as _csv
    from . import db as _db
    _db.init_schema(conn)
    nv = nt = 0
    with open(csv_path, encoding="utf-8") as fh:
        for r in _csv.DictReader(fh):
            typ = (r.get("type") or "").strip().lower()
            name = (r.get("name") or "").strip()
            try:
                elev = float(r["elevation_m"])
            except (KeyError, ValueError, TypeError):
                continue
            if not name:
                continue
            if typ == "team":
                nt += conn.execute("UPDATE teams SET home_altitude_m=? WHERE lower(name)=lower(?)",
                                  (elev, name)).rowcount
            else:
                conn.execute("INSERT INTO venues(name, elevation_m) VALUES (?,?)", (name, elev))
                nv += 1
    conn.commit()
    return {"venues": nv, "teams": nt}
