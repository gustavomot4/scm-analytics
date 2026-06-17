---
tags: [modelo, camada1, incerteza, sigma_dr, V1]
status: V1
tipo: modelo
data: 2026-06-15
---

# Incerteza e propagação (σ_dr)
Trata o input como **distribuição**, não ponto. É a conquista central da v3/v4. Entra na **V1**.

## Fórmula
```
σ_ajuste(T) = sqrt( (a·Σ|ΔE| em dúvida)² + (b·n_meio_tier)² + (c·desvio_forma)²
                  + (d·Δfuso_leste)² + (e·descanso_curto)² )      [a–e a calibrar]
σ_dr = sqrt( σ_R(A)² + σ_R(B)² + σ_ajuste(A)² + σ_ajuste(B)² + banda_mando² )
# RSS — APROXIMAÇÃO (ignora covariância intra-confederação)
```
**Propagação (Monte Carlo):** amostrar `dr ~ N(dr, σ_dr)`, passar a leitura V/E/D inteira, tirar média; **banda** = percentis 16/84 da mesma amostra. Jensen: a propagação **encolhe o favorito** rumo a 0,5.

## Declarado (B4 / [[camada1-revisao-v5]])
Ponto, banda e [[Confianca|confiança]] usam a **mesma** σ_dr — não são três sinais independentes. O backtest calibra σ_dr **isoladamente** (cobertura da banda).

## Relacionado
[[Elo]] · [[Forma recente]] · [[Desfalques direcionais]] · [[Ensemble]] · [[Confianca]] · contrato [[camada1-planejamento-v5]] §3.12
