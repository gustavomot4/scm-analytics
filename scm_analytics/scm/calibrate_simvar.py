"""calibrate_simvar — PORTÃO da incerteza correlacionada na simulação (P-S/D-74).

CANDIDATO: `simulate.SIM_SIGMA_MODE="per_team"` sorteia UM offset de força por seleção por
simulação (compartilhado entre os jogos dela) em vez de re-sortear a cada jogo (`per_game`,
atual). Marginal por jogo IDÊNTICA (Var(off_a−off_b)=σ_a²+σ_b²); só muda a CORRELAÇÃO entre os
jogos de um mesmo time — corrige a subdispersão dos resultados de torneio (Jensen).

PORTÃO (leave-one-tournament-out, sem look-ahead): para cada Copa de 32 times (1998–2022),
reconstrói os 8 grupos do `matches`, tira o Elo/σ_R PRÉ-torneio (snapshot do `match_ratings`,
PIT), simula a fase de grupos nos dois modos e mede o **Brier de AVANÇO** (top-2) vs. o que de
fato aconteceu. Decisão = ΔBrier pareado + IC95 bootstrap (reusa `backtest_harness.gate`).
Adota só se o IC NÃO cruzar zero.

RESULTADO (2026-06, n=224 time×edição): ΔBrier +0,00010 IC95[−0,00083,+0,00105] → **cruza zero,
INCONCLUSIVO**. Mantém `per_game`. (O ganho teórico é maior em campanhas longas — título, 7 jogos
— mas o mata-mata histórico não é reconstruível limpo p/ gatear; sem evidência, não entra.)

Uso:  python -m scm.calibrate_simvar --db dados/scm.sqlite [--sims 6000]
"""
from __future__ import annotations

import argparse
from itertools import combinations
from collections import defaultdict
from pathlib import Path

import numpy as np

from . import db
from .ingest import DEFAULT_DB
from .elo_engine import sigma_r, EloParams
from .backtest_harness import gate

WC_YEARS_32 = ("1998", "2002", "2006", "2010", "2014", "2018", "2022")


def _vlam(dr):
    """Versão vetorizada de predictor.lambdas (forma linear default + piso conservando T_m).

    Espelha o núcleo; `_selfcheck()` garante que não divergiu da fonte. dr: np.ndarray."""
    gd = 0.45 * dr / 100.0
    tm = 2.6 + 0.10 * np.abs(dr) / 100.0
    la = (tm + gd) / 2.0
    lb = (tm - gd) / 2.0
    lmin = 0.15
    m1 = lb < lmin
    la = np.where(m1, np.maximum(lmin, tm - lmin), la); lb = np.where(m1, lmin, lb)
    m2 = (~m1) & (la < lmin)
    lb = np.where(m2, np.maximum(lmin, tm - lmin), lb); la = np.where(m2, lmin, la)
    return la, lb


def _selfcheck():
    """Garante que _vlam == predictor.lambdas (linear) numa grade — pega drift do núcleo."""
    from .predictor import lambdas, PredictParams
    p = PredictParams()
    drs = np.array([-2500., -800., -300., -50., 0., 50., 300., 800., 2500.])
    la, lb = _vlam(drs)
    for k, d in enumerate(drs):
        ea, eb = lambdas(float(d), p)
        assert abs(la[k] - ea) < 1e-9 and abs(lb[k] - eb) < 1e-9, f"_vlam divergiu de lambdas em dr={d}"


def _edition_rows(conn, year):
    return conn.execute(
        """SELECT th.name h, ta.name a, m.home_score hs, m.away_score s,
                  mr.home_elo_pre he, mr.away_elo_pre ae, mr.home_n_pre hn, mr.away_n_pre an
           FROM matches m JOIN match_ratings mr USING (match_id)
           JOIN teams th ON th.team_id=m.home_team_id JOIN teams ta ON ta.team_id=m.away_team_id
           WHERE m.tournament='FIFA World Cup' AND substr(m.date,1,4)=? ORDER BY m.date""",
        (year,)).fetchall()


def _reconstruct_groups(rows):
    """8 grupos do round-robin: os 3 primeiros adversários de cada time = seus companheiros."""
    seq = defaultdict(list)
    for r in rows:
        seq[r["h"]].append(r["a"]); seq[r["a"]].append(r["h"])
    groups = []; seen = set()
    for t in sorted(seq):
        if t in seen:
            continue
        grp = set([t] + seq[t][:3])
        if len(grp) == 4 and all(len(set(seq[x][:3]) | {x}) == 4 for x in grp):
            groups.append(sorted(grp)); seen |= grp
    return groups


def _pit(rows):
    elo = {}; npre = {}
    for r in rows:
        if r["h"] not in elo: elo[r["h"]] = r["he"]; npre[r["h"]] = r["hn"]
        if r["a"] not in elo: elo[r["a"]] = r["ae"]; npre[r["a"]] = r["an"]
    return elo, npre


def _actual_top2(group, rows):
    pts = {t: 0 for t in group}; gf = {t: 0 for t in group}; ga = {t: 0 for t in group}
    for r in rows:
        if r["h"] in group and r["a"] in group and r["hs"] is not None:
            h, a, hs, s = r["h"], r["a"], r["hs"], r["s"]
            gf[h] += hs; ga[h] += s; gf[a] += s; ga[a] += hs
            if hs > s: pts[h] += 3
            elif s > hs: pts[a] += 3
            else: pts[h] += 1; pts[a] += 1
    rank = sorted(group, key=lambda t: (pts[t], gf[t] - ga[t], gf[t]), reverse=True)
    return set(rank[:2])


def _p_advance(group, elo, sig, mode, n, seed):
    rng = np.random.default_rng(seed); T = len(group)
    pairs = list(combinations(range(T), 2))
    dr0 = np.array([elo[group[i]] - elo[group[j]] for i, j in pairs])[:, None]
    if mode == "per_team":
        off = np.array([rng.normal(0.0, sig.get(t, 0.0), n) for t in group])
        dr = np.stack([dr0[k, 0] + off[i] - off[j] for k, (i, j) in enumerate(pairs)])
    else:
        sd = np.array([(sig.get(group[i], 0.0) ** 2 + sig.get(group[j], 0.0) ** 2) ** 0.5
                       for i, j in pairs])[:, None]
        dr = dr0 + rng.normal(0, 1, (len(pairs), n)) * sd
    la, lb = _vlam(dr); gi = rng.poisson(la); gj = rng.poisson(lb)
    pts = np.zeros((T, n)); gf = np.zeros((T, n)); ga = np.zeros((T, n))
    for k, (i, j) in enumerate(pairs):
        a, b = gi[k], gj[k]
        gf[i] += a; ga[i] += b; gf[j] += b; ga[j] += a
        pts[i] += 3 * (a > b) + (a == b); pts[j] += 3 * (b > a) + (a == b)
    order = np.argsort(-(pts * 1e6 + (gf - ga) * 1e3 + gf), axis=0)
    return {group[ti]: float(np.mean((order[0] == ti) | (order[1] == ti))) for ti in range(T)}


def run_gate(conn, sims=6000, B=10000, seed=12345):
    _selfcheck()
    EP = EloParams(); deltas = []; bpg = bpt = 0.0; nobs = 0; eds = 0
    for y in WC_YEARS_32:
        rows = _edition_rows(conn, y)
        if not rows:
            continue
        groups = _reconstruct_groups(rows)
        if len(groups) != 8:
            continue
        elo, npre = _pit(rows); sig = {t: sigma_r(npre.get(t, 0), EP) for t in elo}; eds += 1
        for gi_, grp in enumerate(groups):
            if any(t not in elo for t in grp):
                continue
            act = _actual_top2(grp, rows); sd = hash((y, gi_)) & 0xffff
            pg = _p_advance(grp, elo, sig, "per_game", sims, sd)
            pt = _p_advance(grp, elo, sig, "per_team", sims, sd)
            for t in grp:
                o = 1.0 if t in act else 0.0
                x = (pg[t] - o) ** 2; z = (pt[t] - o) ** 2
                bpg += x; bpt += z; deltas.append(x - z); nobs += 1
    if not deltas:
        return {"n": 0}
    g = gate(deltas, B=B, seed=seed)
    return {"n": nobs, "edicoes": eds, "brier_per_game": bpg / nobs, "brier_per_team": bpt / nobs, **g}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Portão da incerteza correlacionada na simulação (P-S/D-74).")
    ap.add_argument("--db", default=str(DEFAULT_DB))
    ap.add_argument("--sims", type=int, default=6000)
    args = ap.parse_args(argv)
    if not Path(args.db).exists():
        print(f"[erro] {args.db} não existe. Rode ingest + elo_engine antes."); return 1
    conn = db.connect(args.db); r = run_gate(conn, sims=args.sims); conn.close()
    if not r.get("n"):
        print("sem dados (precisa de match_ratings das Copas de 32 times)."); return 1
    print(f"\n  PORTÃO σ por-time na simulação  (n={r['n']} time×edição, {r['edicoes']} Copas)")
    print(f"  Brier avanço: per_game {r['brier_per_game']:.5f}  vs  per_team {r['brier_per_team']:.5f}")
    print(f"  ΔBrier (per_game − per_team, >0 = per_team melhor) = {r['mean']:+.5f}  IC95 [{r['ic_lo']:+.5f}, {r['ic_hi']:+.5f}]")
    keep = r["keep"]
    msg = ('ADOTAR per_team: ligue config.SIM_SIGMA_MODE="per_team"' if keep
           else 'NÃO adotar (IC cruza/≤0) — mantém per_game')
    print("  → " + msg + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
