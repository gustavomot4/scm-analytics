"""backtest_harness: métricas, ICs e o PORTÃO. Lê `predictions` + resultados reais.

- Brier (forma-soma, máx 2), LogLoss, RPS (ordinal) por jogo e médios.
- Bootstrap com **seed fixa** (reprodutível) p/ IC.
- evaluate(versao): mede o modelo e testa se bate o **uniforme** com IC que não cruza zero.
- gate(deltas): mantém um termo SSE o IC95 de ΔBrier (pareado) não cruza zero
  (o antídoto a comparações múltiplas; lógica validada em camada2-baseline-plano §6).
- compare(vA, vB): ΔBrier pareado por jogo entre duas versões de modelo.

Baseline público (eloratings) só com dados reais na máquina do usuário; aqui o
comparador disponível é o **uniforme** e o **Elo-direto** (we_home de match_ratings).
"""
from __future__ import annotations

import argparse
import math
import numpy as np
from pathlib import Path

from . import db
from .ingest import DEFAULT_DB
from .predictor import MODEL_VERSION as _MODEL

_TARGET = {"V": (1.0, 0.0, 0.0), "E": (0.0, 1.0, 0.0), "D": (0.0, 0.0, 1.0)}
UNIFORM = {"p_v": 1 / 3, "p_e": 1 / 3, "p_d": 1 / 3}
# torneios comparáveis a 2026 (finais; exclui eliminatórias) — desenho C2 §2.2
MAJOR = ("FIFA World Cup", "UEFA Euro", "Copa América", "Copa America")


def outcome_of(home_score: int, away_score: int) -> str:
    if home_score > away_score:
        return "V"
    if home_score == away_score:
        return "E"
    return "D"


def _p(row) -> tuple:
    return (row["p_v"], row["p_e"], row["p_d"])


def brier(p: dict, o: str) -> float:
    t = _TARGET[o]
    pv = (p["p_v"], p["p_e"], p["p_d"])
    return sum((pv[i] - t[i]) ** 2 for i in range(3))


def logloss(p: dict, o: str) -> float:
    pr = {"V": p["p_v"], "E": p["p_e"], "D": p["p_d"]}[o]
    return -math.log(max(pr, 1e-12))


def rps(p: dict, o: str) -> float:
    o3 = _TARGET[o]
    pv = (p["p_v"], p["p_e"], p["p_d"])
    c1 = pv[0] - o3[0]
    c2 = (pv[0] + pv[1]) - (o3[0] + o3[1])
    return 0.5 * (c1 * c1 + c2 * c2)


def load_scored(conn, versao: str, only_major: bool = False) -> list:
    q = ("SELECT p.p_v, p.p_e, p.p_d, m.home_score, m.away_score "
         "FROM predictions p JOIN matches m USING (match_id) WHERE p.versao_modelo = ?")
    params = [versao]
    if only_major:
        q += " AND m.tournament IN (%s)" % ",".join("?" * len(MAJOR))
        params += list(MAJOR)
    rows = conn.execute(q, params).fetchall()
    out = []
    for r in rows:
        o = outcome_of(r["home_score"], r["away_score"])
        out.append(({"p_v": r["p_v"], "p_e": r["p_e"], "p_d": r["p_d"]}, o))
    return out


def metrics(items: list) -> dict:
    n = len(items)
    if n == 0:
        return {"n": 0}
    return {
        "n": n,
        "brier": sum(brier(p, o) for p, o in items) / n,
        "logloss": sum(logloss(p, o) for p, o in items) / n,
        "rps": sum(rps(p, o) for p, o in items) / n,
    }


def _boot_ci(values: list, B: int = 10000, seed: int = 12345, lo: float = 0.025, hi: float = 0.975):
    """IC por bootstrap, vetorizado (numpy). Seed fixa -> reprodutível."""
    arr = np.asarray(values, dtype=float)
    n = arr.size
    rng = np.random.default_rng(seed)
    means = np.empty(B)
    for i in range(B):
        means[i] = arr[rng.integers(0, n, n)].mean()
    means.sort()
    return float(means[int(lo * B)]), float(means[int(hi * B)])


def gate(delta_per_match: list, B: int = 10000, seed: int = 12345) -> dict:
    """delta = brier_SEM − brier_COM (>0 = 'com' melhora). Mantém SSE IC95 inteiro > 0."""
    mean = sum(delta_per_match) / len(delta_per_match)
    lo, hi = _boot_ci(delta_per_match, B, seed)
    return {"mean": mean, "ic_lo": lo, "ic_hi": hi, "keep": lo > 0}


def evaluate(conn, versao: str, B: int = 10000, seed: int = 12345, only_major: bool = False) -> dict:
    items = load_scored(conn, versao, only_major=only_major)
    m = metrics(items)
    m["versao"] = versao
    if not items:
        return m
    # ganho vs uniforme, por jogo (pareado): brier_uniforme − brier_modelo  (>0 = modelo melhor)
    d = [brier(UNIFORM, o) - brier(p, o) for p, o in items]
    g = gate(d, B, seed)
    m.update(
        brier_uniforme=round(brier(UNIFORM, "V"), 4),  # = 0.6667 p/ qualquer o
        ganho_vs_uniforme=g["mean"], ic_lo=g["ic_lo"], ic_hi=g["ic_hi"],
        bate_uniforme_com_ic=g["keep"],
    )
    return m


def elo_baseline_read(dr, p=None):
    """Baseline 'Elo publico' independente: P(V/E/D) so do Elo pre-jogo.

    we(dr) (expectativa de pontuacao) + curva de empate empirica C1, SEM forma,
    SEM altitude, SEM Poisson, SEM propagacao, SEM ensemble. E o comparador minimo
    exigido pelo aceite (camada2-planejamento-v1 §5.1) — bem mais forte que o uniforme.
    """
    from .predictor import PredictParams, draw_prob, _clamp_norm
    from .elo_engine import we
    p = p or PredictParams()
    w = we(dr)
    m = min(w, 1.0 - w)
    pe = max(0.0, min(draw_prob(dr, p), 2.0 * m - p.draw_eps))
    pv = w - pe / 2.0
    pd = 1.0 - pv - pe
    v = _clamp_norm((pv, pe, pd), p.clamp_lo, p.clamp_hi)
    return {"p_v": v[0], "p_e": v[1], "p_d": v[2]}


def evaluate_vs_elo(conn, versao, B=10000, seed=12345, only_major=False):
    """MODELO vs baseline Elo publico (delta-Brier pareado por jogo, IC bootstrap).

    delta = brier_elo - brier_modelo (>0 = modelo melhor). Veredito: 'melhor' se IC95>0,
    'empata' se IC contem 0, 'pior' se IC<0. Contrato pede ~Elo publico (nao pior).
    """
    q = ("SELECT p.p_v, p.p_e, p.p_d, mr.dr, m.home_score, m.away_score "
         "FROM predictions p JOIN matches m USING (match_id) "
         "JOIN match_ratings mr USING (match_id) WHERE p.versao_modelo = ?")
    params = [versao]
    if only_major:
        q += " AND m.tournament IN (%s)" % ",".join("?" * len(MAJOR))
        params += list(MAJOR)
    rows = conn.execute(q, params).fetchall()
    if not rows:
        return {"n": 0}
    deltas, sb_model, sb_elo = [], 0.0, 0.0
    for r in rows:
        o = outcome_of(r["home_score"], r["away_score"])
        pm = {"p_v": r["p_v"], "p_e": r["p_e"], "p_d": r["p_d"]}
        pe = elo_baseline_read(r["dr"])
        bm, be = brier(pm, o), brier(pe, o)
        sb_model += bm
        sb_elo += be
        deltas.append(be - bm)
    g = gate(deltas, B, seed)
    n = len(deltas)
    if g["ic_lo"] > 0:
        verdict = "melhor que o Elo (IC>0)"
    elif g["ic_hi"] < 0:
        verdict = "PIOR que o Elo (IC<0)"
    else:
        verdict = "empata com o Elo (IC contem 0)"
    return {"n": n, "brier_modelo": sb_model / n, "brier_elo": sb_elo / n,
            "ganho_vs_elo": g["mean"], "ic_lo": g["ic_lo"], "ic_hi": g["ic_hi"],
            "bate_elo": g["keep"], "veredito": verdict}


def compare(conn, versao_a: str, versao_b: str, B: int = 10000, seed: int = 12345) -> dict:
    """ΔBrier pareado por match entre A e B (delta = brier_B − brier_A; >0 = A melhor)."""
    a = {r["match_id"]: r for r in conn.execute(
        "SELECT match_id, p_v, p_e, p_d FROM predictions WHERE versao_modelo=?", (versao_a,))}
    b = {r["match_id"]: r for r in conn.execute(
        "SELECT match_id, p_v, p_e, p_d FROM predictions WHERE versao_modelo=?", (versao_b,))}
    res = {r["match_id"]: (r["home_score"], r["away_score"]) for r in conn.execute(
        "SELECT match_id, home_score, away_score FROM matches")}
    deltas = []
    for mid in set(a) & set(b) & set(res):
        o = outcome_of(*res[mid])
        pa = {"p_v": a[mid]["p_v"], "p_e": a[mid]["p_e"], "p_d": a[mid]["p_d"]}
        pb = {"p_v": b[mid]["p_v"], "p_e": b[mid]["p_e"], "p_d": b[mid]["p_d"]}
        deltas.append(brier(pb, o) - brier(pa, o))
    return gate(deltas, B, seed) if deltas else {"keep": False, "n": 0}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Backtest: métricas + IC vs uniforme.")
    p.add_argument("--db", default=str(DEFAULT_DB))
    p.add_argument("--versao", default=_MODEL)
    p.add_argument("--major", action="store_true", help="só torneios (WC/Euro/Copa América)")
    args = p.parse_args(argv)
    if not Path(args.db).exists():
        print(f"[erro] SQLite não encontrado: {args.db}. Rode o pipeline antes.")
        return 1
    conn = db.connect(args.db)
    m = evaluate(conn, args.versao, only_major=args.major)
    if m.get("n", 0) == 0:
        conn.close()
        print(f"sem previsões p/ versão {args.versao}")
        return 1
    print(f"versão {m['versao']}  |  n={m['n']}")
    print(f"  Brier   = {m['brier']:.4f}  (uniforme {m['brier_uniforme']})")
    print(f"  LogLoss = {m['logloss']:.4f}  (uniforme {math.log(3):.4f})")
    print(f"  RPS     = {m['rps']:.4f}")
    print(f"  ganho vs uniforme = {m['ganho_vs_uniforme']:+.4f}  IC95 [{m['ic_lo']:+.4f}, {m['ic_hi']:+.4f}]")
    print(f"  bate uniforme (IC não cruza 0)? {'SIM' if m['bate_uniforme_com_ic'] else 'NÃO'}")
    e = evaluate_vs_elo(conn, args.versao, only_major=args.major)
    if e.get("n"):
        print("  --- vs baseline ELO PUBLICO (we + curva empirica C1) ---")
        print(f"  Brier modelo {e['brier_modelo']:.4f}  vs  Elo {e['brier_elo']:.4f}")
        print(f"  ganho vs Elo = {e['ganho_vs_elo']:+.4f}  IC95 [{e['ic_lo']:+.4f}, {e['ic_hi']:+.4f}]  -> {e['veredito']}")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
