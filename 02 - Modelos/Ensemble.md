---
tags: [modelo, camada1, ensemble, V1]
status: V1
tipo: modelo
data: 2026-06-15
---

# Ensemble
Combina leituras de V/E/D. Entra na **V1** com três pernas.

## Pesos iniciais [a calibrar]
| Leitura | c/ odds | s/ odds |
|---|---|---|
| Poisson | 0.45 | 0.56 |
| Elo-direto (propagado) | 0.35 | 0.44 |
| Mercado (odds/[[Fontes gratuitas|Kalshi]]) | 0.20 | 0.00 |

## Regras
- **Clamp por leitura** [0.02, 0.96] e renormaliza **antes** do pool; clamp final idem.
- Leitura **Elo-direto entra inteira e propagada** ([[Incerteza e propagacao]]); a **curva de empate restrita C1** garante P(V),P(D) ∈ [0,1] (forma em [[camada1-apendice-formas-v5]]).
- Banda do ensemble **sub-cobre** (perna de mercado não se move com dr) → cobertura medida na leitura Elo-direto (A2).
- Pesos finos só com **≥30 jogos** (senão é overfit).

## Relacionado
[[Poisson]] · [[Elo]] · [[Incerteza e propagacao]] · [[camada1-apendice-formas-v5]] · contrato [[camada1-planejamento-v5]] §3.8, §9
