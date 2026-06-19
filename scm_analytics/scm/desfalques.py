"""desfalques — Camada 3 (P-F / D-41): ajuste DIRECIONAL por ausências (lesões/suspensões).

Contrato "Desfalques direcionais":
  - ATAQUE fora  → corta o gol esperado do PRÓPRIO time (entra como Δ no GD, via gd_alt);
  - DEFESA/GOLEIRO fora → enfraquece o rating efetivo do time (entra como Δ no dr).

Tiers [a calibrar] (somados por time/setor):
  defesa/goleiro (Elo):  chave 35 · importante 15 · rodízio 5
  ataque (gols):         chave 0.25 · importante 0.12 · rodízio 0.04
  meio-campo            → metade do peso de defesa no dr (influência difusa)

NÃO inventa dados: as ausências vêm de um JSON que o usuário preenche por jogo
(`dados/desfalques.json`). Reusa o `dr` e o `gd_alt` do `predict_match` — o núcleo
(predictor) não muda. As magnitudes são placeholders e ficam candidatas ao portão
quando existir uma base de escalações (não há fonte gratuita estruturada hoje —
ver [[Fontes gratuitas]] "lacunas declaradas").

Formato do JSON (chave = "YYYY-MM-DD|Home|Away", nomes padrão martj42):
{
  "2026-06-20|Mexico|South Korea": {
    "home": [{"setor": "ataque", "tier": "chave"}],
    "away": [{"setor": "defesa", "tier": "importante"}, {"setor": "goleiro", "tier": "rodizio"}]
  }
}
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

TIERS_ELO = {"chave": 35.0, "importante": 15.0, "rodizio": 5.0}     # defesa/goleiro -> dr
TIERS_GOL = {"chave": 0.25, "importante": 0.12, "rodizio": 0.04}    # ataque -> GD (gols)
DEFESA = {"defesa", "zaga", "goleiro", "gk", "lateral"}
ATAQUE = {"ataque", "atacante", "ponta", "meia-atacante"}
MEIO = {"meio", "meio-campo", "volante"}


def team_penalty(outs) -> tuple:
    """(penalidade_defensiva_Elo, penalidade_ofensiva_gols) de uma lista de ausências."""
    def_elo = 0.0
    atk_gol = 0.0
    for o in outs or []:
        setor = str(o.get("setor", "")).strip().lower()
        tier = str(o.get("tier", "")).strip().lower()
        if setor in ATAQUE:
            atk_gol += TIERS_GOL.get(tier, 0.0)
        elif setor in DEFESA:
            def_elo += TIERS_ELO.get(tier, 0.0)
        elif setor in MEIO:
            def_elo += TIERS_ELO.get(tier, 0.0) * 0.5
        # setor desconhecido -> ignora (não inventa efeito)
    return def_elo, atk_gol


def match_deltas(home_outs, away_outs) -> tuple:
    """(dr_delta, gd_delta) a somar ao dr e ao gd_alt do confronto (A=home, B=away)."""
    def_h, atk_h = team_penalty(home_outs)
    def_a, atk_a = team_penalty(away_outs)
    dr_delta = -def_h + def_a       # defesa do mandante fora -> dr cai; do visitante fora -> dr sobe
    gd_delta = -atk_h + atk_a       # ataque do mandante fora -> GD cai; do visitante fora -> GD sobe
    return dr_delta, gd_delta


def load_for_match(path, home, away, date) -> dict:
    """Lê o JSON de desfalques e devolve {'home':[...], 'away':[...]} do confronto (ou vazio)."""
    p = Path(path)
    if not p.exists():
        return {}
    data = json.loads(p.read_text(encoding="utf-8"))
    key = f"{date}|{home}|{away}"
    return data.get(key, {})


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Calcula os deltas (dr, GD) de desfalques de um confronto.")
    ap.add_argument("--json", required=True, help="caminho do desfalques.json")
    ap.add_argument("--home", required=True); ap.add_argument("--away", required=True)
    ap.add_argument("--date", required=True)
    args = ap.parse_args(argv)
    d = load_for_match(args.json, args.home, args.away, args.date)
    if not d:
        print("sem desfalques cadastrados p/ este confronto."); return 1
    ddr, dgd = match_deltas(d.get("home", []), d.get("away", []))
    print(f"desfalques {args.home} x {args.away} ({args.date}):  Δdr={ddr:+.0f} Elo   ΔGD={dgd:+.2f} gols")
    print("  (use em predict_match(..., desfalques=<dict home/away>))")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
