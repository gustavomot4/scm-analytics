---
tags: [modelo, camada1, ambiental, fora-V1]
status: fora-V1
tipo: modelo
data: 2026-06-15
---

# Ajustes ambientais (altitude · calor · bola parada)
Fatores com **evidência publicada + dado gratuito**. **Fora da V1** — entram na C2.5 **um a um, atrás do portão** (IC que não cruza zero).

## Termos
```
Altitude (E1):  GD += θ_alt·(pen_B − pen_A)/1000 ;  pen=max(0, alt_sede−alt_casa)
                θ_alt≈0.5 gol/1000m ([[McSharry 2007 (altitude)]])
Calor (E3):     T_m *= (1 − κ_heat·excesso_WBGT)    # reduz o total
Bola parada (E4): λ_azarão = max(λ_azarão, piso_setpiece)   # corrige BTTS do azarão
```

## Cuidados (B2/B3/A3 / [[camada1-revisao-v5]])
- **Altitude × mando**: em jogo do México na altitude há **dupla contagem** com [[Mando de campo]] → calibrar juntos.
- Penalidade de altitude **assimétrica** é premissa além de McSharry.
- **Piso × calor** mexem no total em direções opostas → calibrar juntos.

## Fuso/descanso (E5/E6)
Entram como **incerteza** ([[Incerteza e propagacao]]), **não** como placar.

## Relacionado
[[McSharry 2007 (altitude)]] · [[Bola parada (Opta)]] · [[Mando de campo]] · contrato [[camada1-planejamento-v5]] §3.11, §3.13
