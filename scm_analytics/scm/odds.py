"""odds — esqueleto de ingestão de mercado (P-H / D-44): a 3ª perna do ensemble.

Hoje o ensemble combina Poisson + Elo, que saem do MESMO `dr` (diversidade fictícia no
histórico — audit §3.6). O mercado é o único sinal **independente**; o contrato (§3.8)
reserva peso **0,20** para ele quando existir. Não há odds históricas gratuitas (lacuna
declarada em [[Fontes gratuitas]]) → captura é **manual** (Kalshi/Polymarket/casas), por
isso este módulo é o ENCAIXE: schema (`odds_hist`), conversão de-vig, e o blend na porta
da frente. Sem odds, tudo se comporta como antes.

Conversões:
  implícita_i = (1/odd_i) / Σ(1/odd_j)        # remove o overround (vig)
  final = (1−w)·modelo + w·mercado            # w=0.20; renormaliza

Probabilidade, não certeza; mercado é benchmark, não verdade (D-08).
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

from . import db
from .ingest import DEFAULT_DB

W_MARKET = 0.20         # peso do mercado no ensemble (contrato §3.8 / D-08)


def implied_probs(odd_home: float, odd_draw: float, odd_away: float) -> dict:
    """Odds decimais -> probabilidades de-vigged (somam 1). Erro se alguma odd <= 1."""
    inv = [1.0 / o for o in (odd_home, odd_draw, odd_away) if o and o > 1.0]
    if len(inv) != 3:
        raise ValueError("odds decimais inválidas (todas devem ser > 1.0)")
    s = sum(inv)
    return {"p_v": inv[0] / s, "p_e": inv[1] / s, "p_d": inv[2] / s}


def blend(model: dict, market: dict, w: float = W_MARKET) -> dict:
    """Mistura 1X2 do modelo com o mercado (peso w) e renormaliza."""
    mix = {k: (1.0 - w) * model[k] + w * market[k] for k in ("p_v", "p_e", "p_d")}
    s = sum(mix.values()) or 1.0
    return {k: v / s for k, v in mix.items()}


def store(conn, home, away, date, market: dict, source="manual") -> None:
    nk = f"{date}|{home}|{away}"
    mid = conn.execute("SELECT match_id FROM matches WHERE natural_key LIKE ?",
                       (nk + "%",)).fetchone()
    conn.execute(
        """INSERT INTO odds_hist (natural_key, match_id, p_home, p_draw, p_away, source, asof)
           VALUES (?,?,?,?,?,?,?)
           ON CONFLICT(natural_key, source) DO UPDATE SET
             p_home=excluded.p_home, p_draw=excluded.p_draw, p_away=excluded.p_away, asof=excluded.asof""",
        (nk, mid["match_id"] if mid else None, market["p_v"], market["p_e"], market["p_d"], source, date),
    )
    conn.commit()


def market_read(conn, home, away, date, source=None) -> dict | None:
    """Lê o mercado (de-vigged) gravado p/ o confronto, ou None."""
    nk = f"{date}|{home}|{away}"
    q = "SELECT p_home, p_draw, p_away FROM odds_hist WHERE natural_key = ?"
    args = [nk]
    if source:
        q += " AND source = ?"; args.append(source)
    row = conn.execute(q, args).fetchone()
    if not row:
        return None
    return {"p_v": row["p_home"], "p_e": row["p_draw"], "p_d": row["p_away"]}


def load_csv(path, conn) -> dict:
    """Ingxere odds de um CSV (date,home,away,odd_home,odd_draw,odd_away[,source]). De-vig + store."""
    db.init_schema(conn)
    n = bad = 0
    with Path(path).open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            try:
                mk = implied_probs(float(r["odd_home"]), float(r["odd_draw"]), float(r["odd_away"]))
            except (ValueError, KeyError, TypeError):
                bad += 1
                continue
            store(conn, r["home"].strip(), r["away"].strip(), r["date"].strip(),
                  mk, (r.get("source") or "manual").strip())
            n += 1
    return {"ingeridos": n, "ignorados": bad}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Ingestão/consulta de odds de mercado (P-H).")
    sub = ap.add_subparsers(dest="cmd", required=True)
    pi = sub.add_parser("ingest", help="carrega odds de um CSV (de-vig + grava)")
    pi.add_argument("csv"); pi.add_argument("--db", default=str(DEFAULT_DB))
    ps = sub.add_parser("show", help="mostra o mercado de-vigged de um confronto")
    ps.add_argument("home"); ps.add_argument("away"); ps.add_argument("--date", required=True)
    ps.add_argument("--db", default=str(DEFAULT_DB))
    pc = sub.add_parser("conv", help="converte 3 odds decimais em prob de-vigged")
    pc.add_argument("odds", nargs=3, type=float, metavar=("HOME", "DRAW", "AWAY"))
    args = ap.parse_args(argv)
    if args.cmd == "conv":
        m = implied_probs(*args.odds)
        print(f"de-vig: casa {m['p_v']*100:.1f}% · empate {m['p_e']*100:.1f}% · fora {m['p_d']*100:.1f}%")
        return 0
    if args.cmd == "ingest":
        conn = db.connect(args.db); r = load_csv(args.csv, conn); conn.close()
        print(f"odds ingeridas: {r['ingeridos']} (ignoradas {r['ignorados']}) -> {args.db}")
        return 0
    if args.cmd == "show":
        conn = db.connect(args.db); m = market_read(conn, args.home, args.away, args.date); conn.close()
        if not m:
            print("sem odds cadastradas p/ este confronto."); return 1
        print(f"mercado {args.home} x {args.away} ({args.date}): "
              f"casa {m['p_v']*100:.1f}% · empate {m['p_e']*100:.1f}% · fora {m['p_d']*100:.1f}%")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
