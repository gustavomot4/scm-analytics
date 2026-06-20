---
tags: [dev, audit, auditoria, modelo, plano]
status: atual
tipo: auditoria
data: 2026-06-20
aliases: ["Auditoria e plano 2026-06-20", "Audit modelo 2026-06-20"]
---

# Auditoria técnica + plano de melhorias (modelo + sistema) — 2026-06-20

Auditoria independente do repositório, nos três papéis pedidos: **cientista de dados / estatístico de previsão esportiva**, **arquiteto de software** e **auditor técnico**. Foco principal: o **modelo matemático**. Método: li todo o vault e todo o `scm_analytics/scm/` (32 módulos, ~5.2k linhas), reconstruí o fluxo de ponta a ponta e **reproduzi numericamente** as fórmulas centrais e o backtest sobre o `dados/scm.sqlite` local (49.435 jogos, 148.281 previsões em 3 versões). Cada número é marcado **[verificado]** (reproduzi) ou **[inferido]** (só li). Princípio do projeto respeitado: *probabilidades, nunca certezas; nada é elogiado sem justificativa técnica.*

> **O que pude e não pude executar.** Reproduzi: `backtest_harness` (todos e `--major`), `report` (ECE/cobertura), os portões de **altitude**, **ataque/defesa**, **Dixon-Coles**, a correlação das pernas do ensemble, a curva de empate (com e sem cutoff PIT), e as fórmulas de núcleo (`we`, Poisson, λ, knockout, altitude). **Não** consegui rodar `pytest` (sandbox sem o pacote e sem rede para instalar) — então li os 25 arquivos de teste (134 casos) para avaliar qualidade, mas **não confirmei pass/fail**; declarado.

> **Relação com auditorias anteriores.** Já existem [[Auditoria tecnica externa (2026-06-18)]] e [[Auditoria tecnica completa (2026-06-19)]]. Esta auditoria **(a)** reproduz de forma independente os achados centrais daquelas (e confirma que as correções de alto impacto — forma na porta da frente, σ escalado, altitude no torneio — **estão de fato no código v0.3**), **(b)** quantifica o que continua aberto, e **(c)** prioriza o caminho mais curto para subir o teto. Onde divirjo das notas do vault, aponto.

---

## 0. Sumário executivo

**Nível técnico geral.** Engenharia e disciplina de processo: **alto** (raro para o porte). Modelagem estatística efetivamente *entregue*: **médio** — baseline correto, honesto e calibrado, mas com aparato (ensemble, incerteza) **parcialmente inerte** e ganho de skill **pequeno** sobre o piso do `dr`. O projeto tem o ativo mais valioso e mais raro de um sistema preditivo: um **portão estatístico** (ΔBrier pareado com IC bootstrap que não pode cruzar zero, `backtest_harness.gate`, linhas 100–104) que **de fato rejeita** fatores sem evidência (calor, estilo, Dixon-Coles e recalibração foram construídos e barrados).

**3 maiores forças** (com evidência):
1. **Honestidade metodológica operacional.** Pipeline point-in-time real (snapshot pré-jogo em `match_ratings`, `elo_engine.py:133-139`; teste anti look-ahead `tests/test_features_pit.py:89`), portão pareado com IC, e múltiplos baselines (uniforme, Elo interno, **lookup não-paramétrico = teto do `dr`**, `backtest_harness.py:176-227`). [verificado]
2. **Coerência [0,1] por construção** via curva de empate restrita com cap por amostra (`predictor.ved_from_elo`, linhas 207-218): em dr∈[−800,800] nenhuma P sai de [0,1]. [verificado]
3. **Calibração boa de verdade.** ECE **0,0260** nos torneios (n=2253) e reliability quase diagonal; bate o uniforme com folga (ΔBrier +0,1077, IC [+0,0925, +0,1228]). [verificado]

**3 maiores fraquezas** (com evidência):
1. **Ensemble de diversidade fictícia.** As duas pernas (Poisson e Elo-direto) saem do **mesmo escalar `dr`**: corr de P(V) = **0,9966** sobre 5.000 jogos (`predictor.lambdas`+`poisson_reads` vs `ved_from_elo`). [verificado] A "combinação de modelos" é redundante; a perna independente (mercado) é zero no histórico (`predictor.py:56-58`, `w_ad=0`).
2. **O modelo está no teto do `dr`.** Empata com o lookup não-paramétrico (torneios +0,0026, IC [−0,0003, +0,0054]; todos −0,0003, IC [−0,0008, +0,0003]). [verificado] Ou seja: já extrai ~todo o sinal do `dr`; para subir precisa de informação **além do `dr`** (gols/xG/mercado/escalações).
3. **Incerteza pouco informativa na base e não propagada no torneio.** `σ_R` satura em ~40 para qualquer seleção com ≥100 jogos (`elo_engine.sigma_r`: n=100→41, n=200→40). [verificado] E o Monte Carlo da Copa (`simulate.py:171,193`) amostra de **λ pontual, sem propagar σ_dr** → probabilidades de título superconfiantes.

**Top-5 melhorias por impacto × esforço** (4 de 5 são do modelo):
1. **(MODELO) Ligar a perna ataque/defesa não-Elo** (`attack_defense.py`, já construída e validada): portão **ΔBrier +0,00391, IC [+0,00280, +0,00511]** (torneios, w_ad=0,30). [verificado] É a única alavanca que **bate o teto do `dr`** porque traz informação de gols. Esforço baixo (flag + rebuild + bump de versão). **Já passou o portão e está OFF.**
2. **(MODELO/VALIDAÇÃO) Congelar a curva de empate com cutoff PIT** e re-medir: hoje a `DRAW_CURVE` foi ajustada in-sample (inclui os jogos do teste; `predictor.py:30-34,160-165`). Diferença frozen vs PIT<2015 ≈ 0,4–0,7 pp em P(E). [verificado] Esforço baixo; tira um vazamento declarado.
3. **(MODELO) Forma saturante de GD** (`gd_form="sat"`, já implementada, OFF): a linear faz **λ_B<0 para dr≳740** (−0,62 em dr=1100), onde o piso passa a "fazer a modelagem". [verificado] Relevante em goleadas da Copa (favorito vs estreante). Atrás do portão.
4. **(DADOS) Recalibrar o nível de gols `T_base`** (`calibrate_total.py`, candidato): o modelo **superprevê BTTS ~5 pp** (47,7% previsto vs 42,7% real, todos). [verificado] É viés de nível, não de correlação (por isso Dixon-Coles não resolve).
5. **(VALIDAÇÃO/PRODUTO) Fechar o laço prospectivo da Copa**: há 5 previsões registradas (`dados/registro-auto.csv`) e **0 liquidadas** → o Brier real de 2026 ainda é zero amostra. Liquidar rodada a rodada é o único juiz que importa daqui pra frente.

**Teto atual em uma frase.** O teto é a informação contida no `dr` (Elo+forma): Brier **≈0,559** em torneios, calibrado, no nível do lookup — e o que o levanta é **adicionar uma fonte verdadeiramente independente de gols** (perna AD já validada; depois xG/odds), não mais ajuste paramétrico no núcleo, que o portão já mostrou estar esgotado.

---

## 1. Visão geral e fluxo

**Objetivo do sistema.** Previsão local e gratuita (R$ 0) de partidas de seleções, com foco na Copa 2026: entrega P(V/E/D) + banda, λ_A/λ_B, mercados derivados (over/under, BTTS, dupla chance, handicap, quem marca 1º, clean sheet), placares prováveis e um score de confiança. Restrições inegociáveis ([[CLAUDE]]): custo zero, roda offline (snapshot em disco, nada lê a internet no cálculo), registro pré-jogo imutável, sem ML opaco / bayes hierárquico, probabilidades nunca certezas.

**Fluxo principal (reconstruído e verificado).** Pipeline linear acoplado por tabelas SQLite (contrato de I/O por tabela):

```
ingest → elo_engine → features_pit → predictor → backtest_harness → report
martj42    Elo + σ_R     forma + σ_dr    λ→Poisson + Elo-direto       Brier/RPS/    reliability
(CSV)      (pré-jogo PIT) (point-in-time)  → ensemble → V/E/D + banda   LogLoss+IC+   + ECE +
                                                                        PORTÃO       cobertura
```

| Módulo | Recebe | Produz |
|---|---|---|
| `ingest.py` | CSV martj42 (`results.csv`) | `teams`, `matches` (idempotente por `natural_key`) |
| `elo_engine.py` | `matches` | `match_ratings` (rating **pré-jogo** PIT, `dr`, `we_home`) + `ratings_current` (+σ_R) |
| `features_pit.py` | `match_ratings`+`matches` | `match_features` (`form_*`, `dr_adj=dr+forma`, `sigma_dr`) — só dados com data < t |
| `predictor.py` | `match_features` | `predictions` (P(V/E/D), banda, λ, over2.5, BTTS) — modelo `baseline-v0.3-altitude` |
| `backtest_harness.py` | `predictions`+`matches` | Brier/LogLoss/RPS + IC vs uniforme/Elo/lookup + `gate()` |
| `report.py` | `predictions`+`matches` | reliability/ECE + cobertura de banda (agregada e por faixa) |
| `predict_match.py` | `ratings_current` (+forma, altitude, desfalques, odds) | **porta da frente**: previsão de UM confronto + confiança |
| `simulate.py` | `ratings_current`+`copa2026.json` | Monte Carlo do torneio: P(campeão/final/semi/passar) |
| `registrar.py` | `predict_match` | registro prospectivo imutável (`registro-auto.csv`) → Brier real da Copa |

Módulos de fator atrás do portão (C2.5/candidatos): `altitude.py`/`factors.py` (E1, **adotada**), `heat.py` (E3, rejeitada), `estilo.py` (rejeitada), `dixon_coles.py` (rejeitada), `calibrate_1x2.py` (rejeitada), `sigma_glicko.py` (OFF), `attack_defense.py` (**passa o portão, OFF**), `odds.py`/`xg.py`/`desfalques.py` (encaixes para dados que faltam). Ferramentas de calibração: `calibrate*.py`.

**Consistência produção ↔ validação.** A porta da frente (`predict_match`) e o backtest usam a **mesma** função `predictor.predict`. As três divergências graves da auditoria 2026-06-19 foram corrigidas e **confirmo no código v0.3**: forma aplicada ao `dr` em produção (`predict_match.py:127`), confiança usando `σ_R` escalado por `vol_mult` (`:133-134`), altitude no Monte Carlo de grupo (`simulate.py:168`). Resíduo: a banda em produção é **re-centrada no ponto do ensemble** com a largura da leitura Elo-direto (`predict_match.py:172-175`) — cosmético, mas é um "o que se entrega ≠ o que se grava no backtest" (lá a banda são os percentis 16/84 da leitura Elo-direto, `predictor.py:241`).

---

## 2. Arquitetura

**Organização.** Vault Obsidian (00–06: contexto, planejamento/contrato, modelos, dados, desenvolvimento, referências, análises) + pacote `scm_analytics/scm/`. Separação **núcleo puro × persistência** é boa: as funções matemáticas (`lambdas`, `poisson_reads`, `ved_from_elo`, `predict`, `markets`) não têm I/O; os `run()` de cada estágio fazem o SQL. Acoplamento entre estágios é via SQLite (baixo). Coesão por módulo é alta. O `config.py` centraliza coeficientes (parcialmente — ver abaixo). Ciclo de import `predictor↔altitude` foi quebrado extraindo termos puros para `factors.py` (`factors.py:1-12`) — boa decisão.

**A arquitetura suporta virar um preditor sério?** Em grande parte **sim**, com lacunas concretas:

- **Versionamento de modelo:** existe (`predictions.versao_modelo`, PK `(match_id, versao_modelo)`; `compare()` faz ΔBrier entre versões). Bom. **Mas** os coeficientes vivem em dois lugares: `config.py` (linhas 16-40) **e** os defaults das dataclasses `frozen=True` (`PredictParams`, `EloParams`, `FeatureParams`). O próprio `config.py:8-12` admite que só `THETA_ALT`/`SIGMA_R_REF`/`SIGMA_AJUSTE_DEFAULT` importam de lá; o resto está **espelhado**. Risco real de divergência entre "fonte única" e o que roda. **Recomendação:** as dataclasses devem ler de `config.py` (uma fonte só), e gravar um hash dos coeficientes no `meta` por versão.
- **Recalibração / re-treino:** os scripts existem (`calibrate*`, gates), mas são **manuais e ad hoc**; não há um comando único "re-treina tudo com cutoff X, congela curvas PIT, escreve versão Y" reprodutível. Para uso ao vivo (drift entre rodadas) isso precisa virar pipeline.
- **Uso ao vivo / drift:** `registrar.py` é o embrião certo (registro imutável + settle + Brier prospectivo). Falta o **monitor de drift** (Brier móvel por janela; alerta quando sai da banda do backtest) e a **recalibração agendada**.
- **Novas fontes:** o schema já tem `odds_hist`, `team_xg`, `venues`, `context` (vazios hoje) — **aditivos**, destravam dados sem migração. Boa antecipação (`db.py:83-124`).
- **Esquema de dados duplicado:** `predictions` **não** grava `sigma_dr` nem `confianca` (o design em [[Esquema SQLite]] previa; a tabela real `db.py:74-82` não tem). Então a calibração de σ_dr isolada (exigida no aceite) tem de recomputar a banda. Pequeno, mas é dívida.

**Veredito de arquitetura.** Sólida para evoluir; os bloqueios são de **disciplina de configuração** (coeficiente em duas fontes) e de **automação de recalibração/drift**, não de design de fundo.

---

## 3. MODELO MATEMÁTICO — núcleo da análise

### 3.1 Inventário completo de fórmulas, coeficientes e "números mágicos"

**Elo** (`elo_engine.py`):
- `we(dr) = 1/(1+10^(−dr/400))` (`:41-43`). [verificado] we(0)=0,5000; we(100)=0,6401; we(200)=0,7597.
- `R_novo = R + K·G·(W−we)`, zero-soma (`:143-146`).
- `K`: Copa 60 · continental 50 · eliminatória 40 · Nations 30 · amistoso 20 · default 40 — heurística por palavra-chave no texto livre `tournament` (`:56-80`).
- `G(gd) = 1 (≤1) · 1.5 (=2) · (11+|gd|)/8 (≥3)` (`:46-53`).
- `σ_R(n) = 40 + (200−40)·e^(−n/20)` (`:83-85`). [verificado] n=30→76; 60→48; 100→41; 200→40.
- `H_hist = 100` em jogo não-neutro (`:29,129`).

**Forma e incerteza** (`features_pit.py`):
- `w_i = 0.9^meses · (0.5 se amistoso)`; `forma = clip(60·média_pond(resíduo), ±30)`, resíduo = real − `we` (`:84-94`). PIT (data < t).
- `dr_adj = dr_elo + forma_home − forma_away` (`:132`).
- `vol_mult(desvio) = clip(0.4 + 0.6·desvio/0.35, 0.6, 1.6)`, neutro (=1) se n_form<5 (`:45-56`).
- `σ_ajuste = 80·desvio_forma` (`:130-131`); `σ_dr = √(σ_R_h²·vol² + σ_R_a²·vol² + σ_ajuste_h² + σ_ajuste_a²)` (`:128-133`).

**Saldo, total e λ** (`predictor.py`):
- `GD = θ·dr/100`, θ=0,45 (linear, default) **ou** `GD_max·tanh(dr/667)` (saturante, OFF) (`:64-69`, `:39-45`).
- `T_m = (2.6 + 0.10·|dr|/100)·estilo_A·estilo_B·heat` (`:72-74`).
- `λ_A=(T_m+GD)/2`, `λ_B=(T_m−GD)/2`; piso `λ_min=0.15` **conservando T_m** (`:80-92`).
- δ_ata (desfalque ofensivo): `λ_T·(1−δ_ata_T)`, sem inflar o rival (`:98-101`).

**Poisson e leituras** (`predictor.py`):
- `M[i][j]=Pois(i;λ_A)·Pois(j;λ_B)`, i,j=0..10; V/E/D, over (i+j≥3), `BTTS=(1−e^−λ_A)(1−e^−λ_B)` (`:109-130`).
- Curva de empate **C1 empírica** `DRAW_CURVE` (10 pontos, interpolação linear em |dr|) (`:33-34,133-153`).
- `ved_from_elo(dr)`: `w=we(dr)`; `pe=clip(draw_prob, 0, 2·min(w,1−w)−0.02)`; `pv=w−pe/2`; `pd=1−pv−pe` (`:207-218`).
- `elo_direct_read`: propagação **determinística** por 200 estratos de igual probabilidade de N(dr,σ_dr); banda = percentis 16/84 de P(V) (`:221-242`).

**Ensemble e mata-mata** (`predictor.py`):
- `mix = (0.56·Poisson + 0.44·Elo)/(0.56+0.44)`, clamp por leitura [0.02,0.96] antes e depois; perna AD só se `w_ad>0` (`:282-291`, `w_ad=0` em `:58`).
- `avanço_A = P(V)+P(E)·(0.5+ε·sinal(dr))`, ε=0,03 (`:251-269`).

**Altitude** (`factors.py:51-60`): `pen(T)=max(0, alt_sede−alt_casa_T)`; `GD_alt = 0.5·(pen_B−pen_A)/1000`. [verificado] CDMX, México×planície = +1,120; Guadalajara, planície×México = −0,783; Miami = 0,00.

**Confiança** (`predict_match.py:79-94`): `conf = 100·reliab(p_max)·maturidade`, `maturidade = 1−min(0.5, σ_R_médio/200)`; `reliab` = curva isotônica do backtest (`calibrate_confidence.py`).

### 3.2 Verificação numérica [verificado]

Reproduzi, em script isolado sobre o `scm.sqlite` local:

| Item | Resultado reproduzido | Doc | Status |
|---|---|---|---|
| Backtest **torneios** (n=2253) | Brier **0,5590**, LL 0,9457, RPS 0,1922 | ~0,562 | bate (versão atual) |
| vs uniforme | +0,1077 IC [+0,0925, +0,1228] | bate c/ IC | **PASS** |
| vs Elo interno | +0,0038 IC [+0,0010, +0,0066] | +0,0037 | **PASS** |
| vs lookup (teto dr) | +0,0026 IC [−0,0003, +0,0054] → **empata** | empata | **PASS** |
| Backtest **todos** (n=49435) | Brier **0,5365** | 0,5366 | **PASS** |
| ECE torneios | **0,0260** | 0,023 | bate |
| Poisson IRN×NZL (1.40,0.78) | 51,7/27,5/20,9, over 37,2, BTTS 40,8 | idem | **PASS exato** |
| Altitude CDMX/Guad | +1,120 / −0,783 | +1,12/−0,78 | **PASS** |
| Portão altitude | +0,0492 IC [+0,029, +0,069], n=568 | +0,049 | **PASS** |
| Portão AD (w=0,30) | +0,00391 IC [+0,00280, +0,00511] keep | +0,0039 | **PASS** |
| Portão Dixon-Coles | ρ=−0,06, ΔBrier_BTTS −0,00069 IC<0 → rejeita | rejeita | **PASS** |
| corr(P(V) Poisson, Elo) | **0,9966** | ~0,997 | **PASS** |

**Conclusão:** a aritmética do modelo bate com a documentação em tudo que testei. As divergências são de **interpretação/risco**, não de conta.

### 3.3 Correção e consistência das fórmulas

As fórmulas são dimensionalmente e estatisticamente corretas. Pontos de atenção reais:

- **`λ_B` negativo no tail (linear).** [verificado] Com GD linear, `λ_B_bruto` = (T_m−GD)/2 zera em dr≈740 e fica negativo depois (dr=900→−0,27; dr=1100→−0,62), salvo pelo piso `λ_min=0.15`. Nesse regime o **piso passa a modelar** o placar do azarão, e a conservação de T_m tira gols do favorito artificialmente. Na Copa, dr>740 é plausível (ex.: Argentina ~2100 vs estreante ~1300). A forma `tanh` (já no código, OFF) elimina isso. **Não é erro de conta; é escolha de forma que degrada no tail.**
- **`σ_dr` implementa 1 dos 5 termos do contrato.** O contrato (§3.12) define σ_ajuste com 5 componentes (desfalque-dúvida, meio-tier, desvio-forma, Δfuso, descanso). O código só implementa o **desvio-forma** (`features_pit.py:130`). Os demais não existem no backtest (não há os dados). É lacuna declarada, não erro — mas significa que "σ_ajuste" no código ≠ σ_ajuste do contrato.
- **Mercados Poisson-condicionais.** A diagonal da matriz soma o P(E) **da Poisson**, não o do ensemble (declarado, `predictor.py:8`). Correto e rotulado; só não confundir as duas P(E).

### 3.4 Vieses e armadilhas estatísticas

- **Vazamento temporal (look-ahead): essencialmente controlado.** [verificado] O rating é snapshot pré-jogo (`elo_engine.py:133-139` grava antes de atualizar); a forma usa `date < t` (`features_pit.py:69`); o teste `test_no_lookahead` perturba o futuro e confirma estabilidade do passado. **Boa engenharia anti look-ahead.**
- **Vazamento in-sample (real, 2º ordem):** a `DRAW_CURVE` congelada foi ajustada no **conjunto inteiro**, inclusive nos jogos avaliados. [verificado] Reconstruí: frozen = (0,2847; 0,2709; 0,2629) = rebuild full; PIT<2015 = (0,2811; 0,2668; 0,2558). A componente P(E) do modelo "viu" o teste. Efeito pequeno (≈0,4–0,7 pp), **mas é o único componente não-PIT** e o próprio código o declara (`predictor.py:30-32`). O lookup-teto e o baseline Elo usam a mesma curva → o vazamento não infla artificialmente a *diferença* model−Elo, mas infla os Briers absolutos um tiquinho.
- **Calibração:** boa no agregado (ECE 0,026), com **superconfiança na faixa 0,8–0,9** (prev 0,85 → obs 0,74, n=81; banda [0,84;0,92] não cobre 0,74) e leve subprevisão em 0,0–0,1 (prev 0,06 → obs 0,11). [verificado] A recalibração global foi testada e deu **T=1,0** (nada a corrigir globalmente, `calibrate_1x2.py`) — mas há um **bolsão local** de superconfiança no favorito que uma isotônica por faixa na marginal de mandante pegaria.
- **Regras de pontuação:** Brier soma-forma (máx 2), LogLoss, RPS ordinal — todas corretas (`backtest_harness.py:42-58`). IC por **bootstrap pareado** com seed fixa (`gate`, `:100-104`). Metodologia de avaliação **forte**. Ressalva: a calibração/ECE e a cobertura de banda são medidas só na **marginal de vitória do mandante** (`report.py:30`), não nas 3 classes — empate e derrota não têm reliability própria.
- **Baselines honestos — com uma ressalva importante.** Há uniforme, Elo e **lookup não-paramétrico** (teto do dr). Excelente. **Mas** o "Elo público" é **interno** (o próprio Elo do projeto, `we`+curva C1, `backtest_harness.py:124-135`), **não** eloratings.net — o código admite (`:10-11`). Logo "bate o Elo público com IC>0" significa "bate a leitura Elo-direto sem forma/altitude/Poisson", **não** um previsor externo. O benchmark externo de verdade (eloratings, e sobretudo **odds de mercado**) ainda **não está no portão**.
- **Incerteza:** a propagação encolhe o favorito na direção certa (Jensen, `test_propagation_shrinks_favorite`). [verificado] **Mas** (i) a base σ_R é degenerada (~40 para toda elite), (ii) a confiança é quase função de p_max, e (iii) o **Monte Carlo do torneio não propaga σ_dr** (`simulate.py:171,193` amostram de λ pontual) → títulos superconfiantes. A incerteza é "informativa" na previsão de 1 jogo, **degenerada no torneio**.
- **Diversidade do ensemble: fictícia.** [verificado] corr(P(V)_Poisson, P(V)_Elo) = **0,9966**; |dif| médio 0,0437. As duas pernas são leituras da mesma `dr`. O pool 0,56/0,44 é praticamente uma leitura só. A perna **independente** existe e está pronta (AD, corr ~0,95) mas OFF.
- **Tail / bordas:** λ_B<0 (acima) e o piso que passa a modelar; cap da curva de empate segura P∈[0,1] nos extremos [verificado]. Knockout soma 1 por construção [verificado].
- **Direção/causalidade das features:** altitude move P(V) do adaptado para cima (`test_run_applies_altitude`, e [verificado] Bolívia em La Paz > no Rio); forma com sinal correto; desfalque ofensivo corta o próprio λ (corrigido, `predictor.py:93-101`). Sinais corretos.
- **Overfitting:** baixo no núcleo — pouquíssimos graus de liberdade (θ, κ, T_base, λ_min, ε + 10 pontos da curva) contra n=49k. O risco real é nos **fatores contra amostra pequena** (torneios n=2253; altitude n=568): por isso o portão pareado é essencial e está sendo usado.

### 3.5 Consistência produção ↔ validação

Alinhada no essencial (mesma `predict`, forma e σ escalado em produção — §1). Resíduos: banda re-centrada em produção (`predict_match.py:172-175`); `predict_match` adiciona `banda_mando²=20²` ao σ_dr para anfitrião (`:135`) que o backtest histórico nunca vê (não há anfitrião 2026 no passado) — correto, mas é um termo só-produção. **Não encontrei "valida X, entrega Y" grave no núcleo v0.3.**

### 3.6 Coeficientes: calibrados ou chutados?

Mistos, e **honestamente rotulados [a calibrar]**:
- **Calibrados/validados:** θ_alt=0,5 (McSharry, e portão +0,049); a decisão de **não** mudar θ/κ/T_base (grid de 243 combos deu ganho +0,0013, IC quase nulo → manteve placeholders, D-17). [inferido do doc + verifiquei que o default segue 0,45/0,10/2,6]
- **Placeholders plausíveis mas não fitados onde importam:** `T_base=2.6` (nunca calibrado na métrica que afeta, BTTS — daí o viés +5 pp); `λ_min=0.15`; `form_scale=60`, `form_cap=30`; `σ_ajuste_c=80`; `vol_mult` [0.6,1.6]; `ε_ko=0.03`.
- **Chutados (sem fonte, declarado):** tiers de desfalque (`desfalques.py`: 35/15/5 Elo, 0,25/0,12/0,04 λ) — sem base de escalações, são placeholders.

### 3.7 Modelos superiores (dado o foco no modelo)

Tudo abaixo respeita as restrições (R$ 0, local, sem ML opaco, auditável). Ordenado por relação ganho/risco.

| Alternativa | Por que é superior | Ganho esperado (métrica) | Esforço | Risco overfit | Como validar |
|---|---|---|---|---|---|
| **Perna ataque/defesa não-Elo** (Maher/Poisson online, **já no repo**) | Única fonte **independente** do `dr` (ratings de gols, não de pontos); quebra a diversidade fictícia | **+0,0039 Brier** torneios, IC [+0,0028,+0,0051] [verificado]; AD sozinho 0,5535 [inferido] | **Baixo** (ligar `w_ad`, rebuild, bump) | Baixo (paramétrico, PIT, poucos g.l.) | Já validado pelo portão; varrer w_ad∈{0,2;0,3;0,4} e congelar o melhor por ΔBrier pareado |
| **Integração de odds de mercado** (de-vig + 3ª perna 0,20) | Benchmark mais difícil e sinal genuinamente externo; a literatura mostra mercado ≥ modelos | Médio-alto no 1X2 (fechar gap p/ o mercado); melhora calibração do favorito | Médio (captura **manual** — sem histórico grátis) | Baixo | Coletar odds de fechamento da fase de grupos 2026; ΔBrier do ensemble c/ vs s/ odds, IC pareado; comparar Brier do modelo vs **Brier do mercado** |
| **Recalibração isotônica por faixa** (na marginal de mandante) | Corrige o bolsão de superconfiança 0,8–0,9 (T global=1,0 não pega o local) | Pequeno no Brier, **maior no ECE** da cauda | Baixo | Médio (cuidar de PIT: fit no treino, aplica no teste) | ECE e cobertura de banda por faixa, treino<cutoff/teste≥cutoff |
| **Dixon-Coles τ(ρ)** | Corrige correlação de placares baixos | **Negativo** aqui (−0,0007 BTTS, IC<0) [verificado] | Baixo | — | Já rejeitado; reabrir só com xG |
| **Forma saturante de GD (tanh)** | Mantém λ_B>0 no tail sem o piso "modelar" | Neutro no centro, melhor no tail (goleadas) | Baixo (flag) | Baixo | ΔBrier/RPS restrito a jogos |dr|>500, IC pareado; placar exato (logloss) |
| **σ estrutural (Glicko/TrueSkill)** (`sigma_glicko.py`, OFF) | Substitui σ_R degenerado (RD varia 30–64) → banda/confiança informativas | Pouco no Brier do ponto; **muito na cobertura/confiança** | Médio (rebuild + portão de banda) | Médio | `report.band_coverage_binned` treino/teste: a banda cobre nominalmente por faixa? |
| **Skellam / Weibull-count p/ o saldo** | Modela o saldo (V/E/D) diretamente, sem assumir 2 Poisson independentes | Médio (melhor empate/saldo) | Médio-alto | Médio | ΔRPS (ordinal) e logloss do saldo, IC pareado |
| **xG como prior de estilo** (`xg.py`+`attack_defense.xg_priors`, esqueleto) | xG é melhor preditor que gols; encolhe os ratings AD onde há cobertura | Médio **onde há cobertura** (2018/22/Euro) | Médio (derivar CSV do StatsBomb) | Médio (cobertura parcial → viés de seleção) | Portão da perna AD **com** vs **sem** prior xG, só no subconjunto coberto |
| **Hierárquico bayesiano** | Encolhimento principiado, incerteza nativa | Potencialmente alto | Alto | **Conflita com a restrição** "sem bayes hierárquico / auditável" | Fora de escopo declarado — só se a restrição mudar |

**Leitura honesta da restrição.** A regra "sem ML/bayes" **limita** o teto: a perna AD e odds vão longe dentro dela, mas um GLM Poisson hierárquico (ataque/defesa com pooling) seria o próximo salto natural e está barrado por decisão de projeto. Vale registrar que a restrição custa acurácia — é uma escolha de auditabilidade, legítima, mas com preço.

---

## 4. Fontes de dados

| Fonte | Em uso? | Qualidade/cobertura | Limitação honesta |
|---|---|---|---|
| **martj42/international_results** | **SIM** (base do Elo; 49.435 jogos 1872–2026) | alta para resultados; cobre torneio/neutro | atualização por PR (lag); sem placar por minuto, sem escalações |
| **Open-Meteo (elevation)** | **Parcial** (altitudes hardcoded em `factors.py:30-40`, não via API) | suficiente p/ as sedes de altitude | dicts no código; `venues`/`teams.home_altitude_m` existem mas pouco usados |
| **Open-Meteo (clima/WBGT)** | **Não** (calor rejeitado; `climatology.json` existe) | climatologia mensal = proxy grosseiro | sem dado horário do jogo (inviável, ~49k chamadas) |
| **StatsBomb (xG, bola parada)** | **Não** (`team_xg` vazio; `xg.py` esqueleto) | bom, mas **só 2018/2022/Euro/WWC** | não cobre as 48, não ao vivo |
| **Kalshi/Polymarket/casas (odds)** | **Não** (`odds_hist` vazio; `odds.py` encaixe pronto) | sinal independente mais forte | **sem histórico grátis** → captura manual |
| **eloratings.net** | **Não** (benchmark externo) | sanidade do Elo | SPA sem API → snapshot manual |
| **Wikidata** (técnico, elevação) | **Não** | — | semiestruturado |

**O que falta, ordenado por impacto esperado na acurácia:**
1. **Odds de fechamento de mercado** — o sinal independente mais forte e o benchmark mais difícil; destrava a 3ª perna real do ensemble e mede se o modelo tem edge sobre o mercado. (Alto)
2. **Escalações/desfalques estruturados** — `desfalques.py` está pronto, mas sem fonte os tiers são chute; o impacto por jogo (estrela fora) é grande. (Alto, episódico)
3. **xG por seleção** — prior de estilo menos ruidoso que gols; melhora a perna AD. (Médio, onde há cobertura)
4. **Minuto do gol** (`goalscorers.csv` do martj42) — destrava "quem marca 1º" calibrado e intervalos quentes. (Baixo-médio)
5. **Elevação/clima por sede via tabela** (não dicts) — já há schema; baixaria o risco de erro manual. (Baixo)

**Nota de integridade.** O `copa2026.json` traz o sorteio oficial declaradamente obtido por busca web e **cruzado 100% com os 20 jogos já disputados** no martj42 — tratado aqui como **[declarado]**, não reverifiquei o chaveamento contra a realidade. Os 5 registros prospectivos (`registro-auto.csv`) estão **gravados e não liquidados** → Brier real da Copa ainda indisponível.

---

## 5. Qualidade do código

**Pontos fortes.** Legível, modular, docstrings que explicam o *porquê* (e citam decisões/ADRs). Núcleo puro separado de I/O (testável sem rede; fixtures `:memory:`). Idempotência real (testada). Tratamento de erro de borda razoável (mensagens de "rode X antes"; `db.session` como context manager, `db.py:136-149`). Sem dependências pesadas; faixas de versão com teto de major.

**Pontos a melhorar:**
- **Testes não pegam regressão de *skill*.** [verificado por leitura] Os 134 casos cobrem coerência, invariantes, anti look-ahead, idempotência e **reprodução de valores-ouro** (ex.: `test_poisson_reproduces_manual` usa 0,516/0,275… fixos — bom, não circular). **Mas não há teste que fixe o Brier/IC do backtest.** Uma mudança de coeficiente que preservasse a coerência e degradasse o Brier **passaria** na suíte. Falta um teste de "skill mínimo" (ex.: Brier torneios < 0,57 e bate uniforme com IC) rodando sobre um mini-snapshot versionado.
- **Risco de teste circular: baixo, mas existe.** `test_dr_adj_equals_elo_plus_form` reproduz a própria fórmula `dr_adj=dr_elo+forma`. É teste de fiação (aceitável), mas não valida a *correção* da fórmula, só que o valor gravado bate com os componentes.
- **Coeficiente em duas fontes** (`config.py` × dataclasses) — já citado (§2); é dívida de configuração e risco de divergência silenciosa.
- **Performance dos portões.** `gate_ad`/`estilo` recomputam `team_form` por linha (consulta SQL por jogo) — rodam, mas são lentos (não consegui rodar 3 pesos em <45s). Para re-treino frequente, vale materializar `match_features` e evitar o N+1.
- **`predictions` sem `sigma_dr`/`confianca`** (§2) — força recomputo na calibração de banda.
- **Segurança:** SQL parametrizado (sem injeção); a única rede é `requests` no `--download` (isolado, lazy). OK para o escopo.

---

## 6. Regras de negócio (domínio: seleções / formato da Copa)

- **K por competição** (`elo_engine.k_factor`): captura bem a hierarquia (Copa>continental>eliminatória>Nations>amistoso). **Limite real:** é heurística por palavra-chave no texto livre; o martj42 **não codifica fase**, então toda a fase de um continental leva K=50 (declarado, `:61-66`) — fase de grupos e final pesam igual. Efeito pequeno, mas é uma imprecisão de domínio.
- **Mando.** `H_hist=100` no histórico; anfitrião 2026 `+40` em banda (rebaixado de +60 por evidência de jogos-fantasma COVID). Defensável e bem fundamentado. **Risco de dupla contagem com altitude** para o México em CDMX (GD_alt +1,12 **e** mando +40) — declarado, a calibrar junto.
- **Formato da Copa 2026** (`simulate.py`): 12×4 → 2 melhores + 8 melhores 3ºs → mata-mata, com **chaveamento oficial da FIFA** (R32 73–88 → final 104) e alocação dos 3ºs por elegibilidade do Anexo C (`:42-85`). Desempate de grupo: pontos → saldo → gols → **confronto direto** (regra FIFA) → moeda (`:177-188`). Boa fidelidade ao regulamento. Simplificações declaradas (não reproduz o desempate linha-a-linha das 495 combinações; mata-mata neutro).
- **Mata-mata.** Empate → `0.5+ε·sinal(dr)` (ε=0,03, pênalti ~moeda). Coerente com a literatura (60:40 não se sustentou). Razoável.
- **Aprimorável:** (i) prorrogação/pênaltis colapsados num ε único (sem modelar gols na prorrogação); (ii) altitude só no grupo, não no mata-mata em sede alta (simplificação que **sub**-credita o México num eventual mata-mata em CDMX); (iii) terceiro-colocado e desempates por *fair-play* não modelados (efeito ínfimo).

---

## 7. Problemas encontrados

Severidade: 🔴 Crítica · 🟠 Alta · 🟡 Média · ⚪ Baixa. "v/i" = [verificado]/[inferido].

| # | Problema | Sev | Local (arquivo:linha) | Impacto | Como corrigir | Como validar | v/i |
|---|---|---|---|---|---|---|---|
| P1 | Ensemble de diversidade fictícia (pernas corr 0,9966) | 🟠 | `predictor.py:282-291`; `:56-58` | "Combinação" é redundante; teto no `dr` | Ligar perna AD (`w_ad>0`) — fonte de gols independente | ΔBrier pareado c/ vs s/ AD, IC>0 (já +0,0039) | v |
| P2 | Modelo no teto do `dr` (empata lookup) | 🟠 | `backtest_harness.py:191-227` | Ganho marginal só com ajuste paramétrico | Adicionar informação além do `dr` (AD, odds, xG) | ΔBrier vs lookup passa a >0 com IC | v |
| P3 | `σ_R` base degenerado (~40 p/ toda elite) | 🟡 | `elo_engine.py:83-85` | Banda/confiança pouco informativas | Adotar Glicko/TrueSkill (RD) após portão de banda | `band_coverage_binned` treino/teste | v |
| P4 | Monte Carlo do torneio não propaga σ_dr | 🟠 | `simulate.py:171,193` | P(título) superconfiante p/ favoritos | Amostrar dr~N(dr,σ_dr) antes da λ, ou inflar λ por σ | Cobertura: distribuição de avanços vs realizado | v |
| P5 | Vazamento in-sample da curva de empate | 🟡 | `predictor.py:30-34,160-165` | P(E) "viu" o teste (≈0,4–0,7pp) | Congelar `DRAW_CURVE` com `before_date` (PIT) | Re-rodar backtest c/ curva PIT; ΔBrier | v |
| P6 | λ_B<0 no tail (GD linear) → piso "modela" | 🟡 | `predictor.py:64-69,84-92` | Distorce goleadas (dr≳740) — comum na Copa | Adotar `gd_form="sat"` atrás do portão | ΔRPS/logloss em \|dr\|>500, IC | v |
| P7 | Superconfiança na faixa 0,8–0,9 | 🟡 | `report.py` (medido); `predictor.py:282-291` | Favoritos levemente superprevistos | Isotônica por faixa na marginal (PIT) | ECE/cobertura por faixa, treino/teste | v |
| P8 | "Bate o Elo público" é Elo **interno**, não eloratings/mercado | 🟡 | `backtest_harness.py:10-11,124-135` | Benchmark superestima a força relativa | Plugar eloratings (snapshot) e odds no portão | ΔBrier vs Elo externo e vs mercado | v |
| P9 | Viés de nível do BTTS (+~5pp) | 🟡 | `predictor.py:72-74`; medido `report.btts_report` | over/BTTS superprevistos | Calibrar `T_base` na Brier de BTTS/over | `calibrate_total` treino/teste, IC | v |
| P10 | σ_ajuste do contrato (5 termos) só tem 1 implementado | ⚪ | `features_pit.py:130` | Incerteza subestima fontes reais | Implementar fuso/descanso/desfalque-dúvida quando houver dado | Calibração de σ_dr isolada | v |
| P11 | Coeficientes em duas fontes (config × dataclasses) | ⚪ | `config.py:8-12` | Risco de divergência silenciosa | Dataclasses leem de `config.py`; hash no `meta` | Teste que compara config vs defaults | v |
| P12 | Testes não fixam skill (só coerência) | 🟡 | `tests/` (ausência) | Regressão de modelagem passa despercebida | Teste de Brier/IC mínimo sobre mini-snapshot | CI roda backtest e falha se Brier sobe | v |
| P13 | Validação prospectiva aberta (0 liquidados) | 🟡 | `dados/registro-auto.csv` | Sem Brier real da Copa | `settle-from-db` rodada a rodada | Brier prospectivo vs backtest, drift | v |
| P14 | K não distingue fase de continental | ⚪ | `elo_engine.py:61-80` | Elo levemente enviesado em continentais | Dado de fase (não há no martj42) ou ignorar | Sensibilidade do Elo a K por fase | v |
| P15 | Banda re-centrada em produção ≠ banda gravada | ⚪ | `predict_match.py:172-175` | "Entrega ≠ grava" (largura ok, centro difere) | Documentar ou unificar | Comparar banda produção vs backtest | v |

---

## 8. Plano de melhorias priorizado (modelo + sistema)

Ordenado por **impacto ÷ esforço**. Separado em **(a)** correções/consistência que **não** mudam o modelo validado (sem portão) e **(b)** mudanças que alteram λ/dr/probabilidade (**exigem backtest com IC antes de adotar**).

### (a) Correções e consistência — não precisam de portão

| Melhoria | Categoria | Impacto (métrica) | Esforço | Risco | Como medir |
|---|---|---|---|---|---|
| Congelar `DRAW_CURVE` com cutoff PIT | validação | remove vazamento (ECE/Brier "limpos") | baixo | baixo | re-rodar backtest; ΔBrier ≈0 confirma 2ª ordem |
| Unificar coeficientes em `config.py` + hash no `meta` | arquitetura | reprodutibilidade/versionamento | baixo | nenhum | teste config==defaults; hash por versão |
| Teste de skill mínimo no CI (mini-snapshot) | validação | barra regressão de modelagem | baixo | nenhum | CI falha se Brier torneios sobe além de ε |
| Gravar `sigma_dr`/`confianca` em `predictions` | arquitetura | calibração de σ isolada direta | baixo | nenhum | coluna populada; report usa |
| Liquidar registro prospectivo rodada a rodada | validação/produto | Brier **real** da Copa | baixo (operacional) | nenhum | `settle-from-db`; Brier prospectivo vs backtest |
| Materializar `team_form` (evitar N+1 nos portões) | performance | re-treino rápido | médio | nenhum | tempo de `gate_*` |

### (b) Mudanças no modelo — exigem portão (backtest + IC) antes de adotar

| Melhoria | Categoria | Impacto esperado (métrica) | Esforço | Risco (overfit) | Experimento de validação (treino/teste, métrica, IC, critério) |
|---|---|---|---|---|---|
| **Ligar perna AD não-Elo** | modelo | **+0,0039 Brier** torneios (IC [+0,0028,+0,0051]) [verificado] | baixo | baixo | Já passou. Varrer w_ad∈{0,2;0,3;0,4} no treino, escolher por ΔBrier pareado no teste (IC>0); rebuild + bump p/ `v0.4-ad` |
| **Integrar odds de mercado (3ª perna 0,20)** | dados/modelo | médio-alto no 1X2; calibra favorito | médio (captura manual) | baixo | Coletar odds de fechamento da fase de grupos 2026; ΔBrier ensemble c/ vs s/ odds (IC pareado); **comparar Brier do modelo vs Brier do mercado** (o juiz real) |
| **Recalibrar `T_base`** | modelo | corrige BTTS +5pp; ΔBrier BTTS | baixo | médio | `calibrate_total` treino<cutoff/teste≥cutoff; adotar se ΔBrier BTTS>0 (IC) **e** não piora 1X2 |
| **Isotônica por faixa (marginal mandante)** | modelo/validação | ↓ECE da cauda 0,8–0,9 | baixo | médio | Fit no treino, aplica no teste; critério: ↓ECE e cobertura nominal sem piorar Brier |
| **Forma saturante GD (tanh)** | modelo | melhora tail (goleadas) | baixo | baixo | ΔRPS/logloss em \|dr\|>500 (IC pareado); adotar se >0 sem piorar centro |
| **σ estrutural Glicko/TrueSkill** | modelo/incerteza | banda/confiança informativas | médio | médio | `band_coverage_binned` treino/teste: cobertura nominal por faixa; só adota se melhora cobertura sem piorar Brier |
| **Propagar σ_dr no Monte Carlo** | modelo/produto | P(título) calibrada (menos superconfiança) | baixo-médio | baixo | Amostrar dr~N(dr,σ_dr) por jogo; checar que favoritos encolhem; validar contra realizado quando houver |
| **xG como prior da perna AD** | dados/modelo | médio onde há cobertura | médio | médio | Portão AD com vs sem prior xG no subconjunto coberto (IC) |

> **Regra de adoção (já é a do projeto, reforçada):** nenhum item de (b) entra em λ/dr sem ΔBrier pareado com **IC95 que não cruza zero**, com **treino/teste separados no tempo** e **curvas congeladas PIT**. Mais variável contra amostra pequena = overfit.

---

## 9. Funcionalidades futuras (foco Copa)

- **Painel prospectivo ao vivo** (artefato/registro): Brier corrente da Copa vs backtest, calibração da rodada, alerta de drift. Fecha o laço de validação — é o que separa "estudo" de "sistema".
- **Comparador vs mercado por jogo**: ao lado de cada previsão, a odd de-vig e o ΔBrier acumulado modelo−mercado. É a métrica honesta de valor.
- **Explicador de incerteza**: além do `dr` decomposto (já existe), mostrar quanto da banda vem de σ_R vs forma vs mando — ajuda a confiar/desconfiar.
- **Cenários de classificação** (fim de grupo): probabilidade de cada seleção avançar condicional a resultados pendentes (insight de alto valor na fase de grupos).
- **Sensibilidade a desfalques**: "se a estrela X não jogar, P(V) cai de a→b" — usa `desfalques.py`, vira ferramenta de leitura de notícia.
- **Backtest por confederação/era**: medir se o edge é uniforme (a altitude, p.ex., é CONMEBOL).

---

## 10. Roadmap (ordem de prioridade e dependências)

**Fase 0 — Higiene e laço de validação (agora, sem portão; destrava medição).**
Congelar curva PIT (P5) → unificar config+hash (P11) → teste de skill no CI (P12) → **liquidar o registro prospectivo** (P13). *Por quê primeiro:* sem curva PIT e sem skill-test, qualquer mudança de (b) é medida sobre base contaminada; sem liquidar o registro, não há juiz real da Copa. Baixo esforço, alto valor de método.

**Fase 1 — Subir o teto com fonte independente (a maior alavanca).**
**Ligar a perna AD** (P1/P2 — já validada) → integrar **odds de mercado** quando houver captura. *Depende de:* Fase 0 (medir limpo). *Destrava:* sair do teto do `dr`; benchmark de mercado. É aqui que o Brier de fato cai abaixo do lookup.

**Fase 2 — Calibração fina e tail.**
`T_base` (P9) → isotônica por faixa (P7) → forma saturante (P6). *Depende de:* Fase 1 (recalibrar sobre o modelo novo). Ganhos menores, mas corrigem vieses medidos.

**Fase 3 — Incerteza honesta.**
σ Glicko (P3) → **propagar σ no Monte Carlo** (P4). *Depende de:* Fase 1. Torna banda/confiança/título calibrados — crítico para "uso ao vivo".

**Fase 4 — Dados de jogo e operação contínua.**
Escalações/desfalques estruturados → xG prior (P + dados) → monitor de drift + recalibração agendada. *Depende de:* fontes; é o que sustenta uso recorrente entre rodadas.

---

## 11. Conclusão

**Pontos fortes (técnicos).** Disciplina de processo rara: contrato congelado e auditado, ADRs, pipeline point-in-time honesto, e — o diferencial — um **portão estatístico pareado com IC** que efetivamente barra fatores sem evidência (calor, estilo, Dixon-Coles, recalibração: todos construídos e rejeitados com número). A coerência [0,1] é por construção; a calibração é boa de verdade (ECE 0,026). Reproduzi todas as contas centrais e elas batem.

**Pontos fracos (técnicos).** O aparato que daria sofisticação está **parcialmente inerte**: o ensemble combina duas leituras do mesmo `dr` (corr 0,9966), a incerteza base é degenerada (σ_R~40) e não é propagada no torneio, e o modelo **empata com o teto não-paramétrico do `dr`** — sinal de que o núcleo paramétrico está esgotado. O ganho de skill sobre o Elo interno é real mas pequeno (+0,003), e o benchmark "Elo público" é na verdade interno, não externo/mercado.

**O que mais chamou atenção.** Duas coisas opostas. (1) A **honestidade**: o repositório documenta seus próprios vazamentos (curva in-sample), rejeita os próprios candidatos e admite "Brier ~0,60 não é vantagem". É auditoria embutida. (2) O **paradoxo da conclusão do vault**: as notas concluem "o núcleo está no teto, pare de adicionar fórmula, ganho vem de dados" — e isso é **quase** certo, mas há uma exceção construída e validada ignorada: a **perna ataque/defesa não-Elo passa o portão (+0,0039, IC>0) e está OFF**. Ela não é "mais fórmula no núcleo do `dr`"; é uma **fonte de informação independente** (gols), exatamente o que falta. O caminho mais curto para subir o teto **já está no repositório, desligado**.

**Nível técnico.** Engenharia/processo **alto**; modelagem estatística entregue **médio** (baseline correto e honesto, com potencial não acionado).

**Preparo real para a Copa.** Como **ferramenta de estudo** que produz 1X2 calibrados e um Monte Carlo plausível: **utilizável, com ressalvas** (títulos superconfiantes por falta de propagação de σ). Como **sistema de previsão sério**: **quase** — falta acionar a perna independente (Fase 1), fechar o laço prospectivo (Fase 0) e calibrar a incerteza do torneio (Fase 3). A arquitetura suporta; falta executar 3 itens de baixo esforço.

**Teto atual e caminho mais curto (explícito).** Teto hoje ≈ **Brier 0,559 em torneios** (informação do `dr`, calibrado, no nível do lookup). O caminho mais curto para superá-lo, em ordem: **(1) ligar a perna AD** (já validada, +0,0039) → **(2) integrar odds de mercado** (sinal externo, benchmark real) → **(3) propagar σ no torneio** (calibra o produto-Copa). Os três respeitam custo zero, execução local e auditabilidade; nenhum exige ML opaco. O resto — mais ajuste paramétrico no núcleo — o próprio portão já mostrou que não move o ponteiro.

---

### Apêndice — comandos para reproduzir esta auditoria
```
cd scm_analytics
python -m scm.backtest_harness --major     # Brier 0,5590; vs uniforme/Elo/lookup com IC
python -m scm.backtest_harness             # todos: Brier 0,5365
python -m scm.report --major               # ECE 0,0260; superconfiança 0,8–0,9
python -m scm.altitude                     # portão altitude +0,0492 IC[+0,029,+0,069]
python -m scm.attack_defense --w-ad 0.30   # portão AD +0,0039 IC[+0,0028,+0,0051] (ADOTAR)
python -m scm.dixon_coles                  # ρ=-0,06, BTTS ΔBrier<0 (rejeita)
# correlação das pernas (0,9966) e λ_B<0 no tail: ver script de verificação da auditoria
```

*Auditoria 2026-06-20. Não altera código. Todas as conclusões citam arquivo:linha ou nota; números marcados [verificado] (reproduzidos no `scm.sqlite` local) ou [inferido] (lidos). pytest não pôde rodar no ambiente da auditoria (sem o pacote/rede) — os 134 testes foram lidos, não executados. Probabilidades, nunca certezas.*
