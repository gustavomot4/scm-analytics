---
tags: [camada2, backtest, design]
status: atual
tipo: planejamento
data: 2026-06-15
aliases: ["Backtest (design)"]
---

# Camada 2 — Planejamento: backtest histórico (metodologia, métricas, invariantes)
**Projeto:** Sistema de previsão de partidas — Copa do Mundo 2026
**Camada:** 2 (coleta/normalização + **backtest histórico**) · **Consome:** [[camada1-planejamento-v5]] (v5.0) + [[camada1-apendice-formas-v5]]
**Data:** 2026-06-15 · **Status:** **design (sem código de sistema)** · **Custo-alvo:** R$ 0
**Versão:** v1 (primeira especificação da C2). Pseudocódigo abaixo é **ilustrativo**, não implementação.

> A Camada 2 é **o único critério de aceite real** do projeto. Até aqui, tudo é coerência — não acurácia. Este documento **desenha** (não implementa) como medir a v5 contra a história, de forma **point-in-time** e **honesta sobre overfit**. Princípio inegociável: o contrato v5 tem **muitos parâmetros [a calibrar]** (θ, κ, T_base, θ_alt, κ_heat, piso_setpiece, banda_mando, σ_R, σ_ajuste, σ_ref, a–e, pesos do ensemble, tabela empírica de empate, formas de GD/T_m). **Ajustar todos e reportar Brier no mesmo conjunto é autoengano** — o backtest precisa de separação treino/teste e de um **portão por termo**. Convenções herdadas (V/E/D, λ, dr, σ_dr, Brier, RPS, **[a calibrar]**). Nada lê a internet no cálculo (snapshot local).

---

## 0. Objetivo e definição de "passar"

Medir se o pipeline v5 **congelado** prevê melhor que baselines triviais, **fora da amostra**, sem inventar sinal. "Passar" = cumprir os **invariantes de aceite** (§5) num conjunto histórico congelado e point-in-time. Não-passar é um resultado **válido e esperado** para parte dos termos da v5 — o portão (§6) existe justamente para **remover** o que não se sustenta.

Três coisas que o backtest **não** é: (i) prova de lucro de aposta (Brier ~0.60 não é edge); (ii) validação de calibração para 2026 (formato de 48 seleções é inédito — §7); (iii) licença para adicionar variáveis até o Brier cair (isso é overfit — §6).

---

## 1. O problema central: contrato com muitos `[a calibrar]`

Não se backtesta um modelo cujos coeficientes e formas saem do **mesmo** conjunto que mede o erro. Solução em três camadas de disciplina:

1. **Point-in-time (anti look-ahead).** Toda entrada de um jogo na data `t` usa **só** dados com carimbo `< t`: Elo reconstruído jogo-a-jogo; forma só com partidas anteriores; coeficientes fitados apenas em jogos `< t`. Isto força, na prática, um esquema **walk-forward** (§3).
2. **Separação treino/validação/teste por torneio.** Coeficientes `[a calibrar]` são fitados em torneios passados (treino), escolhidos por desempenho em torneios intermediários (validação), e medidos **uma única vez** num torneio de teste **intocado** (§3).
3. **Portão por termo, não por modelo.** Cada termo novo (altitude, calor, piso, banda de mando, d/e de σ) entra **um de cada vez** sobre um baseline congelado e **só sobrevive** se melhorar Brier/RPS com **IC que não cruza zero** (§6). Sem isso, sai.

A v5 (§16) já diz "cada variável multiplica os graus de liberdade"; aqui isso vira **procedimento**, não advertência.

---

## 2. Dados: fontes, schema e ingestão

### 2.1 Fontes (todas gratuitas; verificadas no repo em 2026-06-15, v4 §6)
| Dado | Fonte | Papel no backtest | Limite honesto |
|---|---|---|---|
| Resultados 1872–2026 (torneio, neutro, casa/fora) | **martj42/international_results** | base do Elo + V/E/D realizado | atualização por PR (irrelevante p/ histórico) |
| Calendário (descanso, viagem) | **fixturedownload** | dias de descanso, Δfuso (E5/E6) | só jogos |
| xG + tipo de jogada (bola parada) | **StatsBomb Open Data** | prior de estilo (F4) + piso de bola parada (E4) | **só 2018/2022, Euro, WWC — SEM 2014 nem Copa América**; não-comercial |
| Elevação de sede + clima histórico | **Open-Meteo (Elevation + Archive desde 1940)** | altitude (E1) e WBGT aprox. (E3) | uso não-comercial |
| Elevação/coords de estádio + data de nomeação do técnico | **Wikidata** | altitude "de casa", regime → σ_R | semiestruturado |
| Elo benchmark | **eloratings.net / international-football.net** | sanidade do Elo próprio (±25 top-30) | SPA/sem API → snapshot manual 1× |
| Odds 1X2 de fechamento (histórico) | **arquivo a validar** | comparador de mercado | **NÃO confirmado gratuito/estruturado p/ torneios de seleção** — ver §7 |

**Declaração honesta de lacuna (mercado):** Kalshi/Polymarket **não têm histórico** para 2014/18/22, e o repo (v4 §6) já registra que **não há API gratuita garantida de odds de Copa**. Logo o comparador primário do backtest é o **Elo público** (sempre reconstruível); o comparador de **mercado** é **oportunista** — só onde existir arquivo de odds de fechamento, e marcado "a validar". **Não inventar** uma série de odds histórica.

### 2.2 Conjunto de backtest (congelado antes de qualquer fit)
- **Copas:** 2014, 2018, 2022 · **Euros:** 2016, 2020, 2024 · **Copas América:** 2015, 2016, 2019, 2021, 2024.
- Alvo ~**400+ jogos** de seleção em torneio (v5 §15). Eliminatórias/amistosos **alimentam o Elo point-in-time**, mas as **métricas** são medidas só nos jogos de torneio (ambiente comparável a 2026).
- **Subconjuntos por disponibilidade de dado** (importa para o tail e para os termos novos):
  - Altitude/calor: **todos** (Open-Meteo cobre 1940+).
  - xG/bola parada: **só** torneios cobertos pelo StatsBomb (2018/2022 + Euros + WWC). Termos E4/F4 são testados **apenas** nesse subconjunto → amostra menor → IC mais largo → portão mais difícil (correto).

### 2.3 Schema SQLite (normalização — desenho, não DDL final)
```
teams(team_id, fifa_code, name, confederation, home_altitude_m)
venues(venue_id, name, city, country, lat, lon, elevation_m, covered_bool)
matches(match_id, date_utc, tournament, stage, neutral_bool,
        home_team_id, away_team_id, home_goals, away_goals, kickoff_utc, venue_id)
ratings_pit(team_id, asof_date, elo, sigma_R, n_games_eff)      # snapshot point-in-time
form_pit(team_id, asof_date, ppj_pond, desvio_forma)            # janela 10, só jogos < asof
context(match_id, rest_days_home, rest_days_away, dfuso_home, dfuso_away, wbgt_est)
statsbomb(match_id, team_id, xg, setpiece_goal_share)           # subconjunto coberto
odds_hist(match_id, p_home, p_draw, p_away, source)             # OPCIONAL, 'a validar'
predictions(match_id, versao_modelo, p_v, p_e, p_d, banda_pv_lo, banda_pv_hi,
            lambda_a, lambda_b, sigma_dr, confianca, hash_inputs)   # saída do pipeline congelado
```
A migração do `registro-previsoes.csv` (esquema-alvo v5: +`sigma_dr`,`banda_pv`,`hash_inputs`,`preco_mercado_previsao`) entra aqui — **append-only, sem reescrever linhas antigas**; linhas pré-v5 ficam marcadas pela `versao_modelo` e **não se misturam** numa métrica (v5 §15).

---

## 3. Protocolo de validação (o coração)

### 3.1 Walk-forward / expanding window (point-in-time)
O Elo é intrinsecamente temporal — só faz sentido reconstruí-lo para frente. Para cada jogo `m` na data `t(m)`:
```
# ILUSTRATIVO (não implementação)
estado_elo = Elo inicial (1500, H_hist em todo jogo não-neutro)
ordenar todos os jogos por data
para cada jogo m em ordem cronológica:
    entradas(m) = features construídas SÓ com jogos < t(m)      # Elo, forma, σ_R, descanso...
    prever P(V/E/D)(m) com o pipeline CONGELADO e os coeficientes vigentes
    registrar predição (imutável)
    atualizar estado_elo com o resultado real de m              # só DEPOIS de prever
```
Isto garante que **nenhuma predição vê o próprio resultado nem o futuro**. É a definição operacional de "point-in-time" do contrato.

### 3.2 Treino / validação / teste por torneio (para os `[a calibrar]`)
O walk-forward resolve o Elo, mas os **coeficientes** (θ, κ, formas, pesos…) ainda precisam de out-of-sample próprio:
```
TREINO     : torneios mais antigos                  -> fita coeficientes (regressão/grid)
VALIDAÇÃO  : torneios intermediários                -> escolhe formas (linear vs saturante) e o gate por termo
TESTE      : o torneio mais recente coberto (ex.: WC 2022)  -> TOCA UMA VEZ SÓ, no fim
```
- O conjunto de **teste é intocável** até o pipeline e todos os coeficientes estarem congelados. Medir nele mais de uma vez **queima** o teste (vira validação).
- Para usar melhor a amostra pequena, a **escolha de forma** (GD/T_m linear vs saturante; pesos) pode usar **validação cruzada por torneio** (deixar-um-torneio-de-fora) **dentro** do treino+validação — nunca tocando o teste.

### 3.3 Ordem de calibração (do contrato v5 §17–§18; cada passo passa pelo portão §6)
1. **Baseline congelado:** Elo + `H_hist` + σ_R → `GD=f(dr)`, `T_m=g(dr)·estilo` → Poisson → leitura Elo-direto propagada. **Mando rebaixado (E2)** e **formas de GD/T_m** decididos aqui (juntos — são acoplados; v4 D2 / apêndice §2). **Milestone:** Brier < 0.62 (IC) e < Elo público.
2. **Ambientais que mexem em λ — JUNTOS:** altitude (E1) **+** calor (E3). Agem em direções opostas no tail (§4 lacunas) → calibrar no mesmo passo. **B2:** θ_alt e `H_host2026` **identificados separadamente** (os jogos do México na altitude são o único cruzamento que os separa; se a amostra não separar, declarar confusão residual e manter banda larga).
3. **Piso de bola parada (E4)** — só no subconjunto StatsBomb; validar contra o gap BTTS observado; calibrar **junto** com κ_heat (A3 — ambos mexem no total do azarão).
4. **Fuso (E5) e descanso (E6) em σ_ajuste**, não em λ — corrigir métrica (km → Δfuso com sinal); testar se a **cobertura da banda** melhora, não o ponto.
5. **xG (F4)** como prior de estilo + régua de calibração (subconjunto StatsBomb).
6. **Pesos do ensemble** — **só com ≥30 jogos** por configuração; grid minimizando Brier, congelados por fase. `P_ad` (prior não-Elo) só se o fork D5 for acionado.

Cada passo **re-backtesta** e só mantém o termo se passar o portão. A v5 não muda de fórmula por isto — muda o **valor** dos `[a calibrar]` e a **decisão de manter/remover** cada termo.

---

## 4. Métricas (convenção: Brier forma-soma, máx 2 — v4 §15)
```
Brier   = (1/N) Σ_m Σ_{x∈{V,E,D}} (P_x(m) − o_x(m))²       # o = one-hot do resultado
LogLoss = −(1/N) Σ_m ln P_resultado(m)                      # uniforme = ln 3 ≈ 1.099
RPS     = (1/2)[ (P_V−O_V)² + ((P_V+P_E)−(O_V+O_E))² ]      # ordinal — reportar as três
```
**Baselines:** uniforme = **0.667**; Elo público (eloratings.net reconstruído) ≈ **0.55–0.60**; mercado (onde houver odds) ≈ 0.55–0.60. **Meta:** Brier < uniforme **com IC que não cruza o baseline**, e **≈ Elo público** (não pior).

**Calibração (mais importante que acerto):** diagrama de confiabilidade por faixas (≥20 jogos/faixa) — "dos jogos a 60%, ~60% aconteceram?". **Cobertura da banda:** dos jogos com banda [lo,hi], o realizado cai dentro ~68% das vezes (banda 16/84).

---

## 5. Invariantes de aceite (checklist congelado — inclui A2/B2/B4 da revisao-v5)
O backtest **só é aceito** se TODOS valerem no conjunto de teste:

1. **Brier < uniforme**, IC bootstrap (B=10⁴) **não cruza** 0.667; e **≤ Elo público** (não significativamente pior).
2. **P(V), P(D) ∈ [0,1]** em todo |dr| observado (a construção C1 garante; medir no fit real).
3. **Confiança não-crescente com σ_dr** — `g_rating` monótono decrescente; checar correlação ≤ 0 e ausência de inversões por faixa.
4. **Banda com cobertura nominal — MEDIDA NA LEITURA ELO-DIRETO (A2)**, não na do ensemble (a perna de mercado entra com variância propagada zero e faz a banda do ensemble **sub-cobrir** por construção; medir nela daria falso "fail").
5. **Calibração de σ_dr isolada (B4):** a variância empírica dos erros por faixa (nº de jogos / volatilidade de escalação) bate com σ_R/σ_ajuste — senão a "humildade" é teatro (ponto+banda+confiança são a **mesma** σ_dr, não três sinais).
6. **Identificabilidade altitude×mando (B2):** θ_alt e `H_host2026` estimados com sinais separáveis; se confundidos, reportar e **não** creditar duas vezes.
7. **Portão por termo:** cada termo ambiental (E1–E4) e cada d/e de σ **só permanece** se melhorar Brier/RPS com **IC que não cruza zero**; o que não passar é **removido do contrato vigente** (gera nota, possivelmente v6).

---

## 6. O portão estatístico, operacionalizado
```
# ILUSTRATIVO. Para um termo candidato (ex.: calor):
Brier_sem = backtest(pipeline SEM o termo)          # baseline congelado
Brier_com = backtest(pipeline COM o termo)
Δ_m       = brier_m(sem) − brier_m(com)             # por jogo, pareado
# bootstrap pareado B=10000 sobre {Δ_m}: IC95 de E[Δ]
manter_termo  =  IC95(E[Δ]) inteiro > 0             # melhora E NÃO cruza zero
```
- **Pareado por jogo** (mesmo conjunto, com e sem o termo) — controla a variância comum, é o teste certo para um termo pequeno.
- **Teste vs mercado** (onde houver odds): `diff_m = brier_modelo − brier_mercado`, IC que não cruze 0.

**Controle de comparações múltiplas (▲C2 — não estava explícito no contrato).** Testar muitos termos candidatos, cada um exigindo "IC que não cruza zero", **infla o falso-positivo**. O portão "IC95 inteiro acima de zero" é **unicaudal a 2,5%** por termo (sob efeito nulo); com ~6 termos a chance de ≥1 falso "passou" é **1−0,975⁶ ≈ 14%** (e ~26% se o portão for lido como bicaudal a 5% — `0 fora do IC95`). Verificado em código. Disciplina:
- **Pré-registrar** a ordem e o número de termos (§3.3) **antes** de ver o teste — nada de pescar.
- Aplicar **correção** (Bonferroni/Holm) ou **elevar o nível** do portão (ex.: IC99) quando o número de candidatos cresce.
- Preferir **poucos termos com evidência forte** (a v5 já filtrou por evidência publicada) a muitos fracos.
Isto é o antídoto operacional ao maior risco do projeto (v5 §16: graus de liberdade vs amostra minúscula).

---

## 7. Riscos e limitações do próprio backtest (declarar, não esconder)
- **Amostra pequena no tail.** Jogos com |dr|>500 e minnows ruidosos são poucos → ICs largos; formas de GD/T_m no tail ficam **mal determinadas** (v4 §16). Extrapolação cautelosa, σ_dr alargado fora do suporte.
- **Mercado histórico incompleto.** Sem série gratuita garantida de odds 1X2 de fechamento para torneios de seleção (§2.1) → o comparador de mercado é **parcial**; o comparador primário é o **Elo público**. Não inventar odds.
- **StatsBomb não cobre 2014 nem Copa América.** E4/F4 (bola parada, xG) testáveis só num **subconjunto** → menos poder; honesto reportar "termo validado apenas em 2018/2022/Euro".
- **Covariância intra-confederação.** σ_dr via RSS ignora a correlação dos erros de rating de times que jogam muito entre si (v4 D6/A9) — só corrigível com a matriz de covariância do ajuste de Elo; até lá, aproximação declarada.
- **Reconciliação das duas P(E)** (matriz Poisson vs curva empírica) segue **aberta** até a Dixon-Coles entrar (C2.5) — a DC sobe 0×0/1×1 e muda o P(E) da matriz (v5 §3.2; e a nota A1: mercados derivados são Poisson-condicionais).
- **Representatividade para 2026.** Formato de 48 seleções, sedes em 3 países, calor/altitude específicos — o backtest valida o **motor**, não garante calibração para um torneio inédito (v5 §16). A confiança da interface deve dizer isso.
- **Múltiplas comparações** (§6) e **eco do mercado** (peso ≤0.20) seguem como riscos estruturais.

---

## 8. Entregáveis da Camada 2
1. **SQLite normalizado** (point-in-time) + script de ingestão **reprodutível** (snapshot local, sem rede no cálculo).
2. **Relatório de backtest por `versao_modelo`:** Brier/RPS/LogLoss com IC, vs uniforme/Elo/mercado; reliability diagrams; cobertura da banda.
3. **Tabela do portão:** para cada termo candidato (E1–E6, formas, pesos), ΔBrier pareado + IC + decisão **manter/remover**.
4. **Coeficientes calibrados e congelados** (θ, κ, T_base, θ_alt, κ_heat, piso_setpiece, banda_mando, σ_R/σ_ajuste/σ_ref, pesos, tabela `P_E(dr)`) → alimentam a Camada 4.
5. **Migração do CSV** para o esquema-alvo v5 (append-only).

---

## 9. Roadmap C2 → C2.5
- **C2:** ingestão + Elo histórico (H_hist + σ_R) + **baseline congelado** medido (passo 1 da §3.3). *Desbloqueia tudo.*
- **C2.5:** formas de GD/T_m + altitude + calor **juntos**; piso de bola parada; **ataque/defesa + Dixon-Coles** (resolver o fork D5, reconciliar as duas P(E)); re-backtest.
- **C3+ (fora desta camada):** desfalques/descanso JSON → σ; insights (Monte Carlo + cenários); interface. Dependências: C4 exige C2; C5 exige C4.

**Milestone de aceite (resumo §5):** backtest congelado e point-in-time com Brier < uniforme (IC que não cruza o baseline), ≈ Elo público, P(V),P(D) ∈ [0,1], confiança não-crescente com σ_dr, **banda com cobertura nominal na leitura Elo-direto**, **σ_dr calibrado isoladamente**, **altitude e mando identificados separadamente**, e **cada termo ambiental mantido só se passar o portão com controle de comparações múltiplas**. Sem isso, o resto é decoração.

---
*Camada 2 v1 — design, sem código de sistema (pseudocódigo só ilustra). Consome o contrato v5.0 + apêndice de formas. Consolida v5 §15/§17/§18 e incorpora os achados A1/A2/B2/B4 de [[camada1-revisao-v5]]. Fontes verificadas no repo em 2026-06-15; mercado histórico **a validar**, não assumido. Probabilidades, nunca certezas — e o backtest é o único aceite real, não uma promessa de acurácia.*
