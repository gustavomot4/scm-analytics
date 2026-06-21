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


def build_from_statsbomb(repo_path, conn=None, out_csv=None, min_games=2, only_existing=True, min_year=2018) -> dict:
    """Constrói xG/seleção de um clone LOCAL do StatsBomb open-data (grátis; roda na SUA máquina).

        git clone --depth 1 https://github.com/statsbomb/open-data
        python -m scm.xg build /caminho/open-data            # ingere em team_xg
        python -m scm.xg build /caminho/open-data --csv dados/xg.csv   # também exporta o CSV

    Soma `shot.statsbomb_xg` por time (pró) e do adversário (contra) nas competições de SELEÇÕES
    masculinas; grava médias por jogo (team,xg_for,xg_against,n_games). only_existing=True mantém
    só seleções que já têm registro em `teams` (evita órfãos sem Elo).
    AVISO: o layout do StatsBomb pode variar entre versões — VALIDE o CSV gerado. Se falhar,
    monte o CSV manualmente (mesmo formato) e use `scm.xg ingest`.
    """
    import json
    base = Path(repo_path)
    comps = json.loads((base / "data" / "competitions.json").read_text(encoding="utf-8"))
    import re
    def _yr(s):
        m = re.search(r"(19|20)\d{2}", s or "")
        return int(m.group(0)) if m else 0
    YOUTH = ("u20", "u-20", "u23", "u-23", "u21", "u17", "u-17", "women", "olympic")
    # SÓ seleções MASCULINAS, INTERNACIONAIS, da era do xG (season >= min_year), sem base/feminino.
    # (intl=True descarta clubes; o filtro de ano descarta Copas antigas sem statsbomb_xg e o U20.)
    sel = set()
    for c in comps:
        nm = (c.get("competition_name") or "").lower()
        male = (c.get("competition_gender") or "male") == "male"
        intl = c.get("competition_international", None) is True
        youth = any(y in nm for y in YOUTH)
        if male and intl and not youth and _yr(c.get("season_name")) >= min_year:
            sel.add((c["competition_id"], c["season_id"]))
    fr, ag, ng = {}, {}, {}
    for cid, sid in sorted(sel):
        mp = base / "data" / "matches" / str(cid) / f"{sid}.json"
        if not mp.exists():
            continue
        for m in json.loads(mp.read_text(encoding="utf-8")):
            mid = m.get("match_id")
            ht = (m.get("home_team") or {}).get("home_team_name")
            at = (m.get("away_team") or {}).get("away_team_name")
            ev = base / "data" / "events" / f"{mid}.json"
            if not (ht and at and ev.exists()):
                continue
            try:
                events = json.loads(ev.read_text(encoding="utf-8"))
            except (ValueError, OSError):
                continue
            xg = {ht: 0.0, at: 0.0}
            for e in events:
                if (e.get("type") or {}).get("name") == "Shot":
                    tm = (e.get("team") or {}).get("name")
                    if tm in xg:
                        xg[tm] += ((e.get("shot") or {}).get("statsbomb_xg")) or 0.0
            for t, opp in ((ht, at), (at, ht)):
                fr[t] = fr.get(t, 0.0) + xg[t]; ag[t] = ag.get(t, 0.0) + xg[opp]; ng[t] = ng.get(t, 0) + 1
    keep_names = {r[0].lower() for r in conn.execute("SELECT name FROM teams")} if (conn and only_existing) else None
    rows = []
    for t in sorted(ng):
        if ng[t] < min_games:
            continue
        if keep_names is not None and t.lower() not in keep_names:
            continue
        rows.append((t, fr[t] / ng[t], ag[t] / ng[t], ng[t]))
    if out_csv:
        with open(out_csv, "w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh); w.writerow(["team", "xg_for", "xg_against", "n_games"])
            for t, xf, xa, n in rows:
                w.writerow([t, round(xf, 3), round(xa, 3), n])
    if conn:
        for t, xf, xa, n in rows:
            tid = db.get_or_create_team(conn, t)
            conn.execute("INSERT INTO team_xg (team_id,xg_for,xg_against,n_games,source) VALUES (?,?,?,?,?) "
                         "ON CONFLICT(team_id) DO UPDATE SET xg_for=excluded.xg_for, "
                         "xg_against=excluded.xg_against, n_games=excluded.n_games, source=excluded.source",
                         (tid, xf, xa, n, "statsbomb"))
        conn.commit()
    return {"competicoes": len(sel), "selecoes": len(rows)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="xG por seleção (esqueleto): ingestão + leitura do fator.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    pi = sub.add_parser("ingest", help="carrega xG de um CSV (team,xg_for,xg_against,n_games)")
    pi.add_argument("csv"); pi.add_argument("--db", default=str(DEFAULT_DB))
    pb = sub.add_parser("build", help="constrói xG de um clone do StatsBomb open-data (roda local)")
    pb.add_argument("repo", help="caminho do clone statsbomb/open-data")
    pb.add_argument("--db", default=str(DEFAULT_DB)); pb.add_argument("--csv", default=None, help="também exporta CSV")
    pb.add_argument("--all-teams", dest="all_teams", action="store_true", help="inclui seleções sem Elo (default: só as do banco)")
    pb.add_argument("--min-year", dest="min_year", type=int, default=2018, help="só competições com season >= ano (era do xG)")
    pf = sub.add_parser("factor", help="mostra o fator de estilo por xG de uma seleção")
    pf.add_argument("team"); pf.add_argument("--db", default=str(DEFAULT_DB))
    args = ap.parse_args(argv)
    conn = db.connect(args.db)
    if args.cmd == "ingest":
        r = load_csv(args.csv, conn); conn.close()
        print(f"xG ingerido: {r['ingeridos']} seleções (ignoradas {r['ignorados']}) -> {args.db}")
        return 0
    if args.cmd == "build":
        r = build_from_statsbomb(args.repo, conn=conn, out_csv=args.csv, only_existing=not args.all_teams, min_year=args.min_year); conn.close()
        print(f"xG construído: {r['selecoes']} seleções de {r['competicoes']} competições -> team_xg"
              + (f" + {args.csv}" if args.csv else "") + "  [valide o CSV; schema do StatsBomb pode variar]")
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
