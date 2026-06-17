---
tags: [dev, backtest, resultados, baseline]
status: validado
tipo: resultados
data: 2026-06-17
---
# Backtest baseline (resultados) — v0.1

Primeiro backtest com **dados reais** (martj42, 49.423 jogos), **point-in-time**, com coeficientes **placeholder não-fitados** (θ=0,45; κ=0,10; curva de empate proxy). Portanto, calibração **fora de amostra** — não overfit.

## Todos os jogos (n=49.423)
- **Brier 0,538** (uniforme 0,667) · LogLoss 0,912 · RPS 0,183
- ganho vs uniforme **+0,129**, IC95 **[+0,125, +0,132]** → bate o uniforme com IC ✅
- **ECE 0,012**; reliability ~diagonal perfeita; banda dentro

## Torneios — WC/Euro/Copa América (n=2.241) — **recorte do aceite (C2 §2.2)**
- **Brier 0,562** (uniforme 0,667) · LogLoss 0,951 · RPS 0,194
- ganho vs uniforme **+0,104**, IC95 **[+0,089, +0,120]** → bate o uniforme com IC ✅
- **ECE 0,023**; banda dentro (obs 0,466 em [0,389, 0,557])
- reliability boa; leves desvios em faixas de n pequeno (0,8–0,9 superprediz, n=84)

## Veredito
Baseline **VALIDADO** nos invariantes centrais (bate uniforme com IC que não cruza zero; bem calibrado; banda com cobertura nominal) — inclusive no recorte de torneios, que é o mais difícil/comparável a 2026.

## Ressalvas / pendências
- **Não** comparado vs **Elo-público** (só vs uniforme).
- Benchmark eloratings: top-30 plausível, mas com artefatos (Iugoslávia extinta, Colômbia alta, sem recência) → comparar snapshot atual de ativos.
- **C2.5:** fatores ambientais (altitude/calor/bola parada) um a um **atrás do portão** (`compare()` — IC do ΔBrier não cruza zero); calibrar coeficientes num split de treino.

[[BACKLOG]] · [[Codigo (estrutura)]] · [[camada2-planejamento-v1]] · [[MODELO_FINAL]]

## Calibração (C2.5, passo 1) — NÃO adotada
Split treino/teste por torneios (cutoff 2018-01-01; treino n=1905, teste n=336), grid de 243 combos.
- Melhores coeficientes ≈ placeholders (θ=0,45 e draw_base=0,27 **não mudaram**; κ 0,10→0,15, T_base 2,6→2,4, w_poisson 0,56→0,65).
- Brier teste: placeholder 0,5857 → calibrado 0,5844. **Ganho +0,0013, IC95 [+0,0001, +0,0025]** — passa o portão por um fio, mas é **praticamente nulo**.
- **Decisão (ver D-17): manter v0.1.** Os placeholders da v5 estão confirmados como quase ótimos; não vale churn de versão por +0,0013. `calibrate.py` fica como ferramenta para re-checar quando a base crescer.


## Fatores ambientais (C2.5) — pelo portão
- **Altitude (E1): ADOTADA.** `python -m scm.altitude` → ganho de Brier **+0,0491**, IC95 [+0,028, +0,070] nos **554 jogos de altitude** (La Paz/Quito/Bogotá/CDMX), θ=0,5 (McSharry). Forte e robusto mesmo após o Elo. Modelo passa a **`baseline-v0.2-altitude`** (gd_alt ativo; =0 fora de altitude).
- **Calor (E3), bola parada (E4):** próximos, cada um atrás do portão.

- **Calor (E3): NÃO adotada.** Portão no Brier de **over/under** (jogos com WBGT>28°C via climatologia mensal Open-Meteo, n=15.378): ganho **+0,0007**, IC [−0,0008, +0,0022] (cruza zero). Proxy de climatologia é grosseiro e o efeito é sutil → o portão rejeita (D-19). Contraste honesto com a altitude (que passou forte): a disciplina distingue um efeito real de um marginal.
