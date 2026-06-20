"""calibrate_recency — candidato (P-M): reversão à média no Elo, atrás do portão. REJEITADO.

A auditoria notou que o Elo nunca regride (Colômbia>Brasil; valores ~70–210 acima do
eloratings). Este módulo TESTA a reversão à média PIT (`EloParams.revert_half_life_months`):
antes de cada jogo, puxa o rating rumo a `init` por 0.5^(meses_parado/half_life), recompondo
o `dr` (e a expectativa da forma) de forma consistente.

RESULTADO [verificado] (torneios n=2.249): a reversão PIORA o Brier em TODOS os half-lives
testados (24–144 meses: ΔBrier −0,006..−0,023, IC95 inteiro < 0). Conclusão: a inflação
ABSOLUTA do Elo é COSMÉTICA (afeta o display vs eloratings, não o `dr` RELATIVO que prevê);
reverter joga fora sinal real. Mantido OFF (default half_life=0). Fica como ferramenta de
re-teste (ex.: outra média-alvo, ponderação por recência diferente, dados novos).

Uso:
    python -m scm.calibrate_recency --db dados/scm.sqlite --half-lives 24 48 96
"""
from __future__ import annotations

import argparse
import math
from datetime import date
from pathlib import Path

from . import db
from .ingest import DEFAULT_DB
from .elo_engine import we, k_factor, g_factor, sigma_r, _revert, EloParams
from .predictor import PredictParams, lambdas, poisson_reads, ved_from_elo, elo_direct_read, _clamp_norm
from .features_pit import vol_mult, FeatureParams
from .backtest_harness import brier, outcome_of, gate, MAJOR


def _pass(conn, ep: EloParams) -> dict:
    """Passe cronológico do Elo (com/sem reversão). {match_id: (dr, we_home, n_h, n_a)} PRÉ-jogo."""
    rows = conn.execute(
        """SELECT match_id, date, home_team_id h, away_team_id a, home_score hs, away_score s,
                  tournament t, neutral FROM matches WHERE home_score IS NOT NULL
           ORDER BY date, match_id"""
    ).fetchall()
    rat, ng, last, info = {}, {}, {}, {}
    for r in rows:
        h, a = r["h"], r["a"]
        rh = rat.get(h, ep.init); ra = rat.get(a, ep.init)
        if ep.revert_half_life_months > 0:
            rh = _revert(rh, last.get(h), r["date"], ep)
            ra = _revert(ra, last.get(a), r["date"], ep)
        nh = ng.get(h, 0); na = ng.get(a, 0)
        mando = 0.0 if r["neutral"] else ep.h_hist
        dr = rh - ra + mando; wh = we(dr)
        info[r["match_id"]] = (dr, wh, nh, na)
        gd = r["hs"] - r["s"]; w = 1.0 if gd > 0 else (0.5 if gd == 0 else 0.0)
        d = k_factor(r["t"]) * g_factor(gd) * (w - wh)
        rat[h] = rh + d; rat[a] = ra - d; ng[h] = nh + 1; ng[a] = na + 1
        last[h] = r["date"]; last[a] = r["date"]
    return info


def _form(conn, team_id, before, info, fp: FeatureParams):
    rows = conn.execute(
        """SELECT match_id, date, tournament, home_team_id, away_team_id, home_score, away_score
           FROM matches WHERE (home_team_id=? OR away_team_id=?) AND date<? AND home_score IS NOT NULL
           ORDER BY date DESC LIMIT ?""", (team_id, team_id, before, fp.form_window)).fetchall()
    if not rows:
        return 0.0, 0.0, 0
    res, wts = [], []
    for r in rows:
        gd = r["home_score"] - r["away_score"]; wh = info.get(r["match_id"], (0, 0.5, 0, 0))[1]
        if r["home_team_id"] == team_id:
            act = 1.0 if gd > 0 else (0.5 if gd == 0 else 0.0); exp = wh
        else:
            act = 1.0 if gd < 0 else (0.5 if gd == 0 else 0.0); exp = 1 - wh
        mo = max(0.0, (date.fromisoformat(before) - date.fromisoformat(r["date"])).days / 30.44)
        w = (fp.recency_base ** mo) * (fp.friendly_weight if "friendly" in (r["tournament"] or "").lower() else 1.0)
        res.append(act - exp); wts.append(w)
    sw = sum(wts)
    if sw < 1e-9:
        return 0.0, 0.0, len(rows)
    wm = sum(x * w for x, w in zip(res, wts)) / sw
    var = sum(w * (x - wm) ** 2 for x, w in zip(res, wts)) / sw
    return max(-fp.form_cap, min(fp.form_cap, fp.form_scale * wm)), math.sqrt(var), len(rows)


def _briers(conn, info, fp, pp) -> dict:
    ph = ",".join("?" * len(MAJOR))
    mg = conn.execute(
        f"""SELECT match_id, date, home_team_id h, away_team_id a, home_score hs, away_score s
            FROM matches WHERE tournament IN ({ph}) AND home_score IS NOT NULL ORDER BY date""",
        list(MAJOR)).fetchall()
    out = {}
    ep = EloParams()
    for r in mg:
        fh, dh, nfh = _form(conn, r["h"], r["date"], info, fp)
        fa, da, nfa = _form(conn, r["a"], r["date"], info, fp)
        dr0, _, nh, na = info[r["match_id"]]; dr = dr0 + fh - fa
        srh = sigma_r(nh, ep) * vol_mult(dh, nfh); sra = sigma_r(na, ep) * vol_mult(da, nfa)
        sdr = math.sqrt(srh ** 2 + sra ** 2 + (fp.sigma_ajuste_c * dh) ** 2 + (fp.sigma_ajuste_c * da) ** 2)
        pr = poisson_reads(*lambdas(dr, pp))
        cp = _clamp_norm((pr["pv"], pr["pe"], pr["pd"]), pp.clamp_lo, pp.clamp_hi)
        el = elo_direct_read(dr, sdr, pp)
        ce = _clamp_norm((el["pv"], el["pe"], el["pd"]), pp.clamp_lo, pp.clamp_hi)
        ws = pp.w_poisson + pp.w_elo
        ens = _clamp_norm([(pp.w_poisson * cp[i] + pp.w_elo * ce[i]) / ws for i in range(3)],
                          pp.clamp_lo, pp.clamp_hi)
        out[r["match_id"]] = brier({"p_v": ens[0], "p_e": ens[1], "p_d": ens[2]}, outcome_of(r["hs"], r["s"]))
    return out


def run_gate(conn, half_lives=(24, 48, 96), B: int = 10000, seed: int = 12345) -> list:
    fp = FeatureParams(); pp = PredictParams()
    base = _briers(conn, _pass(conn, EloParams()), fp, pp)
    res = []
    for hl in half_lives:
        cand = _briers(conn, _pass(conn, EloParams(revert_half_life_months=hl)), fp, pp)
        ids = [k for k in base if k in cand]
        d = [base[k] - cand[k] for k in ids]   # >0 = reversão melhora
        g = gate(d, B=B, seed=seed)
        res.append({"half_life": hl, "n": len(ids),
                    "brier_base": sum(base[k] for k in ids) / len(ids),
                    "brier_rev": sum(cand[k] for k in ids) / len(ids), **g})
    return res


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Reversão à média no Elo (candidato P-M): portão.")
    ap.add_argument("--db", default=str(DEFAULT_DB))
    ap.add_argument("--half-lives", type=float, nargs="+", default=[24, 48, 96], dest="half_lives")
    args = ap.parse_args(argv)
    if not Path(args.db).exists():
        print(f"[erro] {args.db} não existe. Rode ingest + elo_engine antes."); return 1
    conn = db.connect(args.db)
    res = run_gate(conn, tuple(args.half_lives))
    conn.close()
    print(f"\n  REVERSÃO À MÉDIA no Elo (candidato P-M) — torneios n={res[0]['n']}")
    print(f"  Brier base (sem reversão) = {res[0]['brier_base']:.4f}")
    for g in res:
        print(f"  half_life={g['half_life']:>5.0f}m: Brier {g['brier_rev']:.4f}  "
              f"ΔBrier(rev−base, >0=melhora) {g['mean']:+.5f} IC95[{g['ic_lo']:+.5f},{g['ic_hi']:+.5f}] "
              f"-> {'ADOTA' if g['keep'] else 'NÃO (mantém OFF)'}")
    print("  Conclusão: reversão PIORA o Brier (inflação do Elo é cosmética, não preditiva).\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
