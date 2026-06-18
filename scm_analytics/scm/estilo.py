"""estilo — tendência ofensiva/defensiva por seleção (feature DORMENTE do contrato v5).

`estilo_T = shrink( gols/jogo nos jogos de T  /  média global )`, encolhido a 1.0.
Entra como multiplicador do total esperado: `T_m_match = T_m(dr) · estilo_A · estilo_B`
(predictor.lambdas já aceita estilo_a/estilo_b). Dupla ofensiva → T_m maior → **BTTS sobe**;
dupla defensiva → BTTS cai. É a alavanca natural do "ambos marcam".

Como toca λ, é CANDIDATO ao portão. E como o estilo move o TOTAL (não o 1X2), o portão
mede a **Brier de BTTS** (a métrica que ele de fato afeta) — mesma lição do calor (D-19).
Treino/teste por `cutoff` evita look-ahead. Sem rede; roda local.
"""
from __future__ import annotations

import argparse

from . import db
from .ingest import DEFAULT_DB

SHRINK_K = 30.0          # "jogos equivalentes" de prior em 1.0 (estabilidade) [a calibrar]
CAP_LO, CAP_HI = 0.80, 1.25   # limites do estilo (evita extrapolar caudas)


def team_styles(conn, before_date=None):
    """{team_id: estilo} pela razão de gols/jogo dos jogos do time vs média global.

    PIT quando `before_date` é dado (usa só jogos anteriores) — exigido no portão.
    """
    q = ("SELECT home_team_id, away_team_id, home_score, away_score FROM matches "
         "WHERE home_score IS NOT NULL AND away_score IS NOT NULL")
    args = ()
    if before_date:
        q += " AND date < ?"
        args = (before_date,)
    tot = 0.0
    n = 0
    per = {}
    for h, a, hs, as_ in conn.execute(q, args):
        g = (hs or 0) + (as_ or 0)
        tot += g
        n += 1
        for t in (h, a):
            per.setdefault(t, [0.0, 0])
            per[t][0] += g
            per[t][1] += 1
    if n == 0:
        return {}, 1.0
    gmean = tot / n
    styles = {}
    for t, (s, c) in per.items():
        obs = (s / c) / gmean if c and gmean > 0 else 1.0
        sh = (c * obs + SHRINK_K * 1.0) / (c + SHRINK_K)     # encolhe a 1.0
        styles[t] = min(CAP_HI, max(CAP_LO, sh))
    return styles, gmean


def gate_estilo(conn, cutoff="2015-01-01", only_major=True, B=3000, seed=12345):
    """Portão treino/teste: estilo (treino<cutoff) aplicado ao teste (≥cutoff).

    Mede ΔBrier de **BTTS** (e de 1X2, para referência). keep = IC95 de ΔBrier_BTTS > 0.
    """
    from .predictor import PredictParams, predict
    from .backtest_harness import gate, outcome_of, brier, MAJOR

    styles, _ = team_styles(conn, before_date=cutoff)
    rows = conn.execute(
        """SELECT m.home_team_id h, m.away_team_id a, m.home_score hs, m.away_score s,
                  f.dr_adj dr, f.sigma_dr sg, m.tournament t
           FROM match_features f JOIN matches m USING (match_id)
           WHERE m.home_score IS NOT NULL AND m.away_score IS NOT NULL AND m.date >= ?""",
        (cutoff,)).fetchall()
    p = PredictParams()
    d_btts, d_1x2 = [], []
    mp_b = mp_e = ar = 0.0
    n = 0
    for r in rows:
        if only_major and r["t"] not in MAJOR:
            continue
        ea = styles.get(r["h"], 1.0)
        eb = styles.get(r["a"], 1.0)
        if ea == 1.0 and eb == 1.0:     # estilo não informa este jogo → não conta
            continue
        o = outcome_of(r["hs"], r["s"])
        act = 1.0 if (r["hs"] > 0 and r["s"] > 0) else 0.0
        base = predict(r["dr"], r["sg"], p)
        est = predict(r["dr"], r["sg"], p, estilo_a=ea, estilo_b=eb)
        d_btts.append((base["p_btts"] - act) ** 2 - (est["p_btts"] - act) ** 2)
        d_1x2.append(brier(base, o) - brier(est, o))
        mp_b += base["p_btts"]
        mp_e += est["p_btts"]
        ar += act
        n += 1
    if n == 0:
        return {"n": 0}
    gb = gate(d_btts, B, seed)
    g1 = gate(d_1x2, B, seed)
    return {"n": n, "btts": gb, "x12": g1,
            "btts_pred_base": mp_b / n, "btts_pred_estilo": mp_e / n, "btts_actual": ar / n}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Estilo (tendência de gols) + portão na Brier de BTTS.")
    p.add_argument("--db", default=str(DEFAULT_DB))
    p.add_argument("--cutoff", default="2015-01-01", help="treino<cutoff, teste≥cutoff")
    p.add_argument("--all", action="store_true", help="não restringe a torneios major")
    p.add_argument("--list", action="store_true", help="lista seleções mais ofensivas/defensivas")
    args = p.parse_args(argv)
    conn = db.connect(args.db)
    if args.list:
        st, gm = team_styles(conn)
        named = sorted(((conn.execute("SELECT name FROM teams WHERE team_id=?", (t,)).fetchone()[0], v)
                        for t, v in st.items()), key=lambda x: -x[1])
        print(f"\n  média global de gols/jogo: {gm:.2f}   (estilo>1 = jogos com mais gols)")
        print("  + ofensivas:", " · ".join(f"{nm} {v:.2f}" for nm, v in named[:8]))
        print("  + defensivas:", " · ".join(f"{nm} {v:.2f}" for nm, v in named[-8:]))
        conn.close(); return 0
    r = gate_estilo(conn, args.cutoff, only_major=not args.all)
    conn.close()
    if r.get("n", 0) == 0:
        print("[!] sem jogos de teste com estilo conhecido. Rode o pipeline (features_pit/predictor) antes.")
        return 1
    print(f"\n  PORTÃO do ESTILO  (teste ≥ {args.cutoff}, n={r['n']} jogos)")
    print(f"  BTTS previsto:  base {r['btts_pred_base']*100:.1f}%  →  com estilo {r['btts_pred_estilo']*100:.1f}%"
          f"   |  real {r['btts_actual']*100:.1f}%")
    gb, g1 = r["btts"], r["x12"]
    decis = "ADOTAR ✓" if gb["keep"] else "não adotar (IC cruza 0)"
    print(f"  ΔBrier BTTS: {gb['mean']:+.4f}  IC95 [{gb['ic_lo']:+.4f}, {gb['ic_hi']:+.4f}]   → {decis}")
    print(f"  ΔBrier 1X2 (ref): {g1['mean']:+.4f}  IC95 [{g1['ic_lo']:+.4f}, {g1['ic_hi']:+.4f}]")
    print("  (estilo move o TOTAL/BTTS, não o 1X2 — por isso o portão é na Brier de BTTS.)\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
