---
tags: [modelo, camada1, poisson, V1]
status: V1
tipo: modelo
data: 2026-06-15
---

# Poisson (gerador de placares)
Converte `λ_A, λ_B` (gols esperados) numa **matriz de placares** e dela extrai todas as saídas de gols. Entra na **V1**.

## Fórmula
```
P(X=k) = e^(−λ)·λ^k/k!
M[i][j] = Pois(i;λ_A)·Pois(j;λ_B),  i,j = 0..10  (resíduo na borda)
P(V)=Σ_{i>j} M ; P(E)=Σ_{i=j} M ; P(D)=Σ_{i<j} M
over 2.5 = 1 − Σ_{i+j≤2} M ; BTTS = (1−e^−λ_A)(1−e^−λ_B)
```

## Nota importante (A1 / [[camada1-revisao-v5]])
**over 2.5, BTTS e placares são Poisson-condicionais** — saem desta matriz, **não** do V/E/D do [[Ensemble]]. A diagonal soma o P(E) **da Poisson**, não o do ensemble.

## Fora da V1
**Dixon-Coles** (corrige 0×0/1×1) e o gerador [[Forca ofensiva-defensiva|ataque/defesa]] entram só na C2.5, atrás do portão.

## Relacionado
[[Forca ofensiva-defensiva]] · [[Ensemble]] · contrato [[camada1-planejamento-v5]] §3.2
