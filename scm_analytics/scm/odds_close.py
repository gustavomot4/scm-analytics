"""odds_close — captura SEMI-AUTOMATIZADA da LINHA DE FECHAMENTO (CLV real), R$0.

NÃO é cálculo nem modelo — é instrumentação (como `ingest --download`): o modelo segue lendo
só snapshots. Lê os fixtures (`dados/fixtures.json`, com campo `kickoff` ISO opcional) + a
`odds_hist`; perto do kickoff AVISA os jogos que ainda não têm linha `source='close'`. Você cola
as 3 odds decimais de onde já olha; este módulo **de-viga** (reusa `scm.odds`) e grava
`source='close'`. Aí o `monitor` mede CLV real (modelo × fechamento).

Por que semi-auto e não 100%: não há feed de odds **grátis, programático e confiável** da Copa
(The Odds API cobra futebol; scraping é frágil/ToS). O que falha de verdade é humano — esquecer
ou perder a hora. Isto resolve isso a custo zero, mantendo o fechamento REAL (você vê a linha).

Fixtures: cada item aceita `kickoff` opcional em ISO-8601 COM fuso, ex.:
    {"home":"Spain","away":"Uruguay","date":"2026-06-26","kickoff":"2026-06-26T19:00:00-04:00"}
Sem `kickoff`, o lembrete cai para granularidade de DIA (avisa no dia do jogo).

Uso:
  python -m scm.odds_close due                                  # jogos prestes a começar sem 'close'
  python -m scm.odds_close set "Spain" "Uruguay" 1.85 3.60 4.20 # de-vig + grava (resolve a data)
  python -m scm.odds_close watch --lead 5 --poll 5              # loop: avisa no T-5min (rode num .bat)

Probabilidade, não certeza; mercado é benchmark, não verdade (D-08).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from . import db
from .ingest import DEFAULT_DB
from .odds import implied_probs, store, market_read

DEFAULT_FIXTURES = Path(__file__).resolve().parent.parent / "dados" / "fixtures.json"


def load_fixtures(path=DEFAULT_FIXTURES) -> list:
    p = Path(path)
    if not p.exists():
        return []
    return json.loads(p.read_text(encoding="utf-8"))


def parse_kickoff(fx: dict):
    """datetime AWARE do kickoff, ou None se só houver data (horário desconhecido)."""
    k = fx.get("kickoff") or fx.get("time")
    if not k:
        return None
    s = str(k).strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        try:                                   # tolera "YYYY-MM-DDTHH:MM±HH:MM" (sem segundos)
            dt = datetime.fromisoformat(s[:16] + ":00" + s[16:])
        except ValueError:
            return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def has_close(conn, fx: dict) -> bool:
    return market_read(conn, fx["home"], fx["away"], fx["date"], source="close") is not None


def due(conn, fixtures, within_min=15, now=None) -> list:
    """Jogos SEM linha 'close' que (a) começam dentro de `within_min`, ou (b) sem horário, são HOJE.

    Cada item: {home, away, date, minutes_to (int|None), time_known (bool)}. Jogos já começados
    há mais de `within_min` ficam de fora (a janela de fechamento passou).
    """
    now = now or datetime.now(timezone.utc)
    today = now.date()
    out = []
    for fx in fixtures:
        if has_close(conn, fx):
            continue
        ko = parse_kickoff(fx)
        if ko is not None:
            mins = (ko - now).total_seconds() / 60.0
            if -within_min <= mins <= within_min:        # janela [-w, +w] em torno do kickoff
                out.append({**fx, "minutes_to": int(round(mins)), "time_known": True})
        else:
            try:
                d = datetime.fromisoformat(fx["date"]).date()
            except (ValueError, KeyError):
                continue
            if d == today:
                out.append({**fx, "minutes_to": None, "time_known": False})
    out.sort(key=lambda f: (f["minutes_to"] is None, f["minutes_to"] if f["minutes_to"] is not None else 0))
    return out


def resolve_date(fixtures, home, away):
    """Data do confronto a partir dos fixtures (None se ambíguo/ausente)."""
    cands = [f["date"] for f in fixtures if f.get("home") == home and f.get("away") == away]
    return cands[0] if len(cands) == 1 else None


def set_close(conn, home, away, oh, od, oa, date=None, fixtures=None):
    """De-viga (oh,od,oa) e grava source='close'. Resolve a data pelos fixtures se não vier."""
    if date is None:
        date = resolve_date(fixtures or [], home, away)
        if date is None:
            raise ValueError("data não resolvida pelos fixtures — passe --date YYYY-MM-DD")
    mk = implied_probs(oh, od, oa)
    store(conn, home, away, date, mk, source="close")
    return {"home": home, "away": away, "date": date, **mk}


def notify(title: str, msg: str) -> None:
    """Console + bell (sempre) + popup nativo do Windows (não-bloqueante; sem dependências)."""
    print(f"\a\n  *** {title} ***\n  {msg}\n", flush=True)
    if sys.platform.startswith("win"):
        try:
            import ctypes
            import threading
            threading.Thread(
                target=lambda: ctypes.windll.user32.MessageBoxW(0, msg, title, 0x1000),  # SYSTEMMODAL
                daemon=True,
            ).start()
        except Exception:
            pass


def watch(db_path=DEFAULT_DB, fixtures_path=DEFAULT_FIXTURES, lead=5, poll=5, now_fn=None, once=False):
    """Loop: a cada `poll` min, avisa (uma vez cada) os jogos a ≤`lead` min do kickoff sem 'close'.

    Encerra quando não há mais fixtures futuros sem 'close'. Pensado p/ rodar num `.bat` no dia do
    jogo. `once=True` (testes) faz um único passe sem dormir; `now_fn` injeta o relógio.
    Retorna o nº de avisos emitidos (útil p/ teste).
    """
    now_fn = now_fn or (lambda: datetime.now(timezone.utc))
    seen = set()
    alerts = 0
    while True:
        conn = db.connect(str(db_path))
        fixtures = load_fixtures(fixtures_path)
        now = now_fn()
        for fx in due(conn, fixtures, within_min=lead, now=now):
            key = f"{fx['date']}|{fx['home']}|{fx['away']}"
            if key in seen:
                continue
            seen.add(key)
            alerts += 1
            when = (f"em ~{fx['minutes_to']} min" if fx["time_known"] else "hoje (horário não informado)")
            notify("Linha de fechamento — capture agora",
                   f"{fx['home']} x {fx['away']} começa {when}. "
                   f"Rode:  python -m scm.odds_close set \"{fx['home']}\" \"{fx['away']}\" CASA EMPATE FORA")
        pending = any(not has_close(conn, f) and _future_or_today(f, now) for f in fixtures)
        conn.close()
        if once or not pending:
            if not pending and not once:
                print("  (sem jogos futuros pendentes de 'close' — watcher encerrado)", flush=True)
            return alerts
        time.sleep(max(1, poll) * 60)


def _future_or_today(fx, now):
    ko = parse_kickoff(fx)
    if ko is not None:
        return ko >= now - _td(minutes=180)        # mantém até ~3h após o kickoff
    try:
        return datetime.fromisoformat(fx["date"]).date() >= now.date()
    except (ValueError, KeyError):
        return False


def _td(**kw):
    from datetime import timedelta
    return timedelta(**kw)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Captura semi-auto da linha de fechamento (CLV real, R$0).")
    sub = ap.add_subparsers(dest="cmd", required=True)
    pd = sub.add_parser("due", help="lista jogos prestes a começar sem linha 'close'")
    pd.add_argument("--db", default=str(DEFAULT_DB)); pd.add_argument("--fixtures", default=str(DEFAULT_FIXTURES))
    pd.add_argument("--within", type=int, default=15, help="janela em minutos (default 15)")
    pse = sub.add_parser("set", help="de-viga 3 odds e grava source='close'")
    pse.add_argument("home"); pse.add_argument("away")
    pse.add_argument("odds", nargs=3, type=float, metavar=("CASA", "EMPATE", "FORA"))
    pse.add_argument("--date", default=None); pse.add_argument("--db", default=str(DEFAULT_DB))
    pse.add_argument("--fixtures", default=str(DEFAULT_FIXTURES))
    pw = sub.add_parser("watch", help="loop: avisa no T-lead de cada jogo (rode num .bat)")
    pw.add_argument("--db", default=str(DEFAULT_DB)); pw.add_argument("--fixtures", default=str(DEFAULT_FIXTURES))
    pw.add_argument("--lead", type=int, default=5); pw.add_argument("--poll", type=int, default=5)
    args = ap.parse_args(argv)

    if args.cmd == "due":
        conn = db.connect(args.db); rows = due(conn, load_fixtures(args.fixtures), within_min=args.within); conn.close()
        if not rows:
            print("nenhum jogo na janela sem linha 'close'."); return 0
        print(f"\n  CAPTURAR FECHAMENTO ({len(rows)} jogo(s)):")
        for f in rows:
            when = (f"em ~{f['minutes_to']} min" if f["time_known"] else "hoje (sem horário)")
            print(f"    {f['home']} x {f['away']} ({f['date']}, {when})")
            print(f"      -> python -m scm.odds_close set \"{f['home']}\" \"{f['away']}\" CASA EMPATE FORA")
        return 0
    if args.cmd == "set":
        conn = db.connect(args.db)
        try:
            r = set_close(conn, args.home, args.away, *args.odds, date=args.date, fixtures=load_fixtures(args.fixtures))
        except ValueError as e:
            print(f"[erro] {e}"); conn.close(); return 1
        conn.close()
        print(f"  'close' gravado: {r['home']} x {r['away']} ({r['date']}) -> "
              f"casa {r['p_v']*100:.1f}% · empate {r['p_e']*100:.1f}% · fora {r['p_d']*100:.1f}%")
        return 0
    if args.cmd == "watch":
        print(f"  watcher ativo (lead {args.lead}min, poll {args.poll}min) — Ctrl+C p/ sair.", flush=True)
        watch(args.db, args.fixtures, lead=args.lead, poll=args.poll)
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
