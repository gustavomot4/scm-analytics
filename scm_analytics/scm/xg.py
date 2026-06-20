"""xg — ESQUELETO (D-50): xG por seleção (StatsBomb Open Data) como prior de estilo.

Por que: gols brutos são ruidosos; o **xG** é o melhor sinal de "estilo" (quanto um time
cria/concede). Pode virar a alavanca do BTTS/over (como o `estilo`, mas menos ruidosa) e,
adiante, um membro de **prior não-Elo** no ensemble — dando diversidade real.

**Status: esqueleto, OFF.** Não entra em λ sem passar pelo **portão** (igual estilo/calor).
Cobertura do StatsBomb é parcial (2018/2022/Euro/WWC) e o download roda na **sua máquina**
(não há fonte ao vivo das 48). Aqui ficam: ingestão de um CSV que você deriva do StatsBomb,
o armazenamento (`team_xg`) e a leitura do fator. Wire no `predict` + gate = trabalho futuro.

CSV esperado (uma linha por seleção): team,xg_for,xg_against,n_games
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

from . import db
from .ingest import DEFAULT_DB

SHRINK_K = 10.0          # jogos-equivalentes de prior em 1.0 (estabilidade) [a calibrar]
CAP_LO, CAP_HI = 0.7, 1.4


def load_csv(path, conn) -> dict:
    """Ingxere xG por seleção de um CSV (team,xg_for,xg_against,n_games). Idempotente por team."""
    db.init_schema(conn)
    n = skipped = 0
    with Path(path).open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            name = (row.get("team") or "").strip()
            try:
                xf = float(row["xg_for"]); xa = float(row["xg_against"]); ng = int(row.get("n_games") or 0)
            except (KeyError, ValueError, TypeError):
                skipped += 1
                continue
            if not name or ng <= 0:
                skipped += 1
                continue
            tid = db.get_or_create_team(conn, name)
            conn.execute(
                """INSERT INTO team_xg (team_id, xg_for, xg_against, n_games, source)
                   VALUES (?,?,?,?,?)
                   ON CONFLICT(team_id) DO UPDATE SET xg_for=excluded.xg_for,
                     xg_against=excluded.xg_against, n_games=excluded.n_games, source=excluded.source""",
                (tid, xf, xa, ng, (row.get("source") or "statsbomb").strip()))
            n += 1
    conn.commit()
    return {"ingeridos": n, "ignorados": skipped}


def _global_avg(conn):
    row = conn.execute("SELECT SUM(xg_for*n_games), SUM(n_games) FROM team_xg").fetchone()
    return (row[0] / row[1]) if row and row[1] else None


def xg_factor(conn, team) -> dict | None:
    """Fator de estilo por xG (encolhido a 1.0): ataque = xg_for/média, defesa = xg_against/média.

    Candidato a multiplicador de λ (como `estilo`) — NÃO use sem o portão. None se sem dados.
    """
    avg = _global_avg(conn)
    if not avg:
        return None
    row = conn.execute(
        "SELECT t.team_id, x.xg_for, x.xg_against, x.n_games FROM team_xg x "
        "JOIN teams t USING (team_id) WHERE lower(t.name)=lower(?)", (team,)).fetchone()
    if not row:
        return None
    n = row["n_games"]

    def shrink(obs):
        sh = (n * (obs / avg) + SHRINK_K * 1.0) / (n + SHRINK_K)
        return min(CAP_HI, max(CAP_LO, sh))
    return {"ataque": shrink(row["xg_for"]), "defesa": shrink(row["xg_against"]), "n": n}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="xG por seleção (esqueleto): ingestão + leitura do fator.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    pi = sub.add_parser("ingest", help="carrega xG de um CSV (team,xg_for,xg_against,n_games)")
    pi.add_argument("csv"); pi.add_argument("--db", default=str(DEFAULT_DB))
    pf = sub.add_parser("factor", help="mostra o fator de estilo por xG de uma seleção")
    pf.add_argument("team"); pf.add_argument("--db", default=str(DEFAULT_DB))
    args = ap.parse_args(argv)
    conn = db.connect(args.db)
    if args.cmd == "ingest":
        r = load_csv(args.csv, conn); conn.close()
        print(f"xG ingerido: {r['ingeridos']} seleções (ignoradas {r['ignorados']}) -> {args.db}")
        return 0
    if args.cmd == "factor":
        f = xg_factor(conn, args.team); conn.close()
        if not f:
            print("sem xG p/ essa seleção (rode `ingest` antes)."); return 1
        print(f"{args.team}: ataque {f['ataque']:.2f} · defesa {f['defesa']:.2f}  (n={f['n']})  "
              f"[candidato — não entra em λ sem portão]")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
