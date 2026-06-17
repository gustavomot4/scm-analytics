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


def _scored(conn, versao: str) -> list:
    rows = conn.execute(
        """SELECT p.p_v, p.band_pv_lo, p.band_pv_hi, m.home_score, m.away_score
           FROM predictions p JOIN matches m USING (match_id)
           WHERE p.versao_modelo = ?""",
        (versao,),
    ).fetchall()
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


def summary(conn, versao: str) -> dict:
    items = _scored(conn, versao)
    return {
        "metrics": bh.evaluate(conn, versao) if items else {"n": 0},
        "reliability": reliability_bins(items),
        "calibration_error": calibration_error(items),
        "coverage": band_coverage(items),
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


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Relatório de calibração + cobertura de banda.")
    p.add_argument("--db", default=str(DEFAULT_DB))
    p.add_argument("--versao", default="baseline-v0.1")
    p.add_argument("--png", default=None, help="salva reliability diagram (requer matplotlib)")
    args = p.parse_args(argv)
    if not Path(args.db).exists():
        print(f"[erro] SQLite não encontrado: {args.db}. Rode o pipeline antes.")
        return 1
    conn = db.connect(args.db)
    s = summary(conn, args.versao)
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
    if args.png:
        print("png:", save_reliability_png(conn, args.versao, args.png))
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
