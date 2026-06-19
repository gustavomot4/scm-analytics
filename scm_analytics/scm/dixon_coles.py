"""dixon_coles — candidato (D-39): correção τ(ρ) de Dixon-Coles p/ placares baixos.

**TESTADO e REJEITADO pelo portão** (audit 06-19, P-A) — fica como ferramenta de
re-checagem, igual a `heat.py`/`estilo.py`. NÃO entra no modelo padrão (default ρ=0).

A Poisson do `predictor` assume gols independentes; a DC reforça 0×0/1×1 e corta 0×1/1×0
(ρ<0), corrigindo a correlação negativa real dos placares. Só toca 4 células → cálculo
fechado O(1) (sem varrer a matriz).

Disciplina (D-05): fit de ρ por **máxima verossimilhança** no TREINO (date<cutoff); adoção
só com **portão** no TESTE (ΔBrier de BTTS + Δlogloss de placar exato, IC bootstrap).

Resultado no backtest local (martj42 49.423, treino<2015 / teste≥2015):
  ρ_MLE ≈ -0.06, **mas o portão REJEITA**: BTTS ΔBrier negativo (DC piora ~-0.0007, IC<0)
  e o ganho de placar exato não é significativo (IC cruza 0). O viés de BTTS é de **NÍVEL**
  (resolvido por T_base, D-25), não de correlação. Por isso DC não entra (default ρ=0).

Uso:
    python -m scm.dixon_coles --db dados/scm.sqlite            # fit ρ + portão (todos)
    python -m scm.dixon_coles --db dados/scm.sqlite --major    # recorte de torneios
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path

from . import db
from .ingest import DEFAULT_DB
from .predictor import PredictParams, lambdas
from .backtest_harness import outcome_of, brier, gate, _boot_ci, MAJOR

DEFAULT_CUTOFF = "2015-01-01"
RHO_GRID = [-0.16, -0.12, -0.10, -0.08, -0.06, -0.04, -0.02, 0.0, 0.02, 0.04]


def tau(x: int, y: int, la: float, lb: float, rho: float) -> float:
    """Correção local de Dixon-Coles (1 fora das 4 células de placar baixo)."""
    if x == 0 and y == 0:
        return 1.0 - la * lb * rho
    if x == 0 and y == 1:
        return 1.0 + la * rho
    if x == 1 and y == 0:
        return 1.0 + lb * rho
    if x == 1 and y == 1:
        return 1.0 - rho
    return 1.0


def _norm_const(la: float, lb: float, rho: float) -> float:
    a0 = math.exp(-la); a1 = la * a0; b0 = math.exp(-lb); b1 = lb * b0
    return 1.0 + rho * (-a0 * b0 * la * lb + a0 * b1 * la + a1 * b0 * lb - a1 * b1)


def dc_reads(la: float, lb: float, rho: float) -> dict:
    """P(V/E/D), BTTS pela Poisson com τ de DC (cálculo fechado, renormalizado)."""
    a0 = math.exp(-la); a1 = la * a0; b0 = math.exp(-lb); b1 = lb * b0
    pv0 = pe0 = pd0 = 0.0
    mg = 10
    pa = [math.exp(-la) * la ** i / math.factorial(i) for i in range(mg + 1)]
    pb = [math.exp(-lb) * lb ** j / math.factorial(j) for j in range(mg + 1)]
    for i in range(mg + 1):
        for j in range(mg + 1):
            p = pa[i] * pb[j]
            if i > j: pv0 += p
            elif i == j: pe0 += p
            else: pd0 += p
    T = _norm_const(la, lb, rho)
    pv = (pv0 + a1 * b0 * lb * rho) / T
    pd = (pd0 + a0 * b1 * la * rho) / T
    pe = (pe0 + (-a0 * b0 * la * lb - a1 * b1) * rho) / T
    btts = ((1 - a0) * (1 - b0) - a1 * b1 * rho) / T
    return {"pv": pv, "pe": pe, "pd": pd, "btts": btts}


def _pois(k, l):
    return math.exp(-l) * l ** k / math.factorial(k)


def _load(conn, only_major):
    q = ("SELECT mf.dr_adj dr, m.home_score hs, m.away_score s, m.date d, m.tournament t "
         "FROM match_features mf JOIN matches m USING(match_id) WHERE m.home_score IS NOT NULL")
    rows = conn.execute(q).fetchall()
    if only_major:
        rows = [r for r in rows if r["t"] in MAJOR]
    return rows


def fit_rho_mle(rows, p: PredictParams, grid=RHO_GRID) -> tuple:
    """ρ por máxima verossimilhança dos placares (capados em 10)."""
    pre = []
    for r in rows:
        la, lb = lambdas(r["dr"], p)
        pre.append((la, lb, min(r["hs"], 10), min(r["s"], 10)))
    best = None
    scores = {}
    for rho in grid:
        ll = 0.0
        for la, lb, x, y in pre:
            t = tau(x, y, la, lb, rho)
            t = t if t > 0 else 1e-9
            ll += math.log(_pois(x, la)) + math.log(_pois(y, lb)) + math.log(t) - math.log(_norm_const(la, lb, rho))
        scores[rho] = ll
        if best is None or ll > best[1]:
            best = (rho, ll)
    return best[0], scores


def run_gate(conn, cutoff=DEFAULT_CUTOFF, only_major=False, p: PredictParams = None) -> dict:
    p = p or PredictParams()
    rows = _load(conn, only_major)
    tr = [r for r in rows if r["d"] < cutoff]
    te = [r for r in rows if r["d"] >= cutoff]
    if len(tr) < 200 or len(te) < 100:
        return {"erro": "amostra insuficiente", "n_train": len(tr), "n_test": len(te)}
    rho, _ = fit_rho_mle(tr, p)
    d_btts, d_ll = [], []
    bp0 = bpd = 0.0
    for r in te:
        la, lb = lambdas(r["dr"], p)
        act = 1.0 if (r["hs"] > 0 and r["s"] > 0) else 0.0
        b0 = dc_reads(la, lb, 0.0)["btts"]; bd = dc_reads(la, lb, rho)["btts"]
        bp0 += b0; bpd += bd
        d_btts.append((b0 - act) ** 2 - (bd - act) ** 2)
        x, y = min(r["hs"], 10), min(r["s"], 10)
        p0 = _pois(x, la) * _pois(y, lb)
        pd_ = p0 * tau(x, y, la, lb, rho) / _norm_const(la, lb, rho)
        d_ll.append(-math.log(max(p0, 1e-12)) - (-math.log(max(pd_, 1e-12))))
    g = gate(d_btts)
    mll = sum(d_ll) / len(d_ll); lo, hi = _boot_ci(d_ll)
    act_rate = sum(1.0 for r in te if (r["hs"] > 0 and r["s"] > 0)) / len(te)
    return {"rho_mle": rho, "n_train": len(tr), "n_test": len(te),
            "btts_pred_base": bp0 / len(te), "btts_pred_dc": bpd / len(te), "btts_real": act_rate,
            "btts_dbrier": g["mean"], "btts_ic": (g["ic_lo"], g["ic_hi"]), "btts_keep": g["keep"],
            "score_dlogloss": mll, "score_ic": (lo, hi),
            "adota": bool(g["keep"])}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Dixon-Coles (candidato): fit ρ (MLE) + portão.")
    ap.add_argument("--db", default=str(DEFAULT_DB))
    ap.add_argument("--cutoff", default=DEFAULT_CUTOFF)
    ap.add_argument("--major", action="store_true", help="só torneios (WC/Euro/Copa América)")
    args = ap.parse_args(argv)
    if not Path(args.db).exists():
        print(f"[erro] {args.db} não existe. Rode o pipeline antes."); return 1
    conn = db.connect(args.db)
    r = run_gate(conn, args.cutoff, only_major=args.major)
    conn.close()
    if r.get("erro"):
        print("[!]", r["erro"], r); return 1
    print(f"\n  DIXON-COLES (candidato) — teste ≥ {args.cutoff}, n_teste={r['n_test']}")
    print(f"  ρ (MLE no treino) = {r['rho_mle']:+.3f}")
    print(f"  BTTS: base {r['btts_pred_base']*100:.1f}% → DC {r['btts_pred_dc']*100:.1f}%  (real {r['btts_real']*100:.1f}%)")
    print(f"  PORTÃO BTTS: ΔBrier {r['btts_dbrier']:+.5f} IC[{r['btts_ic'][0]:+.5f}, {r['btts_ic'][1]:+.5f}]")
    print(f"  placar exato: Δlogloss {r['score_dlogloss']:+.5f} IC[{r['score_ic'][0]:+.5f}, {r['score_ic'][1]:+.5f}]")
    print(f"  → {'ADOTAR ✓' if r['adota'] else 'NÃO adotar (IC cruza/abaixo de 0) — mantém ρ=0'}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
