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
