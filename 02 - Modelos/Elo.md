---
tags: [modelo, camada1, elo, V1]
status: V1
tipo: modelo
data: 2026-06-15
---

# Elo Rating
**Espinha dorsal do sistema.** Cada seleção tem rating `R` **e erro-padrão `σ_R`**. Mede a *diferença de força* `dr` entre dois times. Entra na **V1**.

## Fórmula
```
R_novo = R_antigo + K·G·(W − W_e)
W_e = 1/(1 + 10^(−dr/400))      dr = R_A − R_B + mando
K = 60 Copa · 50 continental · 40 elim. · 30 Nations · 20 amistoso
G = 1 (≤1) · 1.5 (2) · (11+N)/8 (N≥3)
```
`H_hist`=100 em todo jogo não-neutro (construção histórica). Inicialização 1500; <30 jogos = provisório.

## Papel na V1
Gera `dr` → alimenta [[Forca ofensiva-defensiva|gols esperados]] e a leitura Elo-direto do [[Ensemble]]. A incerteza `σ_R` é insumo de [[Incerteza e propagacao]].

## Parâmetros [a calibrar]
`H_hist`, `H_host2026` (ver [[Mando de campo]]), `σ_R` por seleção — todos saem do [[camada2-planejamento-v1|backtest]].

## Relacionado
[[Mando de campo]] · [[Forma recente]] · [[Incerteza e propagacao]] · [[Ensemble]] · contrato [[camada1-planejamento-v5]] §3.1
