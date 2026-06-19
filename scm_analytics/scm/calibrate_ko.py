"""calibrate_ko — calibra o ε do mata-mata (contrato §3.2) com dados de pênaltis.

A disputa de pênaltis é ~moeda; o ε mede a leve vantagem do mais forte:
    P(mais forte avança no desempate) = 0.5 + ε.
Aqui medimos isso EMPIRICAMENTE: para cada disputa de pênaltis do `shootouts.csv`
(martj42), achamos o `dr` PRÉ-JOGO (de match_ratings) e vemos se quem venceu a disputa
era o de maior Elo. ε_hat = P(mais forte vence) − 0.5.

A literatura sugere ε pequeno (pênalti ~moeda: Kocher 53:47; Vollmer ~sem efeito) — então
esperamos ε_hat baixo. Rode na sua máquina (precisa baixar o shootouts.csv):
    python -m scm.calibrate_ko --download
    python -m scm.calibrate_ko --shootouts dados/shootouts.csv
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

from . import db
from .ingest import DEFAULT_DB

SHOOTOUTS_URL = "https://raw.githubusercontent.com/martj42/international_results/master/shootouts.csv"
DEFAULT_SHOOTOUTS = Path(__file__).resolve().parent.parent / "dados" / "shootouts.csv"
MAJOR = ("FIFA World Cup", "UEFA Euro", "Copa América", "Copa America")


def download(url=SHOOTOUTS_URL, dest=DEFAULT_SHOOTOUTS) -> Path:
    import requests
    dest = Path(dest); dest.parent.mkdir(parents=True, exist_ok=True)
    r = requests.get(url, timeout=60); r.raise_for_status()
    dest.write_bytes(r.content)
    return dest


def _dr_of(conn, date, home, away):
    row = conn.execute(
        """SELECT mr.dr, m.tournament FROM matches m JOIN match_ratings mr USING (match_id)
           JOIN teams th ON th.team_id=m.home_team_id JOIN teams ta ON ta.team_id=m.away_team_id
           WHERE m.date=? AND th.name=? AND ta.name=?""", (date, home, away)).fetchone()
    return (row["dr"], row["tournament"]) if row else (None, None)


def calibrate(conn, shootouts_csv, only_major=False) -> dict:
    n = won = skipped = 0
    by_bucket = {}      # |dr| bucket -> [n, stronger_won]
    with Path(shootouts_csv).open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            dr, tour = _dr_of(conn, r.get("date", ""), r.get("home_team", ""), r.get("away_team", ""))
            if dr is None or abs(dr) < 1e-9:
                skipped += 1; continue
            if only_major and tour not in MAJOR:
                continue
            stronger = r["home_team"] if dr > 0 else r["away_team"]
            hit = 1 if r.get("winner", "") == stronger else 0
            n += 1; won += hit
            b = min(int(abs(dr) // 100), 4)
            by_bucket.setdefault(b, [0, 0]); by_bucket[b][0] += 1; by_bucket[b][1] += hit
    if n == 0:
        return {"n": 0, "skipped": skipped}
    rate = won / n
    return {"n": n, "skipped": skipped, "stronger_win_rate": rate, "eps_hat": rate - 0.5,
            "by_bucket": {f"{b*100}-{b*100+100}": [v[0], round(v[1]/v[0], 3)] for b, v in sorted(by_bucket.items())}}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Calibra o ε do mata-mata com shootouts.csv (martj42).")
    ap.add_argument("--db", default=str(DEFAULT_DB))
    ap.add_argument("--shootouts", default=str(DEFAULT_SHOOTOUTS))
    ap.add_argument("--download", action="store_true", help="baixa o shootouts.csv (requer rede; sua máquina)")
    ap.add_argument("--major", action="store_true", help="só torneios (WC/Euro/Copa América)")
    args = ap.parse_args(argv)
    if args.download:
        print("baixando shootouts.csv ->", download(dest=args.shootouts))
    if not Path(args.db).exists():
        print(f"[erro] {args.db} não existe. Rode ingest + elo_engine antes."); return 1
    if not Path(args.shootouts).exists():
        print(f"[erro] {args.shootouts} não existe. Rode com --download (na sua máquina)."); return 1
    conn = db.connect(args.db)
    r = calibrate(conn, args.shootouts, only_major=args.major)
    conn.close()
    if not r.get("n"):
        print("sem disputas casáveis com a base."); return 1
    print(f"\n  CALIBRAÇÃO DO ε (mata-mata) — n={r['n']} disputas de pênaltis (puladas {r['skipped']})")
    print(f"  o time mais forte (maior Elo) venceu a disputa em {r['stronger_win_rate']*100:.1f}% das vezes")
    print(f"  ε_hat = {r['eps_hat']:+.3f}   (contrato usa 0,03; pênalti ~moeda -> ε pequeno é esperado)")
    print(f"  por faixa de |dr| (n, taxa do + forte): {r['by_bucket']}")
    print(f"  → para adotar: PredictParams(eps_ko={max(0.0, r['eps_hat']):.3f}) [revisar com IC se n for pequeno]\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
