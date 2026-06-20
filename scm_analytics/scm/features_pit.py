"""features_pit: monta features POINT-IN-TIME por jogo (só dados com data < t).

Consome `match_ratings` (elo_engine) + `matches`; grava `match_features`.
Aceite (M3): teste ANTI LOOK-AHEAD — as features de um jogo não mudam se jogos
FUTUROS forem alterados. Contrato: forma recente (vault `02 - Modelos/Forma recente.md`)
e incerteza (`Incerteza e propagacao.md`). Constantes [a calibrar].
"""
from __future__ import annotations

import argparse
import math
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Optional

from . import db
from .elo_engine import EloParams, sigma_r
from .ingest import DEFAULT_DB


@dataclass(frozen=True)
class FeatureParams:
    form_window: int = 10          # últimas N partidas
    form_scale: float = 60.0       # residual[-1,1] -> Elo [a calibrar]
    form_cap: float = 30.0         # cap ±30 Elo (contrato)
    recency_base: float = 0.9      # peso = base^meses
    friendly_weight: float = 0.5   # amistoso pesa metade
    sigma_ajuste_c: float = 80.0   # σ_ajuste = c·desvio_forma [a calibrar]


def _months(d_past: str, d_ref: str) -> float:
    try:
        a = date.fromisoformat(d_past)
        b = date.fromisoformat(d_ref)
    except ValueError:
        return 0.0
    return max(0.0, (b - a).days / 30.44)


def _is_friendly(t: Optional[str]) -> bool:
    return "friendly" in (t or "").lower()


def vol_mult(desvio: float, n_form: int = 99, ref: float = 0.35, min_n: int = 5) -> float:
    """Multiplicador de σ_R pela (in)consistência recente da seleção.

    Resolve a degenerescência do σ_R antigo (função só de nº de jogos → ~40 fixo p/
    toda seleção estabelecida). Time errático (desvio de forma alto) → σ_R maior;
    consistente → menor. ~1.0 quando desvio≈ref; clampado em [0.6, 1.6].
    Com POUCA forma (n_form < min_n) retorna 1.0 (neutro): desvio≈0 ali significa
    'sem informação', não 'consistente' — um estreante deve manter σ_R alto.
    """
    if n_form < min_n:
        return 1.0
    return max(0.6, min(1.6, 0.4 + 0.6 * desvio / ref))


def team_form(conn, team_id: int, before_date: str, p: FeatureParams):
    """(form_ΔE, desvio_forma, n) usando SÓ jogos com date < before_date.

    Residual = pontuação real − expectativa Elo (we), por jogo, ajustado a adversário
    e mando (we já os embute). Ponderado por recência e tipo (amistoso 0.5).
    """
    rows = conn.execute(
        """SELECT m.date, m.tournament, m.home_team_id, m.away_team_id,
                  m.home_score, m.away_score, mr.we_home
           FROM matches m JOIN match_ratings mr USING (match_id)
           WHERE (m.home_team_id = ? OR m.away_team_id = ?) AND m.date < ?
           ORDER BY m.date DESC LIMIT ?""",
        (team_id, team_id, before_date, p.form_window),
    ).fetchall()
    if not rows:
        return 0.0, 0.0, 0
    resid, wts = [], []
    for r in rows:
        gd = r["home_score"] - r["away_score"]
        if r["home_team_id"] == team_id:
            actual = 1.0 if gd > 0 else (0.5 if gd == 0 else 0.0)
            exp = r["we_home"]
        else:
            actual = 1.0 if gd < 0 else (0.5 if gd == 0 else 0.0)
            exp = 1.0 - r["we_home"]
        w = (p.recency_base ** _months(r["date"], before_date)) * (
            p.friendly_weight if _is_friendly(r["tournament"]) else 1.0
        )
        resid.append(actual - exp)
        wts.append(w)
    sw = sum(wts)
    if sw < 1e-9:
        return 0.0, 0.0, len(rows)
    wmean = sum(x * w for x, w in zip(resid, wts)) / sw
    var = sum(w * (x - wmean) ** 2 for x, w in zip(resid, wts)) / sw
    form = max(-p.form_cap, min(p.form_cap, p.form_scale * wmean))
    return form, math.sqrt(var), len(rows)


def run(conn, params: FeatureParams = FeatureParams(),
        elo_params: EloParams = EloParams(), use_glicko: bool = False) -> dict:
    """Monta match_features para todos os jogos. Idempotente. Exige elo_engine antes.

    use_glicko (candidato P-B/D-42, OFF por padrão): usa o RD de Glicko-1 PIT
    (`sigma_glicko.run_pit`) como base de σ_R, em vez de `sigma_r(n)·vol_mult` — que satura ~40
    p/ TODA elite, tornando banda/confiança pouco informativas. Adoção exige o portão de
    cobertura de banda: `python -m scm.sigma_glicko --gate`.
    """
    db.init_schema(conn)
    if conn.execute("SELECT COUNT(*) FROM match_ratings").fetchone()[0] == 0:
        raise RuntimeError("match_ratings vazio — rode elo_engine.run primeiro.")
    glicko_pit = None
    if use_glicko:
        from .sigma_glicko import run_pit
        glicko_pit = run_pit(conn)   # {match_id: (rd_home, rd_away)} PIT (anti look-ahead)
    conn.execute("DELETE FROM match_features")
    rows = conn.execute(
        """SELECT m.match_id, m.date, m.home_team_id, m.away_team_id,
                  mr.dr AS dr_elo, mr.home_n_pre, mr.away_n_pre
           FROM matches m JOIN match_ratings mr USING (match_id)
           ORDER BY m.date, m.match_id"""
    ).fetchall()
    n = 0
    for r in rows:
        fh, dh, nh_f = team_form(conn, r["home_team_id"], r["date"], params)
        fa, da, na_f = team_form(conn, r["away_team_id"], r["date"], params)
        if glicko_pit is not None:
            sr_h, sr_a = glicko_pit[r["match_id"]]   # σ_R guiado por dados (RD varia ~51–64 nas elites)
        else:
            sr_h = sigma_r(r["home_n_pre"], elo_params) * vol_mult(dh, nh_f)
            sr_a = sigma_r(r["away_n_pre"], elo_params) * vol_mult(da, na_f)
        sa_h = params.sigma_ajuste_c * dh
        sa_a = params.sigma_ajuste_c * da
        dr_adj = r["dr_elo"] + fh - fa
        sigma_dr = math.sqrt(sr_h ** 2 + sr_a ** 2 + sa_h ** 2 + sa_a ** 2)
        conn.execute(
            """INSERT OR REPLACE INTO match_features
               (match_id, dr_elo, form_home, form_away, dr_adj,
                sigma_r_home, sigma_r_away, sigma_ajuste_home, sigma_ajuste_away,
                sigma_dr, n_home_pre, n_away_pre)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (r["match_id"], r["dr_elo"], fh, fa, dr_adj, sr_h, sr_a, sa_h, sa_a,
             sigma_dr, r["home_n_pre"], r["away_n_pre"]),
        )
        n += 1
    conn.commit()
    return {"features": n}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Monta features point-in-time por jogo.")
    p.add_argument("--db", default=str(DEFAULT_DB))
    p.add_argument("--glicko", action="store_true",
                   help="[candidato P-B/D-42] usa σ_R de Glicko-1 (RD PIT) em vez de sigma_r(n)·vol_mult")
    args = p.parse_args(argv)
    if not Path(args.db).exists():
        print(f"[erro] SQLite não encontrado: {args.db}. Rode ingest + elo_engine antes.")
        return 1
    conn = db.connect(args.db)
    stats = run(conn, use_glicko=args.glicko)
    print(f"features montadas: {stats['features']} jogos" + ("  [σ=Glicko]" if args.glicko else ""))
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
