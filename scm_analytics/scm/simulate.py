"""simulate — Monte Carlo do torneio (Camada 5): P(campeão), P(final), P(semi), P(passar).

Lê o sorteio de `dados/copa2026.json` (12 grupos × 4 seleções) e usa o Elo atual
(`ratings_current`) + as λ do modelo (`predictor.lambdas`) para amostrar PLACAR de cada
jogo (Poisson). Mata-mata: empate resolvido pelo termo do contrato §3.2
(`predictor.knockout_advance`, ε≈0.03). Resultados já disputados na base (martj42) são
TRAVADOS (simulação de meio de torneio é coerente).

INSIGHT, não previsão validada por backtest — herda as limitações do modelo.
Probabilidades, nunca certezas. Tudo local, R$ 0.

Simplificações declaradas:
- Chaveamento **OFICIAL da FIFA** (R32 73-88 -> ... -> final 104). Os 8 terceiros são
  alocados às vagas por **elegibilidade** do Anexo C (matching); não se reproduz o
  desempate linha-a-linha das 495 combinações (efeito ínfimo no título).
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

# ---- Chaveamento OFICIAL da FIFA 2026 (Wikipedia / Regulamento Anexo C) ----
# R32: (match_id, slotA, slotB). "1X"/"2X" = 1º/2º do grupo X; "T_X" = vaga de 3º.
R32 = [
    (73, "2A", "2B"), (74, "1E", "T_E"), (75, "1F", "2C"), (76, "1C", "2F"),
    (77, "1I", "T_I"), (78, "2E", "2I"), (79, "1A", "T_A"), (80, "1L", "T_L"),
    (81, "1D", "T_D"), (82, "1G", "T_G"), (83, "2K", "2L"), (84, "1H", "2J"),
    (85, "1B", "T_B"), (86, "1J", "2H"), (87, "1K", "T_K"), (88, "2D", "2G"),
]
# elegibilidade de cada vaga de 3º (grupos de onde aquele 3º pode vir) — Anexo C
THIRD_SLOTS = {
    "T_E": set("ABCDF"), "T_I": set("CDFGH"), "T_A": set("CEFHI"), "T_L": set("EHIJK"),
    "T_D": set("BEFIJ"), "T_G": set("AEHIJ"), "T_B": set("EFGIJ"), "T_K": set("DEIJL"),
}
# árvore R16 -> final: (match_id, vem_de_A, vem_de_B)
LATER = [
    (89, 74, 77), (90, 73, 75), (91, 76, 78), (92, 79, 80),
    (93, 83, 84), (94, 81, 82), (95, 86, 88), (96, 85, 87),
    (97, 89, 90), (98, 93, 94), (99, 91, 92), (100, 95, 96),
    (101, 97, 98), (102, 99, 100), (104, 101, 102),
]


def _assign_thirds(qual_groups):
    """Aloca os 8 grupos-3º qualificados às 8 vagas T_* respeitando a elegibilidade.

    Backtracking (8x8, instantâneo). Existe sempre uma alocação perfeita p/ qualquer
    subconjunto de 8 grupos (é o que o Anexo C garante). Quando há mais de uma alocação
    válida, escolhemos UMA determinística — a estrutura/elegibilidade real é respeitada;
    só não se reproduz o desempate exato linha-a-linha do Anexo C (efeito ínfimo no título).
    """
    slots = list(THIRD_SLOTS.keys())
    assign = {}
    def bt(k, used):
        if k == len(slots):
            return True
        slot = slots[k]
        for g in sorted(qual_groups):
            if g not in used and g in THIRD_SLOTS[slot]:
                assign[slot] = g
                used.add(g)
                if bt(k + 1, used):
                    return True
                used.discard(g); del assign[slot]
        return False
    bt(0, set())
    return assign


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
    """1 simulação completa pelo CHAVEAMENTO OFICIAL. Retorna (champion, finalists, semis, advancers)."""
    firsts, seconds, thirds = {}, {}, []
    advancers = set()
    for g, teams in groups.items():
        rank = _sim_group(teams, tab, played, rng)
        firsts[g] = rank[0][0]; seconds[g] = rank[1][0]
        thirds.append((g,) + rank[2])              # (grupo, team, pts, gd, gf)
        advancers.add(firsts[g]); advancers.add(seconds[g])
    thirds.sort(key=lambda x: (x[2], x[3], x[4], rng.random()), reverse=True)
    best = thirds[:BEST_THIRDS]
    third_team = {x[0]: x[1] for x in best}        # grupo -> seleção 3ª
    for x in best:
        advancers.add(x[1])
    slot_group = _assign_thirds(set(third_team))   # vaga T_* -> grupo

    def team_of(code):
        if code in THIRD_SLOTS:
            return third_team[slot_group[code]]
        return (firsts if code[0] == "1" else seconds)[code[1]]

    win = {}
    for mid, a, b in R32:
        win[mid] = _knockout_winner(team_of(a), team_of(b), tab, rng, p.eps_ko)
    for mid, a, b in LATER:
        win[mid] = _knockout_winner(win[a], win[b], tab, rng, p.eps_ko)
    semis = {win[97], win[98], win[99], win[100]}
    finalists = {win[101], win[102]}
    return win[104], finalists, semis, advancers


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
