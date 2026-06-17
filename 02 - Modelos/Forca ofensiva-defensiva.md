---
tags: [modelo, camada1, ataque-defesa, fora-V1]
status: fora-V1
tipo: modelo
data: 2026-06-15
---

# Força ofensiva/defensiva (Ataque-Defesa)
Estima o **estilo** (tendência de gols) e, no upgrade, λ **direcional** via Dixon-Coles.

## Fórmula
```
estilo_T = shrinkage(tendência_gols_T → 1.0)         # usado na V1 dentro de T_m
ln λ = μ + ATA + DEF + γ·mando                        # upgrade Dixon-Coles (FORA da V1)
```

## Status
O **`estilo` (shrinkage)** entra na V1 dentro de `T_m`. O **gerador ATA/DEF + Dixon-Coles** fica **fora da V1** (C2.5): se for membro do [[Ensemble]], o prior é de **gols/xG, não Elo** (senão a diversidade é fictícia).

## Relacionado
[[Poisson]] · [[Ensemble]] · [[xG preditivo]] · contrato [[camada1-planejamento-v5]] §3.4, §11.2
