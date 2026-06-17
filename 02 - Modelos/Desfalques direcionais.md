---
tags: [modelo, camada1, desfalques, V1]
status: V1
tipo: modelo
data: 2026-06-15
---

# Desfalques direcionais
Ausências ajustam λ **por setor** (corrige o sinal errado da porta simétrica). Entra na **V1**.

## Regra
```
tier 1 (estrela) ΔE=−35 · tier 2 (titular) −15 · tier 3 (rotação) −5   [a calibrar]
setor ∈ {defesa, goleiro}: entra via dr → baixa λ_pró e SOBE λ_contra
setor == ataque:           corta λ_pró direto (δ_ata), NÃO infla o rival
status "dúvida":           alimenta σ_ajuste ([[Incerteza e propagacao]])
```
Entrada por JSON manual (o detector automático é Camada 3). `setor` é **obrigatório**.

## Relacionado
[[Elo]] · [[Incerteza e propagacao]] · contrato [[camada1-planejamento-v5]] §3.6, §13
