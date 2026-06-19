"""simulate — Monte Carlo do torneio (Camada 5): P(campeão), P(final), P(semi), P(passar).

Lê o sorteio de `dados/copa2026.json` (12 grupos × 4 seleções) e usa o Elo atual
(`ratings_current`) + as λ do modelo (`predictor.lambdas`) para amostrar PLACAR de cada
jogo (Poisson). Mata-mata: empate resolvido pelo termo do contrato §3.2
(`predictor.knockout_advance`, ε≈0.03). Resultados já disputados na base (martj42) são
TRAVADOS (simulação de meio de torneio é coerente).

INSIGHT, não previsão validada por backtest — herda as limitações do modelo.
Probabilidades, nunca certezas. Tudo local, R$ 0.

Simplificações declaradas:
- Chaveamento por **sorteio aleatório** dos 32 a cada simulação (não modela a tabela
  posicional exata da FIFA p/ os 8 terceiros) → dá a probabilidade MÉDIA sobre chaveamentos.
- Empate de grupo: pontos → saldo → gols pró → moeda (head-to-head não modelado).
- Sede neutra por padrão; bônus de mando p/ anfitriões via `hosts` no JSON (opcional).

Uso:
    python -m scm.simulate --db dados/scm.sqlite --config dados/copa2026.json --sims 20000
"""
from __future__ import annotations

import argparse
import json
from itertools import combinations
from pathlib import Path

import numpy as np

from . import db
from .ingest import DEFAULT_DB
from .predictor import PredictParams, lambdas, MODEL_VERSION

DEFAULT_CONFIG = Path(__file__).resolve().parent.parent / "dados" / "copa2026.json"
ADVANCE_PER_GROUP = 2          # 2 melhores de cada grupo
BEST_THIRDS = 8                # + 8 melhores terceiros = 32 no mata-mata


def load_config(path) -> dict:
    cfg = json.loads(Path(path).read_text(encoding="utf-8"))
    groups = cfg.get("groups", {})
    return cfg, groups


def get_elos(conn) -> dict:
    return {r["name"]: r["elo"] for r in conn.execute(
        "SELECT t.name, r.elo FROM ratings_current r JOIN teams t USING (team_id)")}


def played_results(conn) -> dict:
    """{(home,away): (hs,as)} dos jogos de grupo da Copa 2026 já disputados (martj42)."""
    out = {}
    for r in conn.execute(
        """SELECT th.name h, ta.name a, m.home_score hs, m.away_score s
           FROM matches m JOIN teams th ON th.team_id=m.home_team_id
           JOIN teams ta ON ta.team_id=m.away_team_id
           WHERE m.tournament='FIFA World Cup' AND m.date>='2026-01-01'"""):
        out[(r["h"], r["a"])] = (r["hs"], r["s"])
    return out


def validate(groups: dict, elos: dict) -> list:
    """Lista de problemas (não impede rodar com sorteio sintético nos testes)."""
    probs = []
    teams = [t for g in groups.values() for t in g]
    if len(groups) != 12:
        probs.append(f"esperados 12 grupos, achei {len(groups)}")
    for g, ts in groups.items():
        if len(ts) != 4:
            probs.append(f"grupo {g}: {len(ts)} seleções (esperado 4)")
    miss = [t for t in teams if t not in elos and not str(t).startswith("TODO")]
    if miss:
        probs.append(f"sem Elo (nome != martj42?): {', '.join(sorted(set(miss))[:8])}")
    todo = [t for t in teams if str(t).startswith("TODO")]
    if todo:
        probs.append(f"{len(todo)} vagas TODO ainda não preenchidas no sorteio")
    return probs


def build_lambda_table(teams, elos, p, hosts=None) -> dict:
    """{(a,b): (dr, la, lb)} p/ todo par ordenado (com bônus de mando p/ anfitrião)."""
    hosts = hosts or {}
    tab = {}
    for a in teams:
        for b in teams:
            if a == b:
                continue
            mando = hosts.get(a, 0.0) - hosts.get(b, 0.0)
            dr = elos.get(a, 1500.0) - elos.get(b, 1500.0) + mando
            la, lb = lambdas(dr, p)
            tab[(a, b)] = (dr, la, lb)
    return tab


def _sim_group(teams, tab, played, rng):
    """Roda 1 grupo. Retorna lista ordenada [(team, pts, gd, gf)] do 1º ao 4º."""
    pts = {t: 0 for t in teams}
    gf = {t: 0 for t in teams}
    ga = {t: 0 for t in teams}
    for a, b in combinations(teams, 2):
        if (a, b) in played:
            xa, xb = played[(a, b)]
        elif (b, a) in played:
            xb, xa = played[(b, a)]
        else:
            _, la, lb = tab[(a, b)]
            xa, xb = int(rng.poisson(la)), int(rng.poisson(lb))
        gf[a] += xa; ga[a] += xb; gf[b] += xb; ga[b] += xa
        if xa > xb: pts[a] += 3
        elif xb > xa: pts[b] += 3
        else: pts[a] += 1; pts[b] += 1
    rank = sorted(teams, key=lambda t: (pts[t], gf[t] - ga[t], gf[t], rng.random()), reverse=True)
    return [(t, pts[t], gf[t] - ga[t], gf[t]) for t in rank]


def _knockout_winner(a, b, tab, rng, eps):
    _, la, lb = tab[(a, b)]
    xa, xb = int(rng.poisson(la)), int(rng.poisson(lb))
    if xa > xb: return a
    if xb > xa: return b
    dr = tab[(a, b)][0]
    share_a = 0.5 + eps * ((dr > 0) - (dr < 0))     # contrato §3.2
    return a if rng.random() < share_a else b


def simulate_once(groups, tab, played, rng, p):
    """1 simulação completa. Retorna (champion, finalists set, semis set, advancers set)."""
    firsts, seconds, thirds = [], [], []
    advancers = set()
    for g, teams in groups.items():
        rank = _sim_group(teams, tab, played, rng)
        firsts.append(rank[0][0]); seconds.append(rank[1][0])
        thirds.append(rank[2])     # (team, pts, gd, gf)
        advancers.add(rank[0][0]); advancers.add(rank[1][0])
    # 8 melhores terceiros
    thirds.sort(key=lambda x: (x[1], x[2], x[3], rng.random()), reverse=True)
    best_thirds = [t[0] for t in thirds[:BEST_THIRDS]]
    advancers.update(best_thirds)
    bracket = firsts + seconds + best_thirds       # 12+12+8 = 32
    rng.shuffle(bracket)                            # sorteio aleatório (simplificação declarada)
    semis = set(); finalists = set()
    rounds = [bracket]
    while len(bracket) > 1:
        nxt = [_knockout_winner(bracket[i], bracket[i + 1], tab, rng, p.eps_ko)
               for i in range(0, len(bracket), 2)]
        if len(bracket) == 4: semis = set(bracket)
        if len(bracket) == 2: finalists = set(bracket)
        bracket = nxt
    return bracket[0], finalists, semis, advancers


def run(conn, config_path=DEFAULT_CONFIG, n_sims=20000, seed=12345):
    cfg, groups = load_config(config_path)
    elos = get_elos(conn)
    played = played_results(conn)
    p = PredictParams()
    teams = [t for g in groups.values() for t in g]
    tab = build_lambda_table(teams, elos, p, hosts=cfg.get("hosts"))
    rng = np.random.default_rng(seed)
    champ = {t: 0 for t in teams}
    fin = {t: 0 for t in teams}
    semi = {t: 0 for t in teams}
    adv = {t: 0 for t in teams}
    for _ in range(n_sims):
        c, f, s, a = simulate_once(groups, tab, played, rng, p)
        champ[c] += 1
        for t in f: fin[t] += 1
        for t in s: semi[t] += 1
        for t in a: adv[t] += 1
    rows = [{"team": t, "elo": round(elos.get(t, 1500)),
             "p_champion": champ[t] / n_sims, "p_final": fin[t] / n_sims,
             "p_semi": semi[t] / n_sims, "p_advance": adv[t] / n_sims}
            for t in teams]
    rows.sort(key=lambda r: -r["p_champion"])
    return {"n_sims": n_sims, "model": MODEL_VERSION, "table": rows,
            "n_played_locked": len(played)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Monte Carlo da Copa 2026 (P de título por seleção).")
    ap.add_argument("--db", default=str(DEFAULT_DB))
    ap.add_argument("--config", default=str(DEFAULT_CONFIG))
    ap.add_argument("--sims", type=int, default=20000)
    ap.add_argument("--seed", type=int, default=12345)
    ap.add_argument("--top", type=int, default=24)
    args = ap.parse_args(argv)
    if not Path(args.db).exists():
        print(f"[erro] {args.db} não existe. Rode ingest + elo_engine antes."); return 1
    if not Path(args.config).exists():
        print(f"[erro] sorteio não encontrado: {args.config}\n"
              f"       preencha o modelo dados/copa2026.json com os 12 grupos × 4."); return 1
    conn = db.connect(args.db)
    cfg, groups = load_config(args.config)
    elos = get_elos(conn)
    probs = validate(groups, elos)
    if probs:
        print("⚠ sorteio incompleto/!confere — a simulação pode não refletir a Copa real:")
        for x in probs: print("   -", x)
        print()
    res = run(conn, args.config, n_sims=args.sims, seed=args.seed)
    conn.close()
    print(f"\n  SIMULAÇÃO DA COPA 2026 — {res['n_sims']} torneios  ·  modelo {res['model']}")
    print(f"  ({res['n_played_locked']} jogos já disputados travados da base)\n")
    print(f"  {'#':>2}  {'seleção':<22}{'Elo':>5}  {'campeão':>8} {'final':>7} {'semi':>7} {'passa 1ª':>9}")
    for i, r in enumerate(res["table"][:args.top], 1):
        print(f"  {i:>2}  {r['team']:<22}{r['elo']:>5}  {r['p_champion']*100:>7.1f}% "
              f"{r['p_final']*100:>6.1f}% {r['p_semi']*100:>6.1f}% {r['p_advance']*100:>8.1f}%")
    print("\n  — insight, não validado por backtest; probabilidade, não certeza.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
