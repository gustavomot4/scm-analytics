"""report: calibração (reliability) + cobertura de banda + resumo (último módulo do baseline).

Lê `predictions` + resultados. Comunica SE o modelo é confiável (não só acurado):
- reliability diagram: P(mandante) prevista vs frequência observada, por faixa;
- ECE: erro de calibração esperado (média ponderada |prev − obs|);
- cobertura da banda: a freq observada cai dentro da banda de P(mandante)?
Plot opcional (matplotlib, import tardio). Métricas vêm do backtest_harness.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from . import db
from . import backtest_harness as bh
from .ingest import DEFAULT_DB
from .predictor import MODEL_VERSION as _MODEL


def _scored(conn, versao: str, only_major: bool = False) -> list:
    q = ("SELECT p.p_v, p.band_pv_lo, p.band_pv_hi, m.home_score, m.away_score "
         "FROM predictions p JOIN matches m USING (match_id) WHERE p.versao_modelo = ?")
    params = [versao]
    if only_major:
        q += " AND m.tournament IN (%s)" % ",".join("?" * len(bh.MAJOR))
        params += list(bh.MAJOR)
    rows = conn.execute(q, params).fetchall()
    return [
        {"p_v": r["p_v"], "lo": r["band_pv_lo"], "hi": r["band_pv_hi"],
         "home_won": 1 if r["home_score"] > r["away_score"] else 0}
        for r in rows
    ]


def reliability_bins(items: list, n_bins: int = 10) -> list:
    """Por faixa de P(mandante): média prevista, frequência observada de vitória, n."""
    buckets = [[] for _ in range(n_bins)]
    for it in items:
        idx = min(n_bins - 1, max(0, int(it["p_v"] * n_bins)))
        buckets[idx].append(it)
    out = []
    for b, grp in enumerate(buckets):
        if not grp:
            continue
        out.append({
            "bin": b,
            "pred_mean": sum(x["p_v"] for x in grp) / len(grp),
            "obs_freq": sum(x["home_won"] for x in grp) / len(grp),
            "n": len(grp),
        })
    return out


def calibration_error(items: list, n_bins: int = 10):
    """ECE: média ponderada de |prev − obs| sobre as faixas (0 = perfeitamente calibrado)."""
    bins = reliability_bins(items, n_bins)
    n = sum(b["n"] for b in bins)
    if n == 0:
        return None
    return sum(b["n"] * abs(b["pred_mean"] - b["obs_freq"]) for b in bins) / n


def band_coverage(items: list) -> dict:
    """Cobertura agregada: a freq observada de vitória do mandante cai na banda média de P(V)?"""
    n = len(items)
    if n == 0:
        return {"n": 0}
    obs = sum(x["home_won"] for x in items) / n
    lo = sum(x["lo"] for x in items) / n
    hi = sum(x["hi"] for x in items) / n
    return {
        "n": n, "obs_home_win": obs,
        "mean_pv": sum(x["p_v"] for x in items) / n,
        "mean_band_lo": lo, "mean_band_hi": hi,
        "mean_band_width": sum(x["hi"] - x["lo"] for x in items) / n,
        "obs_in_mean_band": lo <= obs <= hi,
    }


def band_coverage_binned(items: list, n_bins: int = 10) -> dict:
    """Cobertura de banda POR FAIXA de P(V) (substitui o agregado trivial).

    Em cada faixa de p_v: a frequência observada de vitória cai dentro da banda média
    da faixa? É o teste de cobertura nominal / calibração de σ_dr por estrato que o
    aceite pede (camada2-planejamento-v1 §5.4–5.5) — o agregado anterior quase sempre
    dava 'dentro' por construção. Reporta cobertura por faixa e ponderada por n.
    """
    buckets = [[] for _ in range(n_bins)]
    for it in items:
        idx = min(n_bins - 1, max(0, int(it["p_v"] * n_bins)))
        buckets[idx].append(it)
    rows, cov_n, tot_n = [], 0, 0
    for b, grp in enumerate(buckets):
        if not grp:
            continue
        n = len(grp)
        pred = sum(x["p_v"] for x in grp) / n
        obs = sum(x["home_won"] for x in grp) / n
        lo = sum(x["lo"] for x in grp) / n
        hi = sum(x["hi"] for x in grp) / n
        inb = lo <= obs <= hi
        rows.append({"bin": b, "n": n, "pred_mean": pred, "obs_freq": obs,
                     "lo": lo, "hi": hi, "in_band": inb})
        tot_n += n
        cov_n += n if inb else 0
    nb = len(rows)
    covered = sum(1 for r in rows if r["in_band"])
    return {"bins": rows, "n_bins": nb, "n_bins_covered": covered,
            "coverage_bins": covered / nb if nb else None,
            "coverage_weighted": cov_n / tot_n if tot_n else None,
            "mean_width": sum(r["hi"] - r["lo"] for r in rows) / nb if nb else None}


def summary(conn, versao: str, only_major: bool = False) -> dict:
    items = _scored(conn, versao, only_major=only_major)
    return {
        "metrics": bh.evaluate(conn, versao, only_major=only_major) if items else {"n": 0},
        "reliability": reliability_bins(items),
        "calibration_error": calibration_error(items),
        "coverage": band_coverage(items),
        "coverage_binned": band_coverage_binned(items),
    }


def save_reliability_png(conn, versao: str, path) -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    bins = reliability_bins(_scored(conn, versao))
    xs = [b["pred_mean"] for b in bins]
    ys = [b["obs_freq"] for b in bins]
    plt.figure(figsize=(5, 5))
    plt.plot([0, 1], [0, 1], "--", color="gray", label="perfeito")
    plt.scatter(xs, ys, label="modelo")
    plt.xlabel("P(mandante) prevista"); plt.ylabel("freq. observada")
    plt.title(f"Reliability — {versao}"); plt.legend()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(path, dpi=110, bbox_inches="tight"); plt.close()
    return str(path)


def btts_report(conn, versao: str, only_major: bool = False) -> dict:
    """Mede se o 'ambos marcam' está enviesado: BTTS médio PREVISTO vs taxa REAL."""
    from .backtest_harness import MAJOR
    q = ("SELECT p.p_btts, m.home_score hs, m.away_score s FROM predictions p "
         "JOIN matches m USING (match_id) "
         "WHERE p.versao_modelo=? AND m.home_score IS NOT NULL AND m.away_score IS NOT NULL")
    params = [versao]
    if only_major:
        q += " AND m.tournament IN (%s)" % ",".join("?" * len(MAJOR))
        params += list(MAJOR)
    rows = conn.execute(q, params).fetchall()
    if not rows:
        return {"n": 0}
    preds = [r["p_btts"] for r in rows]
    act = [1.0 if (r["hs"] > 0 and r["s"] > 0) else 0.0 for r in rows]
    n = len(preds)
    mean_pred = sum(preds) / n
    rate = sum(act) / n
    brier = sum((preds[i] - act[i]) ** 2 for i in range(n)) / n
    bins = [[0, 0.0, 0.0] for _ in range(10)]
    for pp, aa in zip(preds, act):
        b = min(9, int(pp * 10))
        bins[b][0] += 1
        bins[b][1] += pp
        bins[b][2] += aa
    rel = [{"pred": c[1] / c[0], "obs": c[2] / c[0], "n": c[0]} for c in bins if c[0] > 0]
    return {"n": n, "mean_pred": mean_pred, "actual_rate": rate,
            "bias": mean_pred - rate, "brier": brier, "reliability": rel}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Relatório de calibração + cobertura de banda.")
    p.add_argument("--db", default=str(DEFAULT_DB))
    p.add_argument("--versao", default=_MODEL)
    p.add_argument("--png", default=None, help="salva reliability diagram (requer matplotlib)")
    p.add_argument("--major", action="store_true", help="só torneios (WC/Euro/Copa América)")
    p.add_argument("--btts", action="store_true", help="diagnóstico do 'ambos marcam' (viés)")
    args = p.parse_args(argv)
    if not Path(args.db).exists():
        print(f"[erro] SQLite não encontrado: {args.db}. Rode o pipeline antes.")
        return 1
    conn = db.connect(args.db)
    if args.btts:
        r = btts_report(conn, args.versao, only_major=args.major)
        conn.close()
        if not r.get("n"):
            print(f"sem previsões p/ versão {args.versao}"); return 1
        print(f"\n  AMBOS MARCAM (BTTS) — versão {args.versao} | n={r['n']}")
        print(f"  previsto (média): {r['mean_pred']*100:.1f}%   |   real: {r['actual_rate']*100:.1f}%   "
              f"|   viés: {r['bias']*100:+.1f} pp   |   Brier {r['brier']:.4f}")
        verdict = ("ok — calibrado" if abs(r['bias']) < 0.02 else
                   ("ALTO demais (corrigir)" if r['bias'] > 0 else "baixo demais"))
        print(f"  veredito: {verdict}")
        print("  reliability (prev -> obs, n):")
        for b in r["reliability"]:
            print(f"    {b['pred']*100:4.0f}% -> {b['obs']*100:4.0f}%  (n={b['n']})")
        print()
        return 0
    s = summary(conn, args.versao, only_major=args.major)
    if s["metrics"].get("n", 0) == 0:
        print(f"sem previsões p/ versão {args.versao}")
        return 1
    m = s["metrics"]
    print(f"versão {args.versao} | n={m['n']} | Brier {m['brier']:.4f} | ECE {s['calibration_error']:.4f}")
    print("reliability (faixa: prev -> obs, n):")
    for b in s["reliability"]:
        print(f"  [{b['bin']/10:.1f}-{(b['bin']+1)/10:.1f}]  prev {b['pred_mean']:.2f} -> obs {b['obs_freq']:.2f}  (n={b['n']})")
    c = s["coverage"]
    print(f"banda: obs mandante {c['obs_home_win']:.3f} em [{c['mean_band_lo']:.3f}, {c['mean_band_hi']:.3f}] "
          f"-> {'DENTRO' if c['obs_in_mean_band'] else 'FORA'} (largura média {c['mean_band_width']:.3f})")
    cb = s["coverage_binned"]
    if cb["n_bins"]:
        print(f"cobertura por faixa de p_v: {cb['n_bins_covered']}/{cb['n_bins']} faixas dentro da banda "
              f"({cb['coverage_weighted']*100:.0f}% dos jogos) | largura média {cb['mean_width']:.3f}")
        for r in cb["bins"]:
            mark = "ok" if r["in_band"] else "FORA"
            print(f"  p_v[{r['bin']/10:.1f}-{(r['bin']+1)/10:.1f}] obs {r['obs_freq']:.2f} "
                  f"banda [{r['lo']:.2f},{r['hi']:.2f}] {mark} (n={r['n']})")
    if args.png:
        print("png:", save_reliability_png(conn, args.versao, args.png))
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
