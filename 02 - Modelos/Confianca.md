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

## Implementação na V1 (`predict_match` / interface)
A V1 operacional usa uma forma **enxuta e validável** do score, ancorada no backtest:
```
confiança   = 100 · reliab(p_max) · maturidade(σ_R)
maturidade  = 1 − min(0.5, σ_R_médio / σ_R_ref)        σ_R_ref = 200 [a calibrar — audit nota escala 0.5–1.0]
reliab(p_max) = taxa real de acerto do 'top pick' por faixa de p_max (curva isotônica do backtest)
```
- `reliab` vem de **`scm/calibrate_confidence.py`** (grava `meta['confidence_reliab']`); sem rodar, usa `p_max` — honesto, pois o reliability diagram mostrou o modelo calibrado mesmo nos extremos.
- **Substitui** o amortecimento antigo `g_rating = 1−min(0.6, σ_dr/σ_ref)`, que **travava** a confiança em ~68 mesmo num massacre (o `σ_ajuste` do jogo hipotético pisava o `σ_dr`). Agora: massacre entre maduros ≈ **76 (alta)**, jogo parelho ≈ 30 (baixa), rating provisório derruba (~47).
- Rótulos operacionais: **≥60 alta · 40–59 média · <40 baixa**. Decisão [[Decisoes tecnicas|D-20]].

## Relacionado
[[Incerteza e propagacao]] · [[Ensemble]] · contrato [[camada1-planejamento-v5]] §14
