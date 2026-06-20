"""altitude (E1) — PORTÃO do termo GD_alt (McSharry), atrás do critério de aceite.

O TERMO PURO (gd_alt e tabelas de elevação) foi movido p/ `scm/factors.py` para quebrar o
ciclo de import `predictor↔altitude` (audit, arquitetura). Aqui ficam só os PORTÕES, que
precisam de `predictor` + `backtest_harness` (avaliação). Os nomes puros são REEXPORTADOS
abaixo, então `from .altitude import gd_alt` segue funcionando.

McSharry (BMJ 2007): ~½ gol de saldo por 1000 m de diferença; só morde p/ o time não-adaptado
jogando em sede alta. Aceite (portão): `gate_altitude` compara v0.1 vs v0.1+GD_alt SÓ nos jogos
de altitude; mantém o termo SSE o IC do ΔBrier não cruza zero. Ver `02 - Modelos/Ajustes ambientais`.
"""
from __future__ import annotations

import argparse

from . import db
from .predictor import PredictParams, predict
from .backtest_harness import brier, outcome_of, gate
from .ingest import DEFAULT_DB
# termo puro + tabelas (agora em factors.py) — reexportados p/ compatibilidade
from .factors import (THETA_ALT, _norm, CITY_ALT, TEAM_HOME_ALT, MX_CITIES,
                      venue_alt, team_alt, gd_alt, confederation_of, seed_team_altitudes,
                      load_elevations)


def gate_altitude(conn, versao: str = "baseline-v0.1", theta: float = THETA_ALT,
                  B: int = 10000, seed: int = 12345) -> dict:
    """Portão do termo de altitude: compara v0.1 vs v0.1+GD_alt SÓ nos jogos de altitude."""
    rows = conn.execute(
        """SELECT mf.dr_adj AS dr, mf.sigma_dr AS sg, m.home_score AS hs, m.away_score AS a,
                  m.city AS city, th.name AS home, ta.name AS away
           FROM match_features mf JOIN matches m USING (match_id)
           JOIN teams th ON th.team_id = m.home_team_id
           JOIN teams ta ON ta.team_id = m.away_team_id"""
    ).fetchall()
    p = PredictParams()
    deltas = []
    for r in rows:
        ga = gd_alt(r["city"], r["home"], r["away"], theta)
        if abs(ga) < 1e-9:
            continue  # só jogos onde a altitude de fato morde
        o = outcome_of(r["hs"], r["a"])
        base = predict(r["dr"], r["sg"], p)
        alt = predict(r["dr"], r["sg"], p, gd_alt=ga)
        b0 = brier({"p_v": base["p_v"], "p_e": base["p_e"], "p_d": base["p_d"]}, o)
        b1 = brier({"p_v": alt["p_v"], "p_e": alt["p_e"], "p_d": alt["p_d"]}, o)
        deltas.append(b0 - b1)  # >0 = altitude melhora o Brier
    if not deltas:
        return {"n_alt": 0, "keep": False}
    g = gate(deltas, B=B, seed=seed)
    return {"n_alt": len(deltas), **g}


def gate_by_confederation(conn, theta: float = THETA_ALT, B: int = 10000, seed: int = 12345) -> dict:
    """Portão da altitude SEPARADO por confederação — revisa se θ deveria diferir (audit).

    Achado no DB local: θ=0,5 sustenta nas DUAS. CONMEBOL ΔBrier ~+0,066 IC[+0,035,+0,096];
    CONCACAF ~+0,023 IC[+0,001,+0,045] (mais fraco, porém positivo; θ ótimo ≈0,5 em ambas).
    Mantém θ único = 0,5.
    """
    rows = conn.execute(
        """SELECT mf.dr_adj dr, mf.sigma_dr sg, m.home_score hs, m.away_score a,
                  m.city city, th.name home, ta.name away
           FROM match_features mf JOIN matches m USING (match_id)
           JOIN teams th ON th.team_id = m.home_team_id
           JOIN teams ta ON ta.team_id = m.away_team_id
           WHERE m.home_score IS NOT NULL"""
    ).fetchall()
    p = PredictParams()
    by = {}
    for r in rows:
        conf = confederation_of(r["city"])
        if not conf:
            continue
        ga = gd_alt(r["city"], r["home"], r["away"], theta)
        if abs(ga) < 1e-9:
            continue
        o = outcome_of(r["hs"], r["a"])
        b0 = brier(predict(r["dr"], r["sg"], p), o)
        b1 = brier(predict(r["dr"], r["sg"], p, gd_alt=ga), o)
        by.setdefault(conf, []).append(b0 - b1)
    return {conf: {"n": len(d), **gate(d, B=B, seed=seed)} for conf, d in by.items()}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Portão do termo de altitude (E1).")
    p.add_argument("--db", default=str(DEFAULT_DB))
    p.add_argument("--theta", type=float, default=THETA_ALT)
    p.add_argument("--by-confed", action="store_true", help="portão separado por confederação (CONMEBOL vs CONCACAF)")
    p.add_argument("--seed-db", action="store_true", help="popula teams.home_altitude_m (N-D) e sai")
    p.add_argument("--load-elevations", default=None, metavar="CSV",
                   help="ingere elevações de um CSV (type,name,elevation_m) -> venues + teams (#7b) e sai")
    args = p.parse_args(argv)
    conn = db.connect(args.db)
    if args.load_elevations:
        r = load_elevations(conn, args.load_elevations)
        conn.close()
        print(f"elevações ingeridas: {r['venues']} sedes (venues) · {r['teams']} seleções (home_altitude_m).")
        return 0
    if args.seed_db:
        n = seed_team_altitudes(conn)
        conn.close()
        print(f"teams.home_altitude_m populado p/ {n} seleções (a partir de TEAM_HOME_ALT).")
        return 0
    if args.by_confed:
        res = gate_by_confederation(conn, theta=args.theta)
        conn.close()
        if not res:
            print("nenhum jogo de altitude encontrado."); return 1
        print(f"Portão da altitude por confederação (θ={args.theta}):")
        for conf, g in sorted(res.items()):
            print(f"  {conf}: n={g['n']}  ΔBrier {g['mean']:+.4f}  IC95 [{g['ic_lo']:+.4f}, {g['ic_hi']:+.4f}]"
                  f"  -> {'mantém' if g['keep'] else 'NÃO sustenta'}")
        return 0
    r = gate_altitude(conn, theta=args.theta)
    conn.close()
    if r["n_alt"] == 0:
        print("nenhum jogo de altitude encontrado (cidades em CITY_ALT)."); return 1
    print(f"jogos de altitude: n={r['n_alt']}  (θ_alt={args.theta})")
    print(f"ganho de Brier (com altitude) = {r['mean']:+.4f}  IC95 [{r['ic_lo']:+.4f}, {r['ic_hi']:+.4f}]")
    print(f"MANTER altitude? (IC não cruza 0) -> {'SIM' if r['keep'] else 'NÃO'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
