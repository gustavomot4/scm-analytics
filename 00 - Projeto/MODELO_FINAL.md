---
tags: [projeto, modelo, V1, contrato]
status: atual
tipo: especificacao
data: 2026-06-15
aliases: ["Modelo Final", "V1"]
---

# MODELO FINAL — o que a V1 calcula

Definição **decisiva** do que entra na primeira versão validável (a **V1 = baseline**), o que fica de fora, e por quê. Fonte da verdade matemática: [[camada1-planejamento-v5]] + [[camada1-apendice-formas-v5]]. Nada aqui é acurácia provada até o [[camada2-planejamento-v1|backtest]].

> **Princípio:** a V1 é o **motor mínimo que se sustenta sozinho**. Tudo que adiciona graus de liberdade fica fora até passar o **portão** (IC que não cruza zero). Sofisticação só entra medida.

## 1. Modelos DENTRO da V1

| Bloco | Papel | Fórmula-chave | Nota |
|---|---|---|---|
| [[Elo]] | diferença de força `dr` + `σ_R` | `W_e=1/(1+10^(−dr/400))`; K/G do contrato | espinha dorsal |
| [[Mando de campo]] | anfitrião / neutro | `H_host2026=+40` [a calibrar], 0 neutro, banda ±20 | passa pelo portão |
| [[Forma recente]] | ajuste curto prazo ao Elo | `ΔE_forma=15·(PPJ_pond−PPJ_esp)`, cap ±30 | ajustada a adversário |
| [[Desfalques direcionais]] | ausências por setor | tier −35/−15/−5; ataque corta λ_pró, defesa via dr | `setor` obrigatório |
| Estilo (shrinkage) | tendência de gols → `T_m` | `estilo=shrinkage(tend→1.0)` | parte de [[Forca ofensiva-defensiva]] |
| [[Incerteza e propagacao]] | `σ_dr` + Monte Carlo | `σ_dr=√(σ_R²+σ_R²+σ_aj²+σ_aj²+banda²)` | propaga V/E/D inteiro + banda |
| [[Poisson]] | matriz de placares | `M[i][j]=Pois(i;λ_A)·Pois(j;λ_B)`, 0..10 | over/BTTS/placares Poisson-condicionais |
| [[Ensemble]] | combina leituras | `0.45·Poisson+0.35·Elo+0.20·mercado` | clamp por leitura |
| [[Confianca]] | metadado | `score·g_rating`; `g_rating=1−min(0.6,σ_dr/σ_ref)` | não-crescente com σ_dr |

**Gols esperados na V1** (formas e placeholders em [[camada1-apendice-formas-v5]]):
```
dr  = R'_A − R'_B + mando
GD  = f(dr)            f_linear = θ·dr/100        θ=0.45  [a calibrar]
T_m = g(dr)·estilo     g_linear = T_base+κ·|dr|/100   T_base=2.6, κ=0.10  [a calibrar]
λ_A = (T_m+GD)/2 ;  λ_B = (T_m−GD)/2   (após desfalque ofensivo; piso λ_min)
```

## 2. Modelos FORA da V1 (e por quê)

| Bloco | Por que fica fora | Quando entra |
|---|---|---|
| [[Ajustes ambientais]] **altitude (E1) — ADOTADA (v0.2)** | passou o portão (+0,049, IC[+0,028,+0,070], 554 jogos) | **ativa**; gd_alt=0 fora de altitude |
| [[Ajustes ambientais]] calor (E3) + piso bola parada (E4) | candidatos | C2.5, **um a um atrás do portão** |
| Fuso/descanso como σ | efeito pequeno, fácil overfit; evidência é de lesão, não placar | C2.5, em `σ_ajuste` |
| Dixon-Coles + gerador [[Forca ofensiva-defensiva|ataque/defesa]] | precisa reconciliar as duas P(E); prior não-Elo p/ ser independente | C2.5 |
| [[xG preditivo]] como prior | StatsBomb só cobre 2018/2022/Euro (não as 48, não ao vivo) | C2.5, subconjunto |
| Afinação fina dos pesos do ensemble | overfit com <30 jogos | após ≥30 jogos |
| ML / boosting / bayes hierárquico / rating por jogador | matam auditabilidade ou garantem overfit | **nunca** (decisão de projeto) |

## 3. Pesos iniciais do ensemble [a calibrar]

| Leitura | com odds | sem odds |
|---|---|---|
| Poisson | 0.45 | 0.56 |
| Elo-direto (propagado) | 0.35 | 0.44 |
| Mercado | 0.20 | 0.00 |

Fixos até **≥30 jogos**; depois grid minimizando Brier, congelados por fase.

## 4. Outputs do sistema
- **P(V/E/D)** + **banda** por percentis 16/84 (cobertura medida na leitura Elo-direto).
- **λ_A, λ_B** (gols esperados).
- **Over/Under 2.5** e **ambos marcam (BTTS)** — Poisson-condicionais.
- **Top-5 placares** + "chance de NÃO ser o modal".
- **Confiança** (0–100, com rótulo alta/média/baixa).

## 5. Métricas de validação
- **Brier Score** (forma-soma, máx 2) — meta **< uniforme 0.667** com IC que não cruza o baseline, e **≤ Elo público**.
- **Log Loss** (uniforme = ln 3 ≈ 1.099) e **RPS** (ordinal).
- **Calibração** (reliability diagram) + **cobertura da banda** + **calibração de σ_dr isolada**.
- Detalhe e invariantes: [[camada2-planejamento-v1]] §4–§5.

## Relacionado
[[CLAUDE]] · [[TECH_STACK]] · [[BACKLOG]] · [[camada1-planejamento-v5]] · [[camada1-revisao-v5]] · [[camada2-baseline-plano-v1]]
