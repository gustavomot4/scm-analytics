"""sigma_glicko — candidato (P-B / D-42): σ_R guiado por dados (RD estilo Glicko-1).

Problema (audit): `elo_engine.sigma_r(n)` é função quase só do nº de jogos → satura ~40
para TODA seleção estabelecida; banda/confiança quase não variam entre as elites.

Esta é a alternativa: um **RD (rating deviation) de Glicko-1**, calculado num passe
cronológico reusando os ratings pré-jogo já gravados em `match_ratings` (não re-deriva o
Elo). O RD **cresce com a inatividade** (incerteza sobe quando o time some) e **cai com
jogos informativos** (adversário definido) — exatamente o que falta ao σ atual. É
paramétrico e auditável (sem ML), respeitando o D-02.

**Candidato, OFF por padrão.** Para ADOTAR, é preciso reconstruir as features com este σ
e passar o **portão de cobertura de banda** (`report.band_coverage_binned`) — rebuild de
49k jogos roda na máquina do usuário (`--apply` grava em `ratings_glicko`; o pipeline
padrão segue usando `sigma_r`). Aqui o `main` só DEMONSTRA que o RD varia entre as elites.

Glicko-1 (Glickman): q=ln10/400; g(RD)=1/√(1+3q²RD²/π²); a cada jogo
  E=1/(1+10^(−g(RD_opp)(r−r_opp)/400)); d²=1/(q²·g²·E(1−E)); RD'=√(1/(1/RD²+1/d²)).
Inatividade: RD ← min(RD_max, √(RD² + c²·Δmeses)).
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path

from . import db
from .ingest import DEFAULT_DB

Q = math.log(10) / 400.0
RD0 = 200.0          # RD inicial (estreante) — escala σ do projeto
RD_FLOOR = 30.0      # piso (time muito ativo/consistente)
RD_MAX = 350.0       # teto (Glicko)
C_INFL = 8.0         # crescimento de RD por mês de inatividade [a calibrar]


def _g(rd: float) -> float:
    return 1.0 / math.sqrt(1.0 + 3.0 * Q * Q * rd * rd / (math.pi ** 2))


def _months(d_from, d_to) -> float:
    from datetime import date
    if not d_from:
        return 0.0
    try:
        return max(0.0, (date.fromisoformat(d_to) - date.fromisoformat(d_from)).days / 30.44)
    except (TypeError, ValueError):
        return 0.0


def _inflate(rd: float, months: float) -> float:
    return min(RD_MAX, math.sqrt(rd * rd + (C_INFL * C_INFL) * months))


def run(conn, c_infl: float = C_INFL) -> dict:
    """Passe cronológico → {team_id: RD}. Usa os Elos pré-jogo de match_ratings."""
    rows = conn.execute(
        """SELECT m.date, m.home_team_id h, m.away_team_id a,
                  mr.home_elo_pre he, mr.away_elo_pre ae
           FROM matches m JOIN match_ratings mr USING (match_id)
           ORDER BY m.date, m.match_id"""
    ).fetchall()
    rd, last = {}, {}
    for r in rows:
        h, a = r["h"], r["a"]
        hrd = _inflate(rd.get(h, RD0), _months(last.get(h), r["date"]))
        ard = _inflate(rd.get(a, RD0), _months(last.get(a), r["date"]))
        # E de cada lado usando o g(RD) do ADVERSÁRIO (pré-jogo)
        eh = 1.0 / (1.0 + 10.0 ** (-_g(ard) * (r["he"] - r["ae"]) / 400.0))
        ea = 1.0 / (1.0 + 10.0 ** (-_g(hrd) * (r["ae"] - r["he"]) / 400.0))
        for me, my_rd, opp_rd, E in ((h, hrd, ard, eh), (a, ard, hrd, ea)):
            var = E * (1.0 - E)
            if var < 1e-9:
                new = my_rd
            else:
                dsq = 1.0 / (Q * Q * _g(opp_rd) ** 2 * var)
                new = math.sqrt(1.0 / (1.0 / (my_rd * my_rd) + 1.0 / dsq))
            rd[me] = max(RD_FLOOR, new)
            last[me] = r["date"]
    return rd


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="σ Glicko (candidato): mostra o RD por seleção (varia, ≠ σ_r fixo).")
    ap.add_argument("--db", default=str(DEFAULT_DB))
    ap.add_argument("--top", type=int, default=20)
    args = ap.parse_args(argv)
    if not Path(args.db).exists():
        print(f"[erro] {args.db} não existe. Rode ingest + elo_engine antes."); return 1
    conn = db.connect(args.db)
    from .elo_engine import sigma_r, EloParams
    ep = EloParams()
    rd = run(conn)
    rows = conn.execute(
        """SELECT t.team_id, t.name, r.elo, r.n_games
           FROM ratings_current r JOIN teams t USING (team_id)
           ORDER BY r.elo DESC LIMIT ?""", (args.top,)).fetchall()
    print(f"\n  σ GLICKO (candidato) — RD por seleção vs σ_r(n) atual (que satura ~{ep.sigma_floor:.0f})")
    print(f"  {'seleção':<20}{'Elo':>6}{'jogos':>7}{'σ_r atual':>11}{'RD Glicko':>11}")
    vals = []
    for row in rows:
        sr = sigma_r(row["n_games"], ep)
        g = rd.get(row["team_id"], RD0)
        vals.append(g)
        print(f"  {row['name']:<20}{row['elo']:>6.0f}{row['n_games']:>7}{sr:>11.1f}{g:>11.1f}")
    if vals:
        print(f"\n  RD entre as top-{args.top}: min {min(vals):.0f} · máx {max(vals):.0f} · amplitude {max(vals)-min(vals):.0f}"
              f"   (σ_r atual ≈ {sigma_r(100, ep):.0f} fixo) → resolve a degenerescência")
    print("  Candidato: para ADOTAR, rebuild de features com este σ + portão de cobertura de banda.\n")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
