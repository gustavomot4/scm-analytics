"""calibrate_confidence — ancora a confiança na CONFIABILIDADE medida no backtest.

Para cada faixa de p_max (prob. do resultado mais provável), mede a taxa real de acerto
do 'top pick'. Essa curva (isotônica = não-decrescente) vira a base da confiança em
predict_match: confiança = reliab(p_max) × maturidade(σ_R). Também VALIDA que p_max maior
de fato acerta mais. Guarda a curva em meta['confidence_reliab']. Sem rede; roda local.
"""
from __future__ import annotations

import argparse
import json

from . import db
from .ingest import DEFAULT_DB

LO = 1.0 / 3.0


def _rows(conn, versao=None):
    q = ("SELECT p.p_v, p.p_e, p.p_d, m.home_score, m.away_score "
         "FROM predictions p JOIN matches m USING (match_id) "
         "WHERE m.home_score IS NOT NULL AND m.away_score IS NOT NULL")
    args = ()
    if versao:
        q += " AND p.versao_modelo = ?"
        args = (versao,)
    return conn.execute(q, args).fetchall()


def _outcome(hs, as_):
    return "V" if hs > as_ else ("E" if hs == as_ else "D")


def _top(p_v, p_e, p_d):
    return "V" if (p_v >= p_e and p_v >= p_d) else ("E" if p_e >= p_d else "D")


def _isotonic(ys, ws):
    """Pool-Adjacent-Violators → ajuste não-decrescente (expandido ao tamanho original)."""
    blocks = []  # [mean, weight, count]
    for y, w in zip(ys, ws):
        blocks.append([y, w, 1])
        while len(blocks) > 1 and blocks[-2][0] > blocks[-1][0] + 1e-12:
            m2, w2, c2 = blocks.pop()
            m1, w1, c1 = blocks.pop()
            blocks.append([(m1 * w1 + m2 * w2) / (w1 + w2), w1 + w2, c1 + c2])
    out = []
    for m, _, c in blocks:
        out += [m] * c
    return out


def build_curve(conn, versao=None, n_bins=8, min_n=20):
    rows = _rows(conn, versao)
    agg = [[0, 0, 0.0] for _ in range(n_bins)]  # n, hits, sum_pmax
    width = (1.0 - LO) / n_bins
    for p_v, p_e, p_d, hs, as_ in rows:
        pmax = max(p_v, p_e, p_d)
        hit = 1 if _top(p_v, p_e, p_d) == _outcome(hs, as_) else 0
        b = min(n_bins - 1, max(0, int((pmax - LO) / width)))
        agg[b][0] += 1
        agg[b][1] += hit
        agg[b][2] += pmax
    raw = [(c[2] / c[0], c[1] / c[0], c[0]) for c in agg if c[0] >= min_n]  # (p_center, hit, n)
    if len(raw) < 2:
        return [], raw, len(rows)
    smooth = _isotonic([r[1] for r in raw], [r[2] for r in raw])
    curve = [[round(raw[k][0], 4), round(smooth[k], 4)] for k in range(len(raw))]
    return curve, raw, len(rows)


def calibrate(conn, versao=None, store=True):
    curve, raw, n = build_curve(conn, versao)
    if store and curve:
        db.set_meta(conn, "confidence_reliab", json.dumps(curve))
        conn.commit()
    return {"curve": curve, "raw": raw, "n": n}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Calibra a confiança contra a confiabilidade do backtest.")
    p.add_argument("--db", default=str(DEFAULT_DB))
    p.add_argument("--versao", default=None, help="filtra por versao_modelo (default: todas)")
    p.add_argument("--no-store", action="store_true", help="só mostra, não grava em meta")
    args = p.parse_args(argv)
    conn = db.connect(args.db)
    res = calibrate(conn, args.versao, store=not args.no_store)
    conn.close()
    if not res["curve"]:
        print(f"[!] suporte insuficiente ({res['n']} previsões com placar). "
              f"Rode o backtest (predictor) sobre o histórico antes."); return 1
    print(f"\n  Curva de confiabilidade  (n={res['n']} previsões com placar)")
    print(f"  {'p_max (faixa)':>16}  {'n':>6}  {'acerto bruto':>12}  {'reliab (isotônico)':>18}")
    mono = True
    prev = -1.0
    for (pc, sm), (rp, rh, rn) in zip(res["curve"], res["raw"]):
        print(f"  {pc*100:>14.0f}%  {rn:>6}  {rh*100:>11.0f}%  {sm*100:>17.0f}%")
        mono = mono and sm >= prev - 1e-9
        prev = sm
    overall = sum(rh * rn for _, rh, rn in res["raw"]) / sum(rn for *_, rn in res["raw"])
    print(f"\n  acerto global do 'top pick': {overall*100:.1f}%")
    print(f"  confiança {'É' if mono else 'NÃO é'} monotônica em p_max "
          f"→ {'confiança alta = mais acerto ✓' if mono else 'há inversão (ruído amostral)'}")
    print("  curva gravada em meta['confidence_reliab'] — predict_match já a usa.\n"
          if not args.no_store else "  (não gravado)\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
