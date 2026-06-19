"""calibrate_1x2 — candidato (D-40): recalibração do 1X2 (temperatura + isotônica por classe).

**TESTADO e REJEITADO pelo portão** (audit 06-19, P-C) — fica como ferramenta de
re-checagem. NÃO altera o pipeline (o modelo já é bem calibrado, ECE ≈ 0,025).

Alvo do audit: superconfiança medida em favoritos [0,8–0,9] (prev 0,85 → obs 0,74).
Dois recalibradores, ambos com portão treino/teste (ΔBrier de 1X2, IC bootstrap):
  - **temperatura** T: p_i ∝ p_i^(1/T) (1 parâmetro; T>1 suaviza/reduz confiança);
  - **isotônica por classe** (PAV) + renormalização.

Resultado no backtest local (treino<2015 / teste≥2015):
  - temperatura: T ótimo no treino = 1,0 (identidade) → **nada a corrigir**;
  - isotônica: ΔBrier de teste **negativo** (piora; overfit de época) → **rejeitada**.
  Conclusão: o 1X2 já está calibrado; a oscilação em [0,8–0,9] é ruído de amostra (n pequeno).

Uso:
    python -m scm.calibrate_1x2 --db dados/scm.sqlite [--major]
"""
from __future__ import annotations

import argparse
from pathlib import Path

from . import db
from .ingest import DEFAULT_DB
from .predictor import MODEL_VERSION
from .backtest_harness import outcome_of, brier, gate, MAJOR

DEFAULT_CUTOFF = "2015-01-01"
TEMP_GRID = [1.0, 1.05, 1.1, 1.15, 1.2, 1.3, 1.4]


def temperature(p, T):
    q = [max(1e-9, x) ** (1.0 / T) for x in p]
    s = sum(q)
    return [x / s for x in q]


def _pav(xs, ys):
    """Pool-Adjacent-Violators (isotônica não-decrescente), expandida ao tamanho original."""
    blocks = [[y, 1, 1] for y in ys]
    i = 0
    while i < len(blocks) - 1:
        if blocks[i][0] > blocks[i + 1][0] + 1e-15:
            m = (blocks[i][0] * blocks[i][1] + blocks[i + 1][0] * blocks[i + 1][1]) / (blocks[i][1] + blocks[i + 1][1])
            blocks[i] = [m, blocks[i][1] + blocks[i + 1][1], blocks[i][2] + blocks[i + 1][2]]
            del blocks[i + 1]
            if i > 0: i -= 1
        else:
            i += 1
    xs_out, ys_out, idx = [], [], 0
    for m, w, cnt in blocks:
        xs_out.append(xs[idx]); ys_out.append(m); idx += cnt
    return xs_out, ys_out


def fit_isotonic(pairs):
    pairs = sorted(pairs)
    return _pav([p for p, _ in pairs], [h for _, h in pairs])


def apply_isotonic(cal, p):
    xs, ys = cal
    if not xs:
        return p
    if p <= xs[0]: return ys[0]
    if p >= xs[-1]: return ys[-1]
    lo, hi = 0, len(xs) - 1
    while lo + 1 < hi:
        mid = (lo + hi) // 2
        if xs[mid] <= p: lo = mid
        else: hi = mid
    if xs[hi] == xs[lo]: return ys[lo]
    t = (p - xs[lo]) / (xs[hi] - xs[lo])
    return ys[lo] + t * (ys[hi] - ys[lo])


def _load(conn, versao, only_major):
    q = ("SELECT p.p_v,p.p_e,p.p_d,m.home_score hs,m.away_score s,m.date d,m.tournament t "
         "FROM predictions p JOIN matches m USING(match_id) "
         "WHERE p.versao_modelo=? AND m.home_score IS NOT NULL")
    rows = conn.execute(q, (versao,)).fetchall()
    if only_major:
        rows = [r for r in rows if r["t"] in MAJOR]
    return rows


def run_gate(conn, versao=MODEL_VERSION, cutoff=DEFAULT_CUTOFF, only_major=False) -> dict:
    rows = _load(conn, versao, only_major)
    tr = [r for r in rows if r["d"] < cutoff]
    te = [r for r in rows if r["d"] >= cutoff]
    if len(tr) < 200 or len(te) < 100:
        return {"erro": "amostra insuficiente", "n_train": len(tr), "n_test": len(te)}

    # --- temperatura (1 parâmetro) ---
    def bri_temp(data, T):
        return sum(brier(dict(zip(("p_v", "p_e", "p_d"), temperature([r["p_v"], r["p_e"], r["p_d"]], T))),
                         outcome_of(r["hs"], r["s"])) for r in data) / len(data)
    T = min(TEMP_GRID, key=lambda t: bri_temp(tr, t))
    dT = []
    for r in te:
        o = outcome_of(r["hs"], r["s"]); base = {"p_v": r["p_v"], "p_e": r["p_e"], "p_d": r["p_d"]}
        q = temperature([r["p_v"], r["p_e"], r["p_d"]], T)
        dT.append(brier(base, o) - brier(dict(zip(("p_v", "p_e", "p_d"), q)), o))
    gT = gate(dT)

    # --- isotônica por classe ---
    calV = fit_isotonic([(r["p_v"], 1.0 if outcome_of(r["hs"], r["s"]) == "V" else 0.0) for r in tr])
    calE = fit_isotonic([(r["p_e"], 1.0 if outcome_of(r["hs"], r["s"]) == "E" else 0.0) for r in tr])
    calD = fit_isotonic([(r["p_d"], 1.0 if outcome_of(r["hs"], r["s"]) == "D" else 0.0) for r in tr])
    dI = []
    for r in te:
        o = outcome_of(r["hs"], r["s"]); base = {"p_v": r["p_v"], "p_e": r["p_e"], "p_d": r["p_d"]}
        v = apply_isotonic(calV, r["p_v"]); e = apply_isotonic(calE, r["p_e"]); dd = apply_isotonic(calD, r["p_d"])
        s = (v + e + dd) or 1.0
        dI.append(brier(base, o) - brier({"p_v": v / s, "p_e": e / s, "p_d": dd / s}, o))
    gI = gate(dI)
    return {"n_train": len(tr), "n_test": len(te), "best_T": T,
            "temp_dbrier": gT["mean"], "temp_ic": (gT["ic_lo"], gT["ic_hi"]), "temp_keep": gT["keep"],
            "iso_dbrier": gI["mean"], "iso_ic": (gI["ic_lo"], gI["ic_hi"]), "iso_keep": gI["keep"],
            "adota": bool(gT["keep"] or gI["keep"])}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Recalibração do 1X2 (candidato): temperatura + isotônica + portão.")
    ap.add_argument("--db", default=str(DEFAULT_DB))
    ap.add_argument("--versao", default=MODEL_VERSION)
    ap.add_argument("--cutoff", default=DEFAULT_CUTOFF)
    ap.add_argument("--major", action="store_true")
    args = ap.parse_args(argv)
    if not Path(args.db).exists():
        print(f"[erro] {args.db} não existe."); return 1
    conn = db.connect(args.db)
    r = run_gate(conn, args.versao, args.cutoff, only_major=args.major)
    conn.close()
    if r.get("erro"):
        print("[!]", r["erro"], r); return 1
    print(f"\n  RECALIBRAÇÃO 1X2 (candidato) — teste ≥ {args.cutoff}, n_teste={r['n_test']}")
    print(f"  temperatura T*={r['best_T']:.2f}: ΔBrier {r['temp_dbrier']:+.5f} IC[{r['temp_ic'][0]:+.5f},{r['temp_ic'][1]:+.5f}] "
          f"-> {'adota' if r['temp_keep'] else 'rejeita'}")
    print(f"  isotônica/classe:        ΔBrier {r['iso_dbrier']:+.5f} IC[{r['iso_ic'][0]:+.5f},{r['iso_ic'][1]:+.5f}] "
          f"-> {'adota' if r['iso_keep'] else 'rejeita'}")
    print(f"  → {'ADOTAR recalibração ✓' if r['adota'] else 'NÃO adotar — o 1X2 já está calibrado'}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
