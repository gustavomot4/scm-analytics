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
| Estilo (shrinkage) | tendência de gols → `T_m` | `estilo=shrink(gols/jogo ÷ média)` | implementado, **rejeitado** pelo portão (D-23) |
| [[Incerteza e propagacao]] | `σ_dr` + Monte Carlo | `σ_dr=√(σ_R²+σ_R²+σ_aj²+σ_aj²+banda²)` | propaga V/E/D inteiro + banda |
| [[Poisson]] | matriz de placares | `M[i][j]=Pois(i;λ_A)·Pois(j;λ_B)`, 0..10 | over/BTTS/placares Poisson-condicionais |
| [[Ensemble]] | combina leituras | `0.45·Poisson+0.35·Elo+0.20·mercado` | clamp por leitura |
| [[Confianca]] | metadado | `score·g_rating`; `g_rating=1−min(0.6,σ_dr/σ_ref)` | não-crescente com σ_dr |

**Gols esperados na V1** (formas e placeholders em [[camada1-apendice-formas-v5]]):
```
dr  = R'_A − R'_B + mando
GD  = f(dr)            f_linear = θ·dr/100        θ=0.45  [a calibrar]
T_m = g(dr)·estilo     g_linear = T_base+κ·|dr|/100   T_base=2.6, κ=0.10  [a calibrar]
λ_A = (T_m+GD)/2 ;  λ_B = (T_m−GD)/2   (piso λ_min CONSERVA o total T_m — D-21/P01)
```

## 2. Modelos FORA da V1 (e por quê)

| Bloco | Por que fica fora | Quando entra |
|---|---|---|
| [[Ajustes ambientais]] **altitude (E1) — ADOTADA (v0.2)** | passou o portão (+0,049, IC[+0,028,+0,070], 554 jogos) | **ativa**; gd_alt=0 fora de altitude |
| [[Ajustes ambientais]] calor (E3) | **testado e REJEITADO** pelo portão (D-19) | fora |
| **Estilo (tendência de gols)** | implementado, **REJEITADO pelo portão** (corrige média do BTTS, sem skill/jogo) | `estilo.py` — D-23 |
| **Nível de gols (T_base)** | calibra o BTTS/over global (viés ~4pp medido) | `calibrate_total.py`, candidato — D-25 |
| [[Ajustes ambientais]] piso bola parada (E4) | candidato (StatsBomb) | C2.5, atrás do portão |
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
- **Mercados derivados do MESMO Poisson** (`predictor.markets`, sem novo modelo): **Over/Under 0.5–4.5**, **ambos marcam (BTTS)**, **total por time** (over 0.5/1.5), **não sofrer gol** (clean sheet), **dupla chance** (1X/12/X2), **handicap** (vencer por 2+) e **quem marca primeiro** (Poisson concorrente `λ_i/(λ_A+λ_B)`) + distribuição do total de gols. [[Decisoes tecnicas|D-21]].
- **Top-5 placares** + "chance de NÃO ser o modal".
- **Confiança** (0–100, rótulo alta/média/baixa) = `reliab(p_max)·maturidade(σ_R)`, calibrável contra o backtest ([[Confianca]], [[Decisoes tecnicas|D-20]]).
- *Fora por ora:* **tempo do gol** (intervalos quentes) exige o minuto dos gols (`goalscorers.csv`) — candidato futuro.

## 5. Métricas de validação
- **Brier Score** (forma-soma, máx 2) — meta **< uniforme 0.667** com IC que não cruza o baseline, e **≤ Elo público**.
- **Log Loss** (uniforme = ln 3 ≈ 1.099) e **RPS** (ordinal).
- **Calibração** (reliability diagram) + **cobertura da banda** + **calibração de σ_dr isolada**.
- Detalhe e invariantes: [[camada2-planejamento-v1]] §4–§5.

## Relacionado
[[CLAUDE]] · [[TECH_STACK]] · [[BACKLOG]] · [[camada1-planejamento-v5]] · [[camada1-revisao-v5]] · [[camada2-baseline-plano-v1]]

> **Atualização 2026-06-18 — Avanço de mata-mata (output novo).** Para jogos eliminatórios, `predictor.knockout_advance` entrega a **probabilidade de avançar** (não só de vencer no tempo normal): `avanço_A = P(V)+P(E)·(0,5+ε·sinal(dr))`, ε=0,03 [a calibrar] (contrato §3.2). É releitura do 1X2 do ensemble (como os mercados, D-21/[[Decisoes tecnicas|D-31]]). Ex.: Espanha 56,9% de vitória vira **70% de avanço** vs Alemanha. Na CLI: `predict_match --mata-mata`; na interface: toggle "Jogo eliminatório".

> **Atualização 2026-06-18 — Simulação do torneio (Camada 5).** `scm/simulate.py` roda o Monte Carlo da Copa inteira e entrega **a chance de título de cada seleção** (+ final/semi/passar do grupo), reaproveitando a Poisson do modelo e o `knockout_advance` (mata-mata). Sorteio em `dados/copa2026.json` (preencher — não inventado). `python -m scm.simulate` ou página `/simulacao`. Insight, não previsão validada — probabilidade, não certeza.

> **Atualização 2026-06-20 — v0.4 (`baseline-v0.4-ad`).** A **perna ataque/defesa não-Elo** (Maher/Poisson, prior de gols independente do `dr`) entrou no ensemble com **peso 0,30** após passar o portão (**+0,0039 Brier**, IC[+0,0028,+0,0051] em torneios) — é a diversidade REAL que faltava (as pernas Poisson/Elo eram corr 0,997). Com ela o modelo **supera o teto não-paramétrico do `dr`** (antes empatava). `predict_match` e `simulate` foram alinhados (porta da frente usa a perna AD; o Monte Carlo propaga σ). Rejeitados pelo portão: T_base, forma saturante, recalibração 1X2, σ-Glicko. Detalhe: [[Evolucao v0.4 - perna AD + sigma no torneio (2026-06-20)]].
