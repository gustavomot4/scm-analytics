"""Motor Elo: reconstrução cronológica do rating histórico (H_hist + σ_R).

Consome `matches` (do ingest) e grava:
  - `match_ratings`   : rating PRÉ-jogo de cada time (snapshot point-in-time, anti look-ahead)
  - `ratings_current` : estado final do Elo por seleção (+ σ_R, provisório se <30 jogos)

Contrato: ver vault `02 - Modelos/Elo.md` e `camada1-planejamento-v5.md` §3.1.
Constantes marcadas [a calibrar] saem do backtest (Camada 2), não do palpite.

Uso:
    python -m scm.elo_engine --db dados/scm.sqlite --top 30
"""
from __future__ import annotations

import argparse
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union

from . import db
from .ingest import DEFAULT_DB


@dataclass(frozen=True)
class EloParams:
    init: float = 1500.0            # rating inicial
    h_hist: float = 100.0           # mando histórico em jogo NÃO-neutro [a calibrar]
    provisional_games: int = 30     # <30 jogos => provisório
    sigma_floor: float = 40.0       # σ_R mínimo (muitos jogos) [a calibrar]
    sigma_provisional: float = 200.0  # σ_R de estreante (n=0) [a calibrar]
    sigma_tau: float = 20.0         # escala de decaimento de σ_R [a calibrar]


def we(dr: float) -> float:
    """Expectativa de pontuação do Elo. we(0)=0.5, we(100)≈0.640, we(-x)=1-we(x)."""
    return 1.0 / (1.0 + 10.0 ** (-dr / 400.0))


def g_factor(goal_diff: int) -> float:
    """Multiplicador de margem de gols (anti-saturação)."""
    m = abs(goal_diff)
    if m <= 1:
        return 1.0
    if m == 2:
        return 1.5
    return (11.0 + m) / 8.0


def k_factor(tournament: Optional[str]) -> float:
    """K por tipo de competição (heurística por palavra-chave) [a calibrar].

    Copa do Mundo 60 · eliminatórias 40 · Nations League 30 · amistoso 20 ·
    finais continentais 50 · competitivo desconhecido 40.
    """
    t = (tournament or "").lower()
    if "friendly" in t:
        return 20.0
    if "qualif" in t:                  # 'FIFA World Cup qualification' cai aqui (antes de World Cup)
        return 40.0
    if "nations league" in t:
        return 30.0
    if "world cup" in t:               # Copa do Mundo (final tournament)
        return 60.0
    continental = ("euro", "copa am", "copa amér", "african cup", "africa cup",
                   "afc asian", "gold cup", "oceania nations", "confederations")
    if any(kw in t for kw in continental):
        return 50.0
    return 40.0


def sigma_r(n_games: int, p: EloParams) -> float:
    """σ_R decrescente com o nº de jogos (estreante incerto -> maduro confiável)."""
    return p.sigma_floor + (p.sigma_provisional - p.sigma_floor) * math.exp(-n_games / p.sigma_tau)


def run(conn, params: EloParams = EloParams()) -> dict:
    """Reconstrói o Elo cronologicamente. Idempotente (limpa e refaz)."""
    db.init_schema(conn)
    conn.execute("DELETE FROM match_ratings")
    conn.execute("DELETE FROM ratings_current")

    ratings: dict[int, float] = {}
    ngames: dict[int, int] = {}

    rows = conn.execute(
        """SELECT match_id, date, home_team_id, away_team_id,
                  home_score, away_score, tournament, neutral
           FROM matches ORDER BY date, match_id"""
    ).fetchall()

    for r in rows:
        h, a = r["home_team_id"], r["away_team_id"]
        rh = ratings.get(h, params.init)
        ra = ratings.get(a, params.init)
        nh = ngames.get(h, 0)
        na = ngames.get(a, 0)

        mando = 0.0 if r["neutral"] else params.h_hist
        dr = rh - ra + mando
        we_home = we(dr)

        # snapshot PRÉ-jogo (point-in-time) antes de atualizar
        conn.execute(
            """INSERT OR REPLACE INTO match_ratings
               (match_id, home_elo_pre, away_elo_pre, home_n_pre, away_n_pre, dr, we_home)
               VALUES (?,?,?,?,?,?,?)""",
            (r["match_id"], rh, ra, nh, na, dr, we_home),
        )

        gd = r["home_score"] - r["away_score"]
        w = 1.0 if gd > 0 else (0.5 if gd == 0 else 0.0)
        delta = k_factor(r["tournament"]) * g_factor(gd) * (w - we_home)

        ratings[h] = rh + delta      # zero-sum: o que um ganha, o outro perde
        ratings[a] = ra - delta
        ngames[h] = nh + 1
        ngames[a] = na + 1

    for team_id, elo in ratings.items():
        n = ngames[team_id]
        conn.execute(
            """INSERT OR REPLACE INTO ratings_current
               (team_id, elo, sigma_r, n_games, provisional) VALUES (?,?,?,?,?)""",
            (team_id, elo, sigma_r(n, params), n, 1 if n < params.provisional_games else 0),
        )
    db.set_meta(conn, "elo_h_hist", params.h_hist)
    conn.commit()
    return {"matches": len(rows), "teams": len(ratings)}


def main(argv: Optional[list] = None) -> int:
    p = argparse.ArgumentParser(description="Reconstrói o Elo histórico a partir do SQLite.")
    p.add_argument("--db", default=str(DEFAULT_DB), help="caminho do SQLite (saída do ingest)")
    p.add_argument("--top", type=int, default=20, help="imprime as N maiores seleções (benchmark)")
    args = p.parse_args(argv)

    if not Path(args.db).exists():
        print(f"[erro] SQLite não encontrado: {args.db}. Rode `python -m scm.ingest` primeiro.")
        return 1

    conn = db.connect(args.db)
    stats = run(conn)
    print(f"Elo reconstruído: {stats['matches']} jogos, {stats['teams']} seleções")
    print(f"Top {args.top} (benchmark vs eloratings.net, alvo ±25 nas top-30):")
    for row in conn.execute(
        """SELECT t.name, r.elo, r.n_games, r.provisional
           FROM ratings_current r JOIN teams t USING (team_id)
           ORDER BY r.elo DESC LIMIT ?""",
        (args.top,),
    ):
        flag = " (prov)" if row["provisional"] else ""
        print(f"  {row['elo']:7.1f}  {row['name']}{flag}  [{row['n_games']}j]")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
