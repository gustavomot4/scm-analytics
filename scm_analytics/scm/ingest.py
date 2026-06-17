"""Ingestão: martj42 international_results -> SQLite (idempotente).

Uso (na sua máquina):
    python -m scm.ingest --download                         # baixa snapshot p/ dados/results.csv (requer rede)
    python -m scm.ingest --csv dados/results.csv --db dados/scm.sqlite
    python -m scm.ingest                                    # carrega o snapshot padrão, se existir

Critério de aceite (BACKLOG / camada2-baseline-plano M1):
    contagens batem · sem nulos em chaves · idempotente.

NADA lê a internet no cálculo. O `--download` cria um SNAPSHOT em disco (1x);
todo o resto roda offline sobre o SQLite.
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import Optional, Union

from . import db

MARTJ42_URL = "https://raw.githubusercontent.com/martj42/international_results/master/results.csv"
_BASE = Path(__file__).resolve().parent.parent  # .../codigo
DEFAULT_CSV = _BASE / "dados" / "results.csv"
DEFAULT_DB = _BASE / "dados" / "scm.sqlite"


def download_snapshot(url: str = MARTJ42_URL, dest: Union[str, Path] = DEFAULT_CSV) -> Path:
    """Baixa o CSV do martj42 para um snapshot local. Roda na máquina do usuário.

    `requests` é importado aqui (lazy) de propósito: os testes não precisam de rede
    nem do pacote instalado.
    """
    import requests  # import tardio — só quando realmente se baixa

    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    dest.write_bytes(resp.content)
    return dest


def _parse_int(value: Optional[str]) -> Optional[int]:
    s = (value or "").strip()
    if s == "":
        return None
    try:
        return int(s)
    except ValueError:
        return None


def _parse_neutral(value: Optional[str]) -> int:
    return 1 if (value or "").strip().lower() == "true" else 0


def load_results(csv_path: Union[str, Path], conn) -> dict:
    """Carrega martj42 results.csv -> teams + matches. Idempotente via natural_key.

    Pula linhas sem placar (jogos não disputados / fixtures futuras). Devolve estatísticas.
    """
    csv_path = Path(csv_path)
    n_rows = n_inserted = n_skipped = 0
    with csv_path.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            n_rows += 1
            home_score = _parse_int(row.get("home_score"))
            away_score = _parse_int(row.get("away_score"))
            date = (row.get("date") or "").strip()
            home = (row.get("home_team") or "").strip()
            away = (row.get("away_team") or "").strip()
            # invariante: não inserir jogo sem chave/placar (evita nulos)
            if home_score is None or away_score is None or not date or not home or not away:
                n_skipped += 1
                continue
            tournament = (row.get("tournament") or "").strip()
            natural_key = f"{date}|{home}|{away}|{tournament}"
            home_id = db.get_or_create_team(conn, home)
            away_id = db.get_or_create_team(conn, away)
            cur = conn.execute(
                """INSERT OR IGNORE INTO matches
                   (date, home_team_id, away_team_id, home_score, away_score,
                    tournament, city, country, neutral, natural_key)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (
                    date, home_id, away_id, home_score, away_score, tournament,
                    (row.get("city") or "").strip() or None,
                    (row.get("country") or "").strip() or None,
                    _parse_neutral(row.get("neutral")), natural_key,
                ),
            )
            if cur.rowcount:
                n_inserted += 1
    conn.commit()
    return {"rows": n_rows, "inserted": n_inserted, "skipped": n_skipped}


def ingest(csv_path: Union[str, Path], db_path: Union[str, Path]) -> dict:
    conn = db.connect(db_path)
    db.init_schema(conn)
    stats = load_results(csv_path, conn)
    db.set_meta(conn, "source", "martj42/international_results")
    db.set_meta(conn, "snapshot_csv", str(csv_path))
    stats["total_matches"] = conn.execute("SELECT COUNT(*) FROM matches").fetchone()[0]
    stats["total_teams"] = conn.execute("SELECT COUNT(*) FROM teams").fetchone()[0]
    conn.close()
    return stats


def main(argv: Optional[list] = None) -> int:
    p = argparse.ArgumentParser(description="Ingestão martj42 -> SQLite (snapshot local).")
    p.add_argument("--download", action="store_true", help="baixa o snapshot do martj42 (requer rede)")
    p.add_argument("--csv", default=str(DEFAULT_CSV), help="caminho do results.csv (snapshot)")
    p.add_argument("--db", default=str(DEFAULT_DB), help="caminho do SQLite de saída")
    args = p.parse_args(argv)

    if args.download:
        dest = download_snapshot(dest=args.csv)
        print(f"snapshot salvo em {dest}")

    if not Path(args.csv).exists():
        print(
            f"[erro] snapshot não encontrado: {args.csv}\n"
            f"       rode `python -m scm.ingest --download` (na sua máquina) primeiro.",
            file=sys.stderr,
        )
        return 1

    stats = ingest(args.csv, args.db)
    print(
        f"ingerido: {stats['inserted']} novos | {stats['total_matches']} jogos | "
        f"{stats['total_teams']} seleções | pulados {stats['skipped']} | db={args.db}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
