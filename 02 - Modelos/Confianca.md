---
tags: [modelo, camada1, confianca, V1]
status: V1
tipo: modelo
data: 2026-06-15
---

# Confiança
**Metadado, não probabilidade.** Diz quão confiável é a previsão. Entra na **V1**.

## Fórmula
```
score = 100·(0.35·separação + 0.15·consist_int + 0.15·corrob_ext + 0.20·dados + 0.15·robustez)
        · g_rating · (0.90 mata-mata) · (0.85 última rodada)
g_rating = 1 − min(0.6, σ_dr/σ_ref)
```
Rótulos: ≥65 alta · 40–64 média · <40 baixa.

## Declarado
`g_rating` cai quando `σ_dr` sobe (invariante: **confiança não-crescente com σ_dr**). Ponto, banda e confiança compartilham a **mesma** σ_dr ([[Incerteza e propagacao]]).

## Relacionado
[[Incerteza e propagacao]] · [[Ensemble]] · contrato [[camada1-planejamento-v5]] §14
