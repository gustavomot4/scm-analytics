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


def run_pit(conn) -> dict:
    """{match_id: (home_rd_pre, away_rd_pre)} — RD PRÉ-jogo (point-in-time) p/ backtest/portão."""
    rows = conn.execute(
        """SELECT m.match_id, m.date, m.home_team_id h, m.away_team_id a,
                  mr.home_elo_pre he, mr.away_elo_pre ae
           FROM matches m JOIN match_ratings mr USING (match_id)
           ORDER BY m.date, m.match_id"""
    ).fetchall()
    rd, last, out = {}, {}, {}
    for r in rows:
        h, a = r["h"], r["a"]
        hrd = _inflate(rd.get(h, RD0), _months(last.get(h), r["date"]))
        ard = _inflate(rd.get(a, RD0), _months(last.get(a), r["date"]))
        out[r["match_id"]] = (hrd, ard)        # snapshot ANTES de atualizar (anti look-ahead)
        eh = 1.0 / (1.0 + 10.0 ** (-_g(ard) * (r["he"] - r["ae"]) / 400.0))
        ea = 1.0 / (1.0 + 10.0 ** (-_g(hrd) * (r["ae"] - r["he"]) / 400.0))
        for me, my_rd, opp_rd, E in ((h, hrd, ard, eh), (a, ard, hrd, ea)):
            var = E * (1.0 - E)
            new = my_rd if var < 1e-9 else math.sqrt(1.0 / (1.0 / (my_rd * my_rd)
                                                            + Q * Q * _g(opp_rd) ** 2 * var))
            rd[me] = max(RD_FLOOR, new)
            last[me] = r["date"]
    return out


def gate_band(conn, versao=None, only_major=True) -> dict:
    """Portão de σ: cobertura de banda (por faixa de p_v) com σ_R atual vs RD-Glicko PIT.

    Adotar SÓ se o Glicko aproximar a cobertura do nominal (~68%). RESULTADO no DB local
    (martj42, recorte torneios): a banda ATUAL já SOBRE-cobre (~92% vs 68%) e o Glicko a
    ALARGA mais (largura 0,134→0,184) sem melhorar → **não adotar**. Sinaliza que o ajuste
    certo seria ENCOLHER σ_dr (banda larga demais), não trocar por Glicko. Candidato OFF.
    """
    from .predictor import PredictParams, elo_direct_read
    from .report import band_coverage_binned
    from .backtest_harness import MAJOR
    from .predictor import MODEL_VERSION
    p = PredictParams()
    versao = versao or MODEL_VERSION
    q = ("SELECT p.match_id, p.p_v, p.band_pv_lo lo, p.band_pv_hi hi, f.dr_adj dr, "
         "f.sigma_ajuste_home sah, f.sigma_ajuste_away saa, m.home_score hs, m.away_score s "
         "FROM predictions p JOIN match_features f USING(match_id) JOIN matches m USING(match_id) "
         "WHERE p.versao_modelo=? AND m.home_score IS NOT NULL")
    params = [versao]
    if only_major:
        q += " AND m.tournament IN (%s)" % ",".join("?" * len(MAJOR))
        params += list(MAJOR)
    rows = conn.execute(q, params).fetchall()
    if not rows:
        return {"n": 0}
    pit = run_pit(conn)
    old_i, new_i = [], []
    for r in rows:
        hw = 1 if r["hs"] > r["s"] else 0
        old_i.append({"p_v": r["p_v"], "lo": r["lo"], "hi": r["hi"], "home_won": hw})
        rd_h, rd_a = pit[r["match_id"]]
        sdr = math.sqrt(rd_h ** 2 + rd_a ** 2 + r["sah"] ** 2 + r["saa"] ** 2)
        e = elo_direct_read(r["dr"], sdr, p)
        new_i.append({"p_v": r["p_v"], "lo": e["band_lo"], "hi": e["band_hi"], "home_won": hw})
    co = band_coverage_binned(old_i); cn = band_coverage_binned(new_i)
    adota = (cn["n_bins_covered"] > co["n_bins_covered"]
             or abs((cn["coverage_weighted"] or 0) - 0.68) < abs((co["coverage_weighted"] or 0) - 0.68) - 0.02)
    return {"n": len(rows), "old": co, "new": cn, "adota": bool(adota)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="σ Glicko (candidato): mostra o RD por seleção (varia, ≠ σ_r fixo).")
    ap.add_argument("--db", default=str(DEFAULT_DB))
    ap.add_argument("--top", type=int, default=20)
    ap.add_argument("--gate", action="store_true", help="portão de cobertura de banda (σ atual vs Glicko)")
    args = ap.parse_args(argv)
    if not Path(args.db).exists():
        print(f"[erro] {args.db} não existe. Rode ingest + elo_engine antes."); return 1
    conn = db.connect(args.db)
    if args.gate:
        g = gate_band(conn)
        conn.close()
        if not g.get("n"):
            print("sem dados p/ o portão (rode o pipeline)."); return 1
        co, cn = g["old"], g["new"]
        print(f"\n  PORTÃO σ (cobertura de banda, n={g['n']}, nominal ~68%)")
        print(f"  σ ATUAL : {co['n_bins_covered']}/{co['n_bins']} faixas · cobertura {co['coverage_weighted']*100:.0f}% · largura {co['mean_width']:.3f}")
        print(f"  σ GLICKO: {cn['n_bins_covered']}/{cn['n_bins']} faixas · cobertura {cn['coverage_weighted']*100:.0f}% · largura {cn['mean_width']:.3f}")
        print(f"  → {'ADOTAR Glicko ✓' if g['adota'] else 'NÃO adotar — banda já sobre-cobre; Glicko alarga mais (manter σ_r)'}\n")
        return 0
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
