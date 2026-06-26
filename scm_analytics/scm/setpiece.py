"""setpiece — cartões & escanteios (D-52): histórico por seleção (StatsBomb) + baseline.

PORTÃO (2026-06, leave-one-out, StatsBomb local, 314 jogos): o preditor POR SELEÇÃO
NÃO vence a média da competição — cartões sem sinal (melhor forma +0,3%), escanteios
+1,7% (dentro do ruído; amostras pequenas, muitos times com 3–7 jogos). Logo NÃO
publicamos "previsão por time". O que entregamos (honesto e calibrado):
  • Histórico DESCRITIVO por seleção (cartões/escanteios por jogo na amostra StatsBomb).
  • Over/under pela MÉDIA DA COMPETIÇÃO (Poisson em 2·μ) — calibrado (over 3,5 cartões ~48%,
    over 9,5 escanteios ~41%), mas NÃO ajustado por seleção. É baseline, não previsão por time.

Cartão = eventos 'Bad Behaviour'/'Foul Committed' com card; escanteio = passe tipo 'Corner'.
Cobertura PARCIAL (6 comps de seleção 2018-2024). A R$0, cartão/escanteio de SELEÇÃO só sai
do StatsBomb (football-data tem isso só de clubes). NADA lê a internet no cálculo (snapshot).
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
import unicodedata as _ud
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
DEFAULT_CSV = _BASE / "dados" / "setpiece.csv"

CARD_LINES = (2.5, 3.5, 4.5, 5.5)
CORNER_LINES = (7.5, 8.5, 9.5, 10.5, 11.5)

# Casamento de nomes StatsBomb (FIFA) -> martj42 (nomes do banco). Sem isto, seleções com
# grafia FIFA eram SILENCIOSAMENTE descartadas no build (db_names casava exato): no open-data
# atual caíam fora 'Cape Verde Islands', 'Congo DR', "Côte d'Ivoire" (audit B2, verificado).
# Cada destino foi conferido contra dados/scm.sqlite. Acrescente pares conforme a amostra crescer.
_SB_TO_MARTJ42 = {
    "cape verde islands": "Cape Verde", "congo dr": "DR Congo", "cote d'ivoire": "Ivory Coast",
    "korea republic": "South Korea", "korea dpr": "North Korea", "ir iran": "Iran",
    "china pr": "China", "czechia": "Czech Republic", "usa": "United States",
}


def _norm(s: str) -> str:
    """lower + sem acento (NFKD) — chave de casamento robusta a acentos/caixa."""
    s = _ud.normalize("NFKD", (s or "").strip().lower())
    return "".join(ch for ch in s if not _ud.combining(ch))


def _canon_team(name: str) -> str:
    """Nome StatsBomb -> nome martj42 do banco (alias direto; senão devolve o original)."""
    return _SB_TO_MARTJ42.get(_norm(name), name)


def build_from_statsbomb(repo_path, out_csv=DEFAULT_CSV, db_names=None, min_games=3, min_year=2018):
    """Taxas de cartões/escanteios por seleção de um clone LOCAL do StatsBomb (sem rede).
    db_names: set de nomes (lower) p/ manter só seleções do banco (evita órfãos sem Elo)."""
    base = Path(repo_path) / "data"
    comps = json.loads((base / "competitions.json").read_text(encoding="utf-8"))

    def yr(s):
        m = re.search(r"(19|20)\d{2}", s or "")
        return int(m.group(0)) if m else 0

    youth = ("u20", "u-20", "u23", "u-23", "u21", "u17", "u-17", "women", "olympic")
    sel = []
    for c in comps:
        nmc = (c.get("competition_name") or "").lower()
        if ((c.get("competition_gender") or "male") == "male" and c.get("competition_international", None) is True
                and not any(y in nmc for y in youth) and yr(c.get("season_name")) >= min_year):
            sel.append((c["competition_id"], c["season_id"]))
    cf = {}; ca = {}; kf = {}; ka = {}; ng = {}
    for cid, sid in sorted(sel):
        mp = base / "matches" / str(cid) / f"{sid}.json"
        if not mp.exists():
            continue
        for m in json.loads(mp.read_text(encoding="utf-8")):
            ht = (m.get("home_team") or {}).get("home_team_name")
            at = (m.get("away_team") or {}).get("away_team_name")
            ep = base / "events" / f"{m['match_id']}.json"
            if not (ht and at and ep.exists()):
                continue
            try:
                ev = json.loads(ep.read_text(encoding="utf-8"))
            except (ValueError, OSError):
                continue
            cards = {ht: 0, at: 0}; corners = {ht: 0, at: 0}
            for e in ev:
                tp = (e.get("type") or {}).get("name")
                tm = (e.get("team") or {}).get("name")
                if tm not in cards:
                    continue
                if tp == "Bad Behaviour" and (e.get("bad_behaviour") or {}).get("card"):
                    cards[tm] += 1
                elif tp == "Foul Committed" and (e.get("foul_committed") or {}).get("card"):
                    cards[tm] += 1
                elif tp == "Pass" and ((e.get("pass") or {}).get("type") or {}).get("name") == "Corner":
                    corners[tm] += 1
            for t, opp in ((ht, at), (at, ht)):
                cf[t] = cf.get(t, 0) + cards[t]; ca[t] = ca.get(t, 0) + cards[opp]
                kf[t] = kf.get(t, 0) + corners[t]; ka[t] = ka.get(t, 0) + corners[opp]
                ng[t] = ng.get(t, 0) + 1
    rows = []
    for t in sorted(ng):
        if ng[t] < min_games:
            continue
        canon = _canon_team(t)   # B2: nome StatsBomb -> martj42 (casa com o banco e com predict_match)
        if db_names is not None and canon.lower() not in db_names:
            continue
        n = ng[t]
        rows.append((canon, round(cf[t] / n, 3), round(ca[t] / n, 3), round(kf[t] / n, 3), round(ka[t] / n, 3), n))
    if out_csv:
        with open(out_csv, "w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["team", "cards_for", "cards_against", "corners_for", "corners_against", "n_games"])
            for r in rows:
                w.writerow(r)
    return {"selecoes": len(rows)}


def load_rates(csv_path=DEFAULT_CSV):
    p = Path(csv_path)
    if not p.exists():
        return None
    rates = {}; tot_c = tot_k = tot_n = 0.0
    with p.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            try:
                n = int(row["n_games"]); cf = float(row["cards_for"]); ca = float(row["cards_against"])
                kf = float(row["corners_for"]); ka = float(row["corners_against"])
            except (KeyError, ValueError, TypeError):
                continue
            nm = (row.get("team") or "").strip()
            if not nm or n <= 0:
                continue
            rates[nm.lower()] = {"name": nm, "cards_for": cf, "cards_against": ca,
                                 "corners_for": kf, "corners_against": ka, "n": n}
            tot_c += cf * n; tot_k += kf * n; tot_n += n
    if not rates:
        return None
    return {"rates": rates, "mu_cards": tot_c / tot_n, "mu_corners": tot_k / tot_n}


def _pois_over(lam, line):
    k = int(line)
    cdf = sum(math.exp(-lam) * lam ** i / math.factorial(i) for i in range(k + 1))
    return 1.0 - cdf


def match_setpiece(home, away, data):
    """Histórico descritivo das 2 seleções + over/under pela MÉDIA da competição (não por time).
       None se faltar dado de qualquer uma (cobertura parcial)."""
    if not data:
        return None
    R = data["rates"]
    h = R.get((home or "").lower()); a = R.get((away or "").lower())
    if not h or not a:
        return None
    lc = 2 * data["mu_cards"]; lk = 2 * data["mu_corners"]
    return {
        "home": {"cards": h["cards_for"], "corners": h["corners_for"], "n": h["n"]},
        "away": {"cards": a["cards_for"], "corners": a["corners_for"], "n": a["n"]},
        "media_jogo": {"cards": round(lc, 2), "corners": round(lk, 2)},
        "over_cards": {str(l): _pois_over(lc, l) for l in CARD_LINES},
        "over_corners": {str(l): _pois_over(lk, l) for l in CORNER_LINES},
        "baseline": True,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description="Cartões & escanteios: histórico StatsBomb + baseline.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build-sb", help="constrói as taxas do StatsBomb open-data LOCAL (sem rede)")
    b.add_argument("repo")
    b.add_argument("--out", default=str(DEFAULT_CSV))
    b.add_argument("--all-teams", dest="all_teams", action="store_true", help="inclui seleções sem Elo")
    s = sub.add_parser("show", help="mostra o histórico de uma seleção")
    s.add_argument("team")
    s.add_argument("--csv", default=str(DEFAULT_CSV))
    args = ap.parse_args(argv)
    if args.cmd == "build-sb":
        db_names = None
        if not args.all_teams:
            from . import db
            from .ingest import DEFAULT_DB
            conn = db.connect(str(DEFAULT_DB))
            db_names = {r[0].lower() for r in conn.execute("SELECT name FROM teams")}
            conn.close()
        r = build_from_statsbomb(args.repo, out_csv=args.out, db_names=db_names)
        print(f"setpiece: {r['selecoes']} seleções -> {args.out}  [cobertura parcial; baseline, não previsão]")
        return 0
    if args.cmd == "show":
        d = load_rates(args.csv)
        if not d:
            print("sem dados (rode build-sb).")
            return 1
        t = d["rates"].get(args.team.lower())
        if not t:
            print("seleção sem dados nessa amostra.")
            return 1
        print(f"{t['name']} (n={t['n']}): cartões {t['cards_for']}/jogo · escanteios {t['corners_for']}/jogo")
        print(f"média competição: {d['mu_cards']:.2f} cartões · {d['mu_corners']:.2f} escanteios por time/jogo")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
