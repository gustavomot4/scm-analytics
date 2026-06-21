"""attack_defense — prior ATAQUE/DEFESA não-Elo (diversidade REAL do ensemble; audit P-A).

Problema (auditoria): Poisson e Elo-direto saem do MESMO escalar `dr` — são duas leituras
correlacionadas (P(V) corr ≈ 0,997, [verificado]); o "ensemble" é redundante e o edge sobre o
Elo é minúsculo. Este módulo gera (λ_A, λ_B) de uma fonte INDEPENDENTE: ratings de ataque/defesa
por seleção, estimados dos GOLS (não do dr), como uma terceira perna do ensemble.

Modelo (Maher/Poisson, online e POINT-IN-TIME, paramétrico/auditável — respeita D-02, sem ML):
    λ_home = exp(μ + atk[h] − def[a] + mando_log·não_neutro)
    λ_away = exp(μ + atk[a] − def[h])
Atualização online por jogo (gradiente da NLL de Poisson no log-rate η; erro = λ − gols), com
shrinkage L2 (regularização) dos ratings rumo a 0. O λ PRÉ-jogo é gravado ANTES de atualizar
(anti look-ahead, igual ao `match_ratings` do Elo).

Diversidade [verificado] (torneios n=2.249): corr P(V) Poisson–AD ≈ 0,95 (vs Poisson–Elo 0,997);
AD sozinho Brier 0,5535 < ensemble base 0,5617. PORTÃO de adicionar a perna AD: ΔBrier
**+0,0039 IC[+0,0027,+0,0051]** em w_ad=0,30 (e cresce com o peso) → passa com folga. Adoção =
PredictParams(w_ad>0) + rebuild + bump de versão (mudança de modelo). OFF por padrão.

Uso:
    python -m scm.attack_defense --db dados/scm.sqlite            # mostra ratings + portão
    python -m scm.attack_defense --db dados/scm.sqlite --w-ad 0.4 # portão com peso w_ad
"""
from __future__ import annotations

import argparse
import math
from dataclasses import dataclass
from pathlib import Path

from . import db
from .ingest import DEFAULT_DB


@dataclass(frozen=True)
class ADParams:
    mu_log: float = 0.38        # log da média de gols/time (~1,46) [a calibrar]
    home_log: float = 0.223     # vantagem de casa em log-gols (~1,25x) p/ jogos NÃO-neutros
    lr: float = 0.04            # taxa de aprendizado online [a calibrar]
    reg: float = 0.003          # shrinkage L2 dos ratings (estabilidade) [a calibrar]
    lam_min: float = 0.05
    lam_max: float = 8.0


def _lam(mu: float, atk_self: float, def_opp: float, ha: float, p: ADParams) -> float:
    return min(p.lam_max, max(p.lam_min, math.exp(mu + atk_self - def_opp + ha)))


def _pass(conn, p: ADParams, store_pit: bool = False, priors: dict = None):
    """Passe cronológico único. Retorna (atk, dfn, pit). pit={match_id:(la,lb)} PRÉ-jogo se pedido.

    `priors` (D-67, opcional): {team_id: (atk0_log, def0_log)} — alvo de inicialização E de
    shrinkage (em vez de 0). Vindo do xG (xg_priors), torna os ratings menos ruidosos onde há
    cobertura. Sem priors → shrink rumo a 0 (comportamento original, IDÊNTICO)."""
    priors = priors or {}

    def a0(t):
        return priors.get(t, (0.0, 0.0))[0]

    def d0(t):
        return priors.get(t, (0.0, 0.0))[1]

    atk: dict[int, float] = {}
    dfn: dict[int, float] = {}
    pit: dict[int, tuple] = {}
    rows = conn.execute(
        """SELECT match_id, home_team_id h, away_team_id a, home_score hs, away_score s, neutral
           FROM matches WHERE home_score IS NOT NULL ORDER BY date, match_id"""
    ).fetchall()
    mu = p.mu_log
    for r in rows:
        h, a = r["h"], r["a"]
        ah = atk.get(h, a0(h)); aa = atk.get(a, a0(a)); dh = dfn.get(h, d0(h)); da = dfn.get(a, d0(a))
        ha = 0.0 if r["neutral"] else p.home_log
        lh = _lam(mu, ah, da, ha, p)
        la_ = _lam(mu, aa, dh, 0.0, p)
        if store_pit:
            pit[r["match_id"]] = (lh, la_)            # PRÉ-jogo (anti look-ahead)
        eh = lh - r["hs"]; ea = la_ - r["s"]          # erro (λ − gols) no log-rate
        atk[h] = ah - p.lr * eh - p.lr * p.reg * (ah - a0(h))   # shrink rumo ao prior (0 sem xG)
        dfn[a] = da + p.lr * eh - p.lr * p.reg * (da - d0(a))
        atk[a] = aa - p.lr * ea - p.lr * p.reg * (aa - a0(a))
        dfn[h] = dh + p.lr * ea - p.lr * p.reg * (dh - d0(h))
    return atk, dfn, pit


def xg_priors(conn) -> dict:
    """{team_id: (atk_log, def_log)} a partir do team_xg (D-67). Vazio se não houver xG ingerido.

    atk_log = log(xg_for/média); def_log (força defensiva) = −log(xg_against/média) — conceder
    mais xG = defesa mais fraca. Alimenta o shrinkage do `_pass` (xG menos ruidoso que gols)."""
    from .xg import xg_factor
    out = {}
    for r in conn.execute("SELECT t.team_id, t.name FROM team_xg x JOIN teams t USING(team_id)"):
        f = xg_factor(conn, r["name"])
        if f:
            out[r["team_id"]] = (math.log(max(0.2, f["ataque"])), -math.log(max(0.2, f["defesa"])))
    return out


def run_pit(conn, p: ADParams = ADParams(), priors: dict = None) -> dict:
    """{match_id: (λ_home, λ_away)} PRÉ-jogo (PIT) — consumido pelo `predictor` (w_ad>0) e pelo portão.

    `priors` (xG, D-67) opcional: passe `xg_priors(conn)` p/ shrinkage rumo ao xG (menos ruidoso)."""
    _, _, pit = _pass(conn, p, store_pit=True, priors=priors)
    return pit


def fit(conn, p: ADParams = ADParams(), priors: dict = None):
    """(atk, dfn) finais — estado atual dos ratings p/ prever um confronto FUTURO (predict_match)."""
    atk, dfn, _ = _pass(conn, p, store_pit=False, priors=priors)
    return atk, dfn


def team_lambdas(atk, dfn, home_id, away_id, neutral: bool = True, p: ADParams = ADParams()):
    """(λ_home, λ_away) do confronto a partir dos ratings AD (p/ um jogo avulso)."""
    ah = atk.get(home_id, 0.0); aa = atk.get(away_id, 0.0)
    dh = dfn.get(home_id, 0.0); da = dfn.get(away_id, 0.0)
    ha = 0.0 if neutral else p.home_log
    return _lam(p.mu_log, ah, da, ha, p), _lam(p.mu_log, aa, dh, 0.0, p)


def gate_ad(conn, w_ad: float = 0.40, only_major: bool = True, B: int = 10000, seed: int = 12345,
            priors: dict = None) -> dict:
    """PORTÃO: adicionar a perna AD ao ensemble (ΔBrier pareado vs ensemble atual).

    Imports de `predictor`/`backtest_harness` ficam LOCAIS (dentro da função) p/ o módulo não
    criar ciclo — `predictor.run` importa `run_pit` (puro) no topo do passe. `priors` (xG, D-67)
    opcional: gateia a versão alimentada por xG.
    """
    from .predictor import PredictParams, lambdas, poisson_reads, ved_from_elo, _clamp_norm
    from .backtest_harness import brier, outcome_of, gate, MAJOR
    from .features_pit import team_form, FeatureParams
    p = PredictParams(); fp = FeatureParams()
    pit = run_pit(conn, priors=priors)
    rows = conn.execute(
        """SELECT m.match_id, m.date, m.home_team_id h, m.away_team_id a, mr.dr dr_elo,
                  m.home_score hs, m.away_score s, m.tournament t
           FROM matches m JOIN match_ratings mr USING(match_id) WHERE m.home_score IS NOT NULL"""
    ).fetchall()
    if only_major:
        rows = [r for r in rows if r["t"] in MAJOR]
    deltas = []
    for r in rows:
        fh, _, _ = team_form(conn, r["h"], r["date"], fp)
        fa, _, _ = team_form(conn, r["a"], r["date"], fp)
        dr = r["dr_elo"] + fh - fa
        o = outcome_of(r["hs"], r["s"])
        la, lb = lambdas(dr, p)
        pr = poisson_reads(la, lb, p.max_goals)
        cp = _clamp_norm((pr["pv"], pr["pe"], pr["pd"]), p.clamp_lo, p.clamp_hi)
        ce = _clamp_norm(ved_from_elo(dr, p), p.clamp_lo, p.clamp_hi)
        lah, lbh = pit[r["match_id"]]
        ar = poisson_reads(lah, lbh, p.max_goals)
        ca = _clamp_norm((ar["pv"], ar["pe"], ar["pd"]), p.clamp_lo, p.clamp_hi)
        ws = p.w_poisson + p.w_elo
        base = _clamp_norm([(p.w_poisson * cp[i] + p.w_elo * ce[i]) / ws for i in range(3)],
                           p.clamp_lo, p.clamp_hi)
        ws2 = ws + w_ad
        mix = _clamp_norm([(p.w_poisson * cp[i] + p.w_elo * ce[i] + w_ad * ca[i]) / ws2 for i in range(3)],
                          p.clamp_lo, p.clamp_hi)
        bb = {"p_v": base[0], "p_e": base[1], "p_d": base[2]}
        bm = {"p_v": mix[0], "p_e": mix[1], "p_d": mix[2]}
        deltas.append(brier(bb, o) - brier(bm, o))   # >0 = AD melhora
    if not deltas:
        return {"n": 0}
    g = gate(deltas, B=B, seed=seed)
    return {"n": len(deltas), "w_ad": w_ad, **g}


def gate_xg_increment(conn, w_ad=None, only_major: bool = True, B: int = 10000, seed: int = 12345):
    """PORTAO: o prior de xG ACRESCENTA sobre a perna AD atual? ΔBrier pareado (IC).

    Compara ensemble[Poisson+Elo+AD(xG)] vs ensemble[Poisson+Elo+AD(sem xG)] por jogo (delta =
    brier_sem − brier_com, >0 = xG melhora). keep = IC95 > 0. Usa dr_adj de match_features
    (rápido). Precisa de team_xg ingerido (scm.xg ingest/build). É o portão da regra do projeto
    (nada entra em λ sem IC que não cruza zero) ANTES de ligar config.USE_XG_PRIOR.
    """
    from .predictor import PredictParams, lambdas, poisson_reads, ved_from_elo, _clamp_norm
    from .backtest_harness import brier, outcome_of, gate, MAJOR
    p = PredictParams(); wad = p.w_ad if w_ad is None else w_ad
    pri = xg_priors(conn)
    if not pri:
        return {"n": 0, "erro": "team_xg vazio — rode `python -m scm.xg ingest <csv>` ou `build`"}
    pit_x = run_pit(conn, priors=pri); pit_p = run_pit(conn, priors=None)
    rows = conn.execute("SELECT mf.match_id mid, mf.dr_adj dr, m.home_score hs, m.away_score s, "
                        "m.tournament t FROM match_features mf JOIN matches m USING(match_id) "
                        "WHERE m.home_score IS NOT NULL").fetchall()
    if only_major:
        rows = [r for r in rows if r["t"] in MAJOR]
    ws = p.w_poisson + p.w_elo + wad

    def mix(cp, ce, ca):
        return _clamp_norm([(p.w_poisson * cp[i] + p.w_elo * ce[i] + wad * ca[i]) / ws for i in range(3)],
                           p.clamp_lo, p.clamp_hi)

    deltas = []
    for r in rows:
        la, lb = lambdas(r["dr"], p); pr = poisson_reads(la, lb)
        cp = _clamp_norm((pr["pv"], pr["pe"], pr["pd"]), p.clamp_lo, p.clamp_hi)
        ce = _clamp_norm(ved_from_elo(r["dr"], p), p.clamp_lo, p.clamp_hi)
        lax, lbx = pit_x.get(r["mid"], (None, None)); lap, lbp = pit_p.get(r["mid"], (None, None))
        if lax is None or lap is None:
            continue
        arx = poisson_reads(lax, lbx); arp = poisson_reads(lap, lbp)
        cax = _clamp_norm((arx["pv"], arx["pe"], arx["pd"]), p.clamp_lo, p.clamp_hi)
        cap = _clamp_norm((arp["pv"], arp["pe"], arp["pd"]), p.clamp_lo, p.clamp_hi)
        o = outcome_of(r["hs"], r["s"])
        mx = mix(cp, ce, cax); mp = mix(cp, ce, cap)
        deltas.append(brier({"p_v": mp[0], "p_e": mp[1], "p_d": mp[2]}, o)
                      - brier({"p_v": mx[0], "p_e": mx[1], "p_d": mx[2]}, o))
    if not deltas:
        return {"n": 0}
    g = gate(deltas, B=B, seed=seed)
    return {"n": len(deltas), "w_ad": wad, **g}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Prior ataque/defesa não-Elo (candidato P-A): ratings + portão.")
    ap.add_argument("--db", default=str(DEFAULT_DB))
    ap.add_argument("--w-ad", type=float, default=0.40, dest="w_ad", help="peso da perna AD no ensemble")
    ap.add_argument("--xg-prior", action="store_true", dest="xg_prior",
                    help="[D-67] usa o xG (team_xg) como prior do ataque/defesa (menos ruidoso que gols)")
    ap.add_argument("--gate-xg", dest="gate_xg", action="store_true",
                    help="PORTÃO: o prior de xG acrescenta sobre a perna AD? (precisa de team_xg)")
    ap.add_argument("--top", type=int, default=12)
    args = ap.parse_args(argv)
    if not Path(args.db).exists():
        print(f"[erro] {args.db} não existe. Rode ingest + elo_engine antes."); return 1
    conn = db.connect(args.db)
    if getattr(args, "gate_xg", False):
        r = gate_xg_increment(conn, w_ad=args.w_ad); conn.close()
        if not r.get("n"):
            print("[!]", r.get("erro", "sem dados (rode o pipeline)")); return 1
        print(f"\n  PORTÃO xG (incremento sobre a perna AD) — w_ad={r['w_ad']:.2f}, n={r['n']}")
        print(f"  ΔBrier(com xG − sem xG, >0 = melhora) = {r['mean']:+.5f}  IC95 [{r['ic_lo']:+.5f}, {r['ic_hi']:+.5f}]")
        print("  → " + ("ADOTAR xG ✓ (IC>0): ligue config.USE_XG_PRIOR=True + rebuild + bump de versão"
                        if r["keep"] else "NÃO adotar (IC cruza/≤0) — mantém AD sem xG") + "\n")
        return 0
    priors = xg_priors(conn) if args.xg_prior else None
    if args.xg_prior and not priors:
        print("[aviso] sem xG ingerido (team_xg vazio) — rode `python -m scm.xg ingest <csv>`. Seguindo sem prior.")
    atk, dfn = fit(conn, priors=priors)
    top = conn.execute(
        """SELECT t.team_id, t.name FROM ratings_current r JOIN teams t USING(team_id)
           ORDER BY r.elo DESC LIMIT ?""", (args.top,)).fetchall()
    print(f"\n  ATAQUE/DEFESA (não-Elo) — top {args.top} por Elo  (atk>0 marca mais; def<0 sofre menos)")
    for row in top:
        print(f"    {row['name']:<20} atk {atk.get(row['team_id'],0.0):+.2f}  def {dfn.get(row['team_id'],0.0):+.2f}")
    g = gate_ad(conn, w_ad=args.w_ad, priors=priors)
    conn.close()
    if not g.get("n"):
        print("\n  sem dados p/ o portão (rode o pipeline)."); return 1
    print(f"\n  PORTÃO — perna AD no ensemble (w_ad={g['w_ad']:.2f}, n={g['n']} torneios)")
    print(f"  ΔBrier (com AD − sem AD, >0 = melhora) = {g['mean']:+.5f}  IC95 [{g['ic_lo']:+.5f}, {g['ic_hi']:+.5f}]")
    print(f"  → {'ADOTAR perna AD ✓ (IC>0)' if g['keep'] else 'NÃO adotar (IC cruza/≤0)'}")
    print("  adoção: PredictParams(w_ad=...) + rebuild (predictor) + bump de versão.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
