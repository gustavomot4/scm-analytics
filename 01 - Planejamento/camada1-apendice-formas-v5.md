---
tags: [camada1, apendice, atual]
status: atual
tipo: apendice
data: 2026-06-15
aliases: ["Apendice formas v5"]
---

# Camada 1 — Apêndice à v5: formas funcionais de λ e da curva de empate (autocontenção)
**Projeto:** Sistema de previsão de partidas — Copa do Mundo 2026
**Anexa-se a:** [[camada1-planejamento-v5]] (v5.0) · **Origem:** achado B1 de [[camada1-revisao-v5]]
**Data:** 2026-06-15 · **Status:** documentação (sem código) · **Custo-alvo:** R$ 0

> **Este apêndice NÃO altera nenhuma fórmula** — logo **não há bump de versão**: o contrato segue **v5.0**. Ele apenas **restabelece, no escopo da v5**, as famílias funcionais de `f(dr)` (saldo), `g(dr)` (total) e da curva de empate restrita **C1**, que existem na v4 (§8, §9, §11.1) mas que a v5.md só referenciava ("por backtest"). Objetivo: tornar a v5 **autocontida** (um leitor da v5 + este apêndice tem tudo para reproduzir as execuções), separando o que é **forma fixa** do que é **coeficiente [a calibrar]**. Todos os números abaixo foram **verificados em código** (ver [[camada1-revisao-v5]] §1, V8) e reproduzem a tabela da v4 §8 **e** a execução IRN×NZL (v5.0).

---

## 1. `f(dr)` — saldo de gols esperado (GD)

**Papel no pipeline (v5 §8, passo 3):** `GD = f(dr) + GD_alt`, onde `GD_alt` é o termo de altitude (v5 §3.13).

**Família (v4 §8, escolha por backtest, monótona em dr, ímpar — `f(−dr)=−f(dr)`):**
```
f_linear(dr)  = θ · dr/100                     # candidato 1 (placeholder atual das execuções)
f_sat(dr)     = GD_max · tanh(dr / dr_escala)   # candidato 2 (saturante; controla o tail)
```

**Coeficiente-placeholder atual (execuções manuais até o backtest):** `θ = 0.45` gol por 100 Elo.
Verificado: reproduz a tabela v4 §8 (GD=1.35/2.70/4.05 em dr=300/600/900) e a execução IRN×NZL (`GD = 0.45·152/100 = 0.684 ≈ 0.68`).

**Por que a forma importa (V8):** com `f_linear` e `g_linear`, `λ_B = (T_m−GD)/2` fica **negativo** em dr≥900 (−0.27 em 900; −0.62 em 1100), hoje só mascarado pelo `λ_min`. A forma **saturante** mantém λ_B>0 sem clamp. **Decisão é do backtest** (Brier/RPS com IC, point-in-time, extrapolação cautelosa além do suporte |dr|≲500).

---

## 2. `g(dr)` — total de gols esperado (T_m)

**Papel no pipeline (v5 §8, passo 4):** `T_m = g(dr) · estilo_A · estilo_B · (1 − κ_heat·excesso_WBGT)`.
O termo de calor `(1−κ_heat·…)` é v5 (E3); `g(dr)·estilo` é herdado da v4.

**Família (v4 §8/§11.1, escolha por backtest, função de `|dr|` — total cresce com o desequilíbrio):**
```
g_linear(dr)  = T_base + κ · |dr|/100                 # candidato 1 (placeholder atual)
g_concava(dr) = T_base + κ · raiz/log de |dr|          # candidato 2
g_satsuave(dr)= T_base + (T_top − T_base)·(1 − e^(−|dr|/dr_e))   # candidato 3 (saturação suave)
```

**Coeficientes-placeholder atuais:** `T_base = 2.6` (Copas: 2018 = 2.64; 2022 = 2.69 — recalibrar com cautela), `κ = 0.10` gol por 100 Elo.
Verificado: reproduz a tabela v4 §8 (T_m=2.90/3.20/3.50 em dr=300/600/900) e a execução IRN×NZL (`T_m = (2.6+0.10·1.52)·0.90·0.90·1.0 = 2.23`).

**Acoplamento (v4 D2):** GD e T_m são **acopladas** em λ (`λ_A0=(T_m+GD)/2`, `λ_B0=(T_m−GD)/2`). **Não libertar uma e impor a outra** — escolher as duas formas **juntas** no backtest. Linear e saturação coincidem onde há dados (|dr|≲300) e divergem no tail esparso.

---

## 3. Curva de empate restrita **C1** (leitura Elo-direto)

**Papel:** transforma `dr` (e sua incerteza) na leitura V/E/D "Elo-direto", garantindo **P(V), P(D) ∈ [0,1] por construção** (conquista da v3). É a peça que a v5.md mais deixava implícita.

**Construção (v4 §9 e §3.12) — esta é a forma do contrato:**
```
W_e(dr)  = 1 / (1 + 10^(−dr/400))                       # expectativa de pontuação Elo
P_E(dr)  = curva EMPÍRICA do martj42 por faixa de |dr|   # ~0.26 em |dr|<50  →  ~0.15 em |dr|>300 (cai além)
# propagação e cap POR AMOSTRA (S=10^4), dr_s ~ Normal(dr0, σ_dr):
pe_s = min( P_E(dr_s),  2·min(we_s, 1−we_s) − ε )        # cap garante coerência em CADA amostra
pv_s = we_s − pe_s/2
pd_s = 1 − pv_s − pe_s
P_elo(V/E/D) = média_s(pv_s, pe_s, pd_s)                 # leitura inteira propagada (v4 D1)
banda(x)     = [percentil_16, percentil_84] de {x_s}     # MESMA amostra do ponto
```

**O que está fixo vs. [a calibrar]:**
- **Fixo (forma):** `W_e` logística; o **cap** `2·min(W_e,1−W_e)−ε` (é ele que impede P(D)<0 em |dr| alto); a decomposição `pv=we−pe/2`, `pd=1−pv−pe`; a propagação por amostra e a banda 16/84.
- **[a calibrar]:** a **tabela empírica `P_E(dr)`** (congelar do martj42 por faixa de |dr|, point-in-time) e `ε` (folga pequena do cap).

**Aviso de método (revisao-v5 §1, V6):** na auditoria usei um *proxy* `P(E)=2k·min(W_e,1−W_e)`, k≈0.371, que reproduz a leitura a 3 casas. **Esse proxy não é a C1** — a C1 é **empírica em dr** com cap, não função fechada de W_e. O proxy só serviu para confirmar direção/magnitude da propagação. **Não implementar o proxy no lugar da curva empírica.**

**E[W_e] propagado (v4 §3.12, MC reconferido) — referência de sanidade:**

| dr0 | σ_dr=0 | 75 | 150 | 250 |
|---:|---:|---:|---:|---:|
| 150 | 0.703 | 0.696 | 0.679 | 0.651 |
| 300 | 0.849 | 0.841 | 0.819 | 0.781 |
| 500 | 0.947 | 0.942 | 0.929 | 0.898 |

(A propagação **encolhe** o favorito — Jensen: W_e é côncava para dr>0. Confirmado em código na revisao-v5.)

---

## 4. Resumo: forma fixa × coeficiente [a calibrar]

| Bloco | Forma (fixa, restabelecida aqui) | Coeficientes [a calibrar] | Placeholder atual (verificado) |
|---|---|---|---|
| `f(dr)` saldo | linear `θ·dr/100` **ou** `tanh` | θ; (GD_max, dr_escala se saturante) | θ=0.45 |
| `g(dr)` total | linear `T_base+κ·\|dr\|/100`, côncava ou sat. suave | T_base, κ | T_base=2.6, κ=0.10 |
| C1 empate | logística + cap `2·min(W_e,1−W_e)−ε` + decomposição | tabela `P_E(dr)`, ε | proxy só p/ auditoria |
| altitude (v5) | `θ_alt·(pen_B−pen_A)/1000`, `pen=max(0,Δalt)` | θ_alt (~0.5 CONMEBOL) | θ_alt=0.5 |
| calor (v5) | `T_m·(1−κ_heat·excesso_WBGT)` | κ_heat | estimado, cap pequeno |
| piso bola parada (v5) | `λ_az = max(λ_az, piso)` | piso_setpiece | estimado por propensão |

---
*Apêndice à v5.0 — sem código, sem mudança de fórmula, sem bump de versão. Restabelece no escopo da v5 as formas de f/g/C1 que viviam na v4, separando forma fixa de coeficiente [a calibrar]. Verificado em código (revisao-v5 §1). As escolhas de forma e todos os coeficientes seguem atrás do portão de backtest. Probabilidades, nunca certezas.*
