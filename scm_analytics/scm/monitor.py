"""monitor — acompanhamento AO VIVO da Copa (Top 1 / operacional, SEM portão).

Instrumentação, não modelo: lê o registro pré-jogo IMUTÁVEL (`registro-auto.csv`, gravado pelo
`registrar`) + `odds_hist` e reporta, rolando a cada rodada:
  (a) Brier acumulado vs uniforme  → o modelo tem skill na Copa real?
  (b) Calibração: reliability/ECE por faixa de p_max (o 'top pick')  → está calibrado ou DERIVOU?
  (c) Skill vs mercado: Brier modelo/mercado/blend nos jogos com odds;
  (d) Edge vs mercado (sabor CLV): divergência média p_modelo−p_mercado na perna escolhida.
  (e) Calibração + DRIFT POR MERCADO (1X2 top-pick, Over 2.5, BTTS): previsto vs observado,
      Brier vs taxa-base e z-score binomial; só alarma com n suficiente (power-aware).

NÃO muda o modelo nem passa por portão (é medição — o ganho mais seguro durante o torneio: detecta
DRIFT antes que custe caro). Probabilidade, não certeza. R$0, roda local.

CLV verdadeiro (entrada vs FECHAMENTO) precisa de um snapshot da linha de fechamento: grave-a em
`odds_hist` com `source='close'` (via `scm.odds ingest`); aí o (d) compara modelo×fechamento.

Uso:  python -m scm.monitor --db dados/scm.sqlite [--reg dados/registro-auto.csv]
"""
from __future__ import annotations

import argparse
from pathlib import Path

from . import db
from .ingest import DEFAULT_DB
from .backtest_harness import brier, UNIFORM
from .registrar import DEFAULT_REG, _read          # reusa o leitor do registro imutável
from .odds import blend, market_read


def _settled(path):
    """Linhas do registro JÁ com resultado (previsão imutável + resultado preenchido)."""
    return [x for x in _read(path) if x.get("resultado")]


def calibration(path=DEFAULT_REG, n_bins=5):
    """Brier vs uniforme + reliability/ECE do top pick por faixa de p_max."""
    rows = _settled(path)
    if not rows:
        return {"n": 0}
    N = len(rows)
    bm = sum(float(x["brier"]) for x in rows) / N
    bu = sum(brier(UNIFORM, x["resultado"]) for x in rows) / N
    bins = [[0, 0, 0.0] for _ in range(n_bins)]   # [n, acertos_top_pick, soma_pmax]
    for x in rows:
        p = {"V": float(x["p_v"]), "E": float(x["p_e"]), "D": float(x["p_d"])}
        pick = max(p, key=p.get); pmax = p[pick]
        b = min(n_bins - 1, int(pmax * n_bins))
        bins[b][0] += 1
        bins[b][1] += 1 if pick == x["resultado"] else 0
        bins[b][2] += pmax
    rel = []; ece = 0.0
    for n, h, s in bins:
        if n == 0:
            continue
        pred = s / n; obs = h / n; ece += (n / N) * abs(pred - obs)
        rel.append({"pred": round(pred, 3), "obs": round(obs, 3), "n": n})
    return {"n": N, "brier_model": bm, "brier_uniform": bu,
            "edge_vs_uniform": bu - bm, "ece": ece, "reliability": rel}


def _f(x, k):
    """float seguro de um campo do registro (None se vazio/ausente)."""
    v = x.get(k, "")
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


# Mercados binários auditáveis a partir do registro imutável: (nome, p_previsto(row), desfecho 0/1).
# Tudo já está gravado pré-jogo (p_*) + o placar real (gols_*); nada recomputado, nada inventado.
def _mkt_toppick(x):
    p = {"V": _f(x, "p_v"), "E": _f(x, "p_e"), "D": _f(x, "p_d")}
    if None in p.values():
        return None
    pick = max(p, key=p.get)
    return p[pick], (1 if pick == x.get("resultado") else 0)


def _mkt_over25(x):
    p = _f(x, "p_over25"); gh = _f(x, "gols_home"); ga = _f(x, "gols_away")
    if p is None or gh is None or ga is None:
        return None
    return p, (1 if (gh + ga) > 2.5 else 0)


def _mkt_btts(x):
    p = _f(x, "p_btts"); gh = _f(x, "gols_home"); ga = _f(x, "gols_away")
    if p is None or gh is None or ga is None:
        return None
    return p, (1 if (gh > 0 and ga > 0) else 0)


_MARKETS = (("1X2 (top pick)", _mkt_toppick), ("Over 2.5", _mkt_over25), ("BTTS", _mkt_btts))


def reliability_by_market(path=DEFAULT_REG, z_alarm=2.0, n_min=10):
    """Calibração + drift POR MERCADO (1X2 top-pick, Over 2.5, BTTS) sobre o registro settled.

    Para cada mercado: n, prob média prevista vs frequência observada, Brier do modelo vs Brier
    da taxa-base (skill), e um sinal de DRIFT = z-score binomial do observado vs o previsto pelo
    próprio modelo (gap / sqrt(p̄(1−p̄)/n)). É POWER-AWARE: com n<n_min não alarma ('n baixo'),
    para não confundir ruído de amostra com deriva — mesma disciplina do portão (IC que decide).
    Não muda o modelo, não passa por portão. Drift real = |z|>z_alarm com n suficiente.
    """
    rows = _settled(path)
    out = []
    for name, fn in _MARKETS:
        data = [r for r in (fn(x) for x in rows) if r is not None]
        n = len(data)
        if n == 0:
            continue
        pbar = sum(p for p, _ in data) / n
        obar = sum(o for _, o in data) / n
        brier_m = sum((p - o) ** 2 for p, o in data) / n
        brier_base = obar * (1.0 - obar)                 # sempre prever a taxa-base
        se = (pbar * (1.0 - pbar) / n) ** 0.5
        z = (obar - pbar) / se if se > 0 else 0.0
        flag = "n baixo" if n < n_min else ("DRIFT" if abs(z) > z_alarm else "ok")
        out.append({"mercado": name, "n": n, "prev": pbar, "obs": obar,
                    "brier_model": brier_m, "brier_base": brier_base, "z": z, "flag": flag})
    return {"n": len(rows), "markets": out}


def vs_market(conn, path=DEFAULT_REG):
    """Brier modelo/mercado/blend + edge médio do modelo nos jogos com odds gravadas."""
    rows = _settled(path)
    bm = bk = bb = 0.0; n = 0; edge = 0.0
    for x in rows:
        mk = market_read(conn, x["home"], x["away"], x["data_jogo"])
        if not mk or not all(mk.get(k, 0) > 0 for k in ("p_v", "p_e", "p_d")):
            continue
        o = x["resultado"]
        model = {"p_v": float(x["p_v"]), "p_e": float(x["p_e"]), "p_d": float(x["p_d"])}
        bl = blend(model, mk)
        bm += brier(model, o); bk += brier(mk, o); bb += brier(bl, o)
        diffs = {k: model[k] - mk[k] for k in ("p_v", "p_e", "p_d")}
        pick = max(diffs, key=diffs.get); edge += diffs[pick]; n += 1
    if n == 0:
        return {"n": 0}
    return {"n": n, "brier_model": bm / n, "brier_market": bk / n,
            "brier_blend": bb / n, "edge_vs_market": edge / n}


def summary(conn, path=DEFAULT_REG):
    return {"calibration": calibration(path), "by_market": reliability_by_market(path),
            "market": vs_market(conn, path),
            "n_open": len([x for x in _read(path) if not x.get("resultado")])}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Monitor ao vivo: calibração + skill vs mercado (operacional).")
    ap.add_argument("--db", default=str(DEFAULT_DB))
    ap.add_argument("--reg", default=str(DEFAULT_REG))
    args = ap.parse_args(argv)
    c = calibration(args.reg)
    if not c.get("n"):
        print("sem jogos com resultado no registro (rode 'registrar settle-from-db' após as rodadas)."); return 1
    print(f"\n  MONITOR DA COPA — {c['n']} jogos com resultado")
    print(f"  Brier modelo {c['brier_model']:.4f}  (uniforme {c['brier_uniform']:.4f}; edge {c['edge_vs_uniform']:+.4f})")
    print(f"  ECE (calibração do top pick) = {c['ece']:.3f}   [quanto menor, melhor; alto = DRIFT]")
    print("  reliability (faixa de confiança → acerto observado):")
    for r in c["reliability"]:
        print(f"    previsto {r['pred']*100:4.0f}%  vs  observado {r['obs']*100:4.0f}%   (n={r['n']})")
    bm = reliability_by_market(args.reg)
    if bm["markets"]:
        print("\n  POR MERCADO (calibração ao vivo + drift):")
        print(f"    {'mercado':<16} {'n':>3}  {'prev':>5} {'obs':>5}  {'Brier':>6} {'(base)':>7}  {'z':>5}  flag")
        for r in bm["markets"]:
            print(f"    {r['mercado']:<16} {r['n']:>3}  {r['prev']*100:4.0f}% {r['obs']*100:4.0f}%  "
                  f"{r['brier_model']:.4f} {r['brier_base']:.4f}  {r['z']:+5.2f}  {r['flag']}")
        print("    [flag: 'ok' calibrado · 'DRIFT' |z|>2 com n suficiente · 'n baixo' = sem potência]")
    if Path(args.db).exists():
        m = vs_market(db.connect(args.db), args.reg)
        if m.get("n"):
            print(f"\n  vs MERCADO ({m['n']} jogos com odds):")
            print(f"    Brier modelo {m['brier_model']:.4f} | mercado {m['brier_market']:.4f} | blend {m['brier_blend']:.4f}")
            print(f"    edge médio do modelo na perna escolhida = {m['edge_vs_market']*100:+.1f} pp")
        else:
            print("\n  (sem odds gravadas — ingira com 'scm.odds ingest' p/ comparar com o mercado/CLV)")
    print(f"\n  ({c['n']} fechados; previsão imutável — drift = ECE subindo vs. o treino) ·  probabilidade, não certeza.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
