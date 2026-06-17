---
tags: [modelo, camada1, forma, V1]
status: V1
tipo: modelo
data: 2026-06-15
---

# Forma recente
Ajuste de curto prazo ao [[Elo]], **ajustado a adversário**. Entra na **V1**.

## Fórmula
```
w_i = 0.9^(meses)·(1 oficial · 0.5 amistoso)
PPJ_pond = Σ w_i·pontos_i / Σ w_i
ΔE_forma = 15·(PPJ_pond − PPJ_esperado)     cap ±30 Elo
```
A **dispersão da forma** na janela alimenta `σ_ajuste` ([[Incerteza e propagacao]]).

## Parâmetros [a calibrar]
Peso/cap; `PPJ_esperado` exige a curva de empate (ver [[Ensemble]]). No backtest: Elo **point-in-time** (anti look-ahead).

## Relacionado
[[Elo]] · [[Incerteza e propagacao]] · contrato [[camada1-planejamento-v5]] §3.3
