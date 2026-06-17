---
tags: [camada1, planejamento, historico]
status: historico
tipo: planejamento
data: 2026-06-15
aliases: ["Modelo v4"]
---

# Camada 1 — Planejamento Matemático e de Dados (v4 — propagação inteira e contrato↔prática)
**Projeto:** Sistema de previsão de partidas — Copa do Mundo 2026 (EUA/Canadá/México)
**Data:** 2026-06-15 · **Status:** planejamento (sem código) · **Custo-alvo:** R$ 0
**Supersede:** [[camada1-planejamento-v3]] (v3, 2026-06-15). Base da revisão: [[camada1-revisao-v3]] (3ª rodada, achados A1–A11).

> Convenções: probabilidades em [0,1]; V/E/D = vitória A / empate / vitória B; λ = gols esperados; dr = diferença de Elo (A − B, já com mando); W_e = expectativa de pontuação do Elo; σ_R = erro-padrão do rating; **σ_ajuste = erro-padrão dos ajustes (forma + desfalque) ▲v4**; σ_dr = erro-padrão da diferença total. **[a calibrar]** = estimativa educada a fixar no backtest, não constante da literatura. Marcador **▲v4** sinaliza o que mudou em relação à v3 e por quê. **Todas as correções da v2 (saturação de gols, mando histórico) e da v3 (coerência [0,1], incerteza de rating) continuam válidas e integradas** — a v4 só fecha o que a v3 deixou *pela metade* ou *fora do contrato*. Tabelas numéricas reconferidas em código (ver §3.12, §8, §9).

---

## 0. Changelog v4 (o que mudou e por quê)

A v3 foi auditada em [[camada1-revisao-v3]] (3ª rodada). A auditoria confirmou que a **aritmética está limpa** (3ª verificação independente) e a coerência [0,1] se sustenta, mas apontou **correções aplicadas pela metade** e **lacunas contrato↔prática**. A v4 promove os patches aprovados ao contrato congelado. Nenhum quebra a filosofia das versões anteriores; todos aumentam a **honestidade da incerteza** e fecham a distância entre o que o documento especifica e o que as execuções já fazem à mão.

| # | Correção | Severidade | Seções | Origem |
|---|---|---|---|---|
| D1 | **Propagar a leitura Elo-direto INTEIRA.** A v3 integrava `W_e` sobre σ_dr mas congelava a curva de empate e o cap no ponto `dr0`. Agora V, E e D saem do **mesmo** Monte Carlo sobre `dr ~ N(dr0, σ_dr)`, e a **banda** vira **percentis 16/84 da mesma amostra** (um cálculo, não dois). Sem isso, o minnow tinha o empate sub-propagado (medido: +1,9 p.p. de P(E) em dr=572, σ=250). | 🟡 coerência | 3.12, 9, 10 | A1, A7 |
| D2 | **Forma de `T_m` escolhida por backtest, não linear por decreto.** A C5 (v3) libertou a forma do `GD` mas deixou `T_m = T_base + κ·|dr|/100` linear — a mesma premissa que a C5 condenou. Em código, linear×linear dá **λ_B = −0,27 em dr=900** (negativo, só mascarado pelo clamp 0,2). A v4 deixa o backtest escolher a forma do *total* também (linear / côncava / saturação suave), acoplada à forma do GD. | 🟡 modelagem | 8, 11.1 | A2 |
| D3 | **`σ_ajuste` entra em σ_dr.** A v3 derivava σ_R só de propriedades do *rating*; a incerteza dos *ajustes* (forma, e sobretudo desfalque com escalação não confirmada, que chega a −57) ficava fora — e as execuções a injetavam à mão em σ_R. Agora é termo do contrato: `σ_dr = √(σ_R(A)²+σ_R(B)²+σ_ajuste(A)²+σ_ajuste(B)²)`. | 🟡 modelagem | 3.12, 13, 14 | A3 |
| D4 | **Split direcional de desfalque no baseline.** A porta única (ΔE simétrico) sobe λ_contra para *qualquer* ausência — certo para zagueiro/goleiro, **sinal errado para atacante**. A v4 usa o campo `setor` (já no JSON): ausência ofensiva corta λ_pró; defensiva/goleiro infla λ_contra. Deixa de ser "refinamento futuro". | 🟡 modelagem | 8, 11.1, 13 | A4 |
| D5 | **Independência do AD resolvida de verdade.** A C6 (v3) resolveu o fork no papel, mas ancorava `ATA/DEF` num prior ∝ R_Elo. Se o AD é a 3ª leitura "independente" do ensemble com prior = Elo, a independência é fictícia. A v4: **se membro do ensemble, prior do AD NÃO é Elo** (prior de gols/xG histórico); **se gerador primário, não há `P_ad`** e a `consist_int` é rotulada como consistência interna. | 🟡 contrato | 4, 9, 11.2 | A5 |
| D6 | **Patches de coerência textual e notas honestas.** "Encolhe para **½**" (não 1/3 — o limite verificado de E[W_e] é 0,5; o 1/3 é da V/E/D a jusante). Reconciliação de `P(E)` matriz-vs-curva declarada **pré-requisito** da Dixon-Coles (a DC sobe 0×0/1×1 → muda P(E)). `σ_dr = RSS` declarada **aproximação** (ignora covariância de rating intra-confederação). Triplo-uso de σ_dr (ponto, banda, confiança) declarado **correlacionado**, não três sinais independentes. | ⚪ | 3.12, 3.2, 9, 14 | A6, A8, A9, A10 |
| D7 | **Fontes + registro.** Mercados de previsão **Kalshi/Polymarket** entram como benchmark multiagente (resolvem a fraqueza "1 casa" da §3.7; já usados à mão em URU×KSA). **Wikidata** sistematiza a data de nomeação do técnico (regime). **StatsBomb** ganha papel de **% de gols de bola parada** (ataca o gap BTTS do azarão). CSV passa a ter `sigma_dr`, `banda_pv`, `hash_inputs` + filtro obrigatório por `versao_modelo`; `setor` vira obrigatório no JSON de desfalque. | ⚪ → dados | 6, 13, 15 | A11 |

Princípio mantido desde a v1: **nada de certezas — só probabilidades**; tudo roda local; nenhuma previsão lê a internet no momento do cálculo (snapshot diário em disco). **Esta versão passa a ser `v4.0`. A coerência [0,1] segue garantida; a acurácia segue não-comprovada até o 1º backtest.**

---

## 1. Visão geral do sistema em camadas

| Camada | Função | Estado |
|---|---|---|
| 1 | Motor matemático e dados base | **este documento (v4)** |
| 2 | Coleta e normalização (CSV/JSON → SQLite local) | próxima |
| 3 | Detector de notícias/lesões/desfalques | depois da 2 |
| 4 | Sistema de previsão (ensemble) | consome 1–3 |
| 5 | Geração de insights/explicações | consome 4 |
| 6 | Interface local | última |

A Camada 1 define **contratos matemáticos** (entradas, fórmulas, saídas). As demais só alimentam ou consomem esses contratos. Mudança em qualquer fórmula desta camada = nova `versao_modelo`.

## 2. Objetivo da Camada 1

Especificar o pipeline que transforma dados públicos em: P(V), P(E), P(D) **com banda de incerteza por percentis** (▲v4), λ_A, λ_B, placares mais prováveis, P(over 2.5), P(ambos marcam), ajuste **direcional** por desfalques (▲v4), score de confiança e métricas de validação. Critério de pronto: qualquer dev implementa a Camada 4 lendo só este documento; cada número de saída é rastreável a uma fórmula e a um dado de entrada (auditabilidade); **toda probabilidade fica em [0,1] por construção**; e **a incerteza dos inputs (rating E ajustes) é propagada de forma completa e consistente** (▲v4).

## 3. Cálculos recomendados

Pipeline (não modelos paralelos independentes): Elo (+ forma + desfalques + mando) estima a *diferença* de força **e sua incerteza total**; fatores ofensivos/defensivos estimam o *total* e (no upgrade C6/D5) a *direção* de gols; Poisson converte em distribuição de placares; um mini-ensemble combina leituras; odds e mercados de previsão são benchmark externo.

### 3.1 Elo Rating (espinha dorsal) — mantido da v3
**Funcionamento.** Cada seleção tem rating R **e erro-padrão σ_R**. Após cada jogo:
```
R_novo = R_antigo + K · G · (W − W_e)
W_e = 1 / (1 + 10^(−dr/400))        dr = R_A − R_B + mando
W  = 1 vitória · 0.5 empate · 0 derrota
K  = 60 Copa · 50 continentais · 40 eliminatórias · 30 Nations League · 20 amistosos
G  = 1 (margem ≤1) · 1.5 (margem 2) · (11+N)/8 (margem N ≥ 3)
```
**Mando (mantido da v2):** dois parâmetros distintos, nunca fundidos.
```
mando = H_hist (=100, eloratings ou fit)  se construindo o Elo histórico E jogo NÃO neutro
      = H_host2026 (=60 [a calibrar])      se previsão 2026 E anfitrião em solo próprio
      = 0                                   jogo neutro
```
`H_hist` aplica-se a **TODO** jogo não-neutro do martj42. Inicialização em 1500; ratings com <30 jogos são **provisórios**. Metodologia do World Football Elo Ratings; sanidade: dr=+100 → W_e≈0.64; dr=+300 → W_e≈0.85. Benchmark contra eloratings.net (±25 nas top-30) e international-football.net. **Limitações.** Reage devagar a troca de geração/técnico (vira σ alargado, não nota); amistosos ruidosos; não separa ataque de defesa (daí 3.4); estreantes mal calibrados (σ_R alto).

### 3.2 Poisson (gerador de placares) — mantido da v3 + ▲v4 (D6)
Gols ~ Poisson independente: `P(X=k)=e^(−λ)λ^k/k!`. Matriz `M[i][j]=P_A(i)·P_B(j)`, **i,j = 0..10**; resíduo (>10) distribuído proporcionalmente na borda.
```
P(V)=Σ M[i][j] (i>j)   P(E)=Σ M[i][i]   P(D)=Σ M[i][j] (i<j)
P(over 2.5)=1 − Σ M[i][j] (i+j ≤ 2)
P(ambos marcam)=(1−e^(−λ_A))·(1−e^(−λ_B))
Placares prováveis = top-k células de M
```
**▲v4 (D6) — duas P(E) na arquitetura, a reconciliar.** Existe um `P(E)` da **diagonal da matriz** (leitura `P_poisson`) e outro da **curva empírica** `P(E|dr)` com cap (leitura `P_elo`, §9). São leituras distintas por design. **Mas quando a Dixon-Coles entrar (11.2)**, o termo τ (ρ<0) **sobe 0×0 e 1×1** — ambos empates — e a `P(E)` da matriz **aumenta**, divergindo mais da curva e reinteragindo com o cap C1. Pré-requisito de entrada da DC: **recomputar V/E/D, over 2.5 E BTTS** da matriz corrigida e reconciliar as duas fontes de P(E) (não só over/BTTS, como a v3 dizia). **Limitações.** Independência entre ataques é falsa — subestima 0×0/1×1; a DC corrige. Não modela prorrogação/expulsões/estado de jogo. **Mata-mata:** V/E/D = tempo normal; avanço = `P(V)+P(E)·(0.5+ε·sinal(dr))`, ε≈0.03 [a calibrar].

### 3.3 Forma recente — mantido da v3 (alimenta σ_ajuste em 3.12 ▲v4)
Janela das **últimas 10 partidas**, peso temporal e desconto de amistosos:
```
w_i = 0.9^(idade_em_meses) · (1.0 oficial · 0.5 amistoso)
PPJ_pond = Σ w_i · pontos_i / Σ w_i
ΔE_forma = 15 · (PPJ_pond − PPJ_esperado)    cap ±30 Elo  [a calibrar]
```
Métrica **ajustada a adversário** (comparar com o esperado pelo Elo do adversário). **Dependências (v2):** (a) `PPJ_esperado = 3·P(V)+1·P(E)` exige a curva de empate `P(E|dr)` (com a restrição C1); (b) no backtest, usar **Elo point-in-time** (anti look-ahead). Risco de dupla contagem com o Elo → cap e peso baixos. **▲v4:** a **dispersão da forma na janela** alimenta `σ_ajuste` (3.12) — forma volátil = input mais incerto.

### 3.4 Força ofensiva/defensiva — mantido da v3 + ▲v4 (D5)
**Baseline (total, mantido).** Sobre a janela ponderada:
```
tendência_gols_T = (gols_pró + gols_contra por jogo de T, ajustado pelo Elo médio dos adversários) / média_internacional
estilo_T = shrinkage(tendência_gols_T → 1.0, força = n_jogos/(n_jogos+10))
```
**▲v4 — papel do ATA/DEF (D5, refina C6).** O upgrade Dixon-Coles (11.2) gera λ **direcional**. O contrato escolhe **uma** função para ele: **gerador primário** de λ **XOR** leitura independente `P_ad` do ensemble. **E mais (D5):** se for `P_ad` (membro do ensemble), seu **prior NÃO pode ser ∝ R_Elo** — usar prior de **gols/xG histórico** (StatsBomb) — senão `P_ad` e `P_elo` compartilham backbone e a "diversidade" é fictícia. **Limitações.** Gols ≠ qualidade de chance (sem xG ao vivo); ajuste por adversário grosseiro via Elo médio.

### 3.5 Mando de campo / campo neutro — mantido da v2
```
H_host2026 = +60 Elo  para anfitrião jogando no próprio país   [a calibrar]
           = 0         nos demais jogos (neutro)
```
Distinto de `H_hist` (=100, construção do Elo). Caso "quase-casa" (México em solo americano): `bonus_mando_override` manual. Altitude/calor: diagnóstico (3.11), não λ na baseline.

### 3.6 Lesões e desfalques — resumo ▲v4 (D4)
Representação completa na **seção 13**. Entrada por JSON manual (detector é Camada 3). **▲v4:** o campo `setor` ("ataque"/"defesa"/"goleiro"), que já existia no JSON, passa a ser **obrigatório e usado**: define se o desfalque corta λ_pró (ofensivo) ou infla λ_contra (defensivo/goleiro). Antes a porta era simétrica (sinal errado para ausência ofensiva).

### 3.7 Odds e mercados de previsão (benchmark) ▲v4 (D7)
```
p_i = (1/odd_i) / Σ_j (1/odd_j)        (de-vig proporcional; Shin fica p/ futuro)
```
**Benchmark, não input.** Peso ≤ 0.20 no ensemble. **▲v4 — mercado de previsão (Kalshi/Polymarket):** preço público multiagente é **benchmark mais forte que a odd de uma casa** (a v3 já alertava que "1 book é fraco"; URU×KSA usou Kalshi 68% à mão). Entra como `P_mercado` preferencial **ou** 2ª linha de corroboração, por **captura manual com timestamp** (ToS restringe scraping; não é API livre). **Realidade (2026-06):** segue sem API de odds de Copa gratuita garantida; `oddspapi.io` ainda **a validar**. **Cautela:** mercado de previsão pode ecoar o mesmo Elo público — não é sinal onisciente; peso e rótulo "estudo" mantidos.

### 3.8 Ensemble — resumo ▲v4 (D1, D5)
Detalhe em 9–10. Leituras `P_poisson` e `P_elo` **compartilham o Elo**; diversidade real vem do mercado e, no upgrade D5, da leitura AD **se** seu prior não for o Elo. **▲v4:** a leitura Elo-direto entra **inteira e propagada** (V, E, D do mesmo MC), não com o empate congelado.

### 3.9 Nível de confiança — resumo ▲v4 (D3, D6)
Seção 14. Confiança é metadado, não probabilidade. Gate `g_rating` (incerteza derruba a confiança). **▲v4:** o `g_rating` passa a refletir `σ_dr` **com σ_ajuste** (escalação não confirmada derruba a confiança pelo contrato, não à mão); e fica **declarado** que ponto, banda e confiança usam a *mesma* σ_dr (são correlacionados, não três confirmações).

### 3.10 Validação — resumo ▲v4 (D7)
Seção 15. Brier + LogLoss + RPS + calibração, IC bootstrap, registro pré-jogo imutável **com `sigma_dr`, `banda_pv`, `hash_inputs`** e **filtro por versão** (exclui `*-prelim`).

### 3.11 Contexto físico e xG (diagnóstico) — mantido da v3
Variáveis gratuitas e locais; **entram como diagnóstico/modificador de confiança; viram termo de λ só se passarem no portão de backtest** (16): xG (StatsBomb, WC 2018+2022, Euro, WWC; licença não-comercial); fadiga/descanso e descanso diferencial; viagem (haversine entre sedes); altitude (Cidade do México ~2.240 m); calor (Open-Meteo); idade média/caps (Wikipedia); **flag de troca de técnico** → alarga σ_R (agora via Wikidata, D7). Não perseguir (sem fonte gratuita estruturada p/ seleções): posse de bola, distância percorrida.

### 3.12 Incerteza total `σ_dr` e propagação ▲v4 (D1, D3, D6)
Tratar o input como **distribuição**, não ponto — e agora incluir a incerteza dos **ajustes**, não só do rating.

```
σ_R(T)      = base(n_jogos efetivos, recência)
              + estreante/<30 jogos + diversidade de oposição baixa
              + técnico novo há poucos jogos + elenco pouco benchmarkável   [a calibrar]
σ_ajuste(T) = sqrt( (a·Σ|ΔE_i| de desfalques em DÚVIDA)²       # ▲v4 (D3): escalação não confirmada
                  + (b·n_meio_tier)²
                  + (c·desvio_forma_na_janela)² )              # a,b,c [a calibrar]
σ_dr        = sqrt( σ_R(A)² + σ_R(B)² + σ_ajuste(A)² + σ_ajuste(B)² )   # RSS — APROXIMAÇÃO (D6/A9)
```
**▲v4 (D6/A9):** a RSS **ignora a covariância** dos erros de rating (não-nula intra-confederação, onde A e B jogaram entre si e contra os mesmos adversários). Sinal e magnitude **incertos**; corrigível só com a matriz de covariância do ajuste de rating (Camada 2). Até lá, declarar como aproximação.

**Propagação (Jensen) ▲v4 (D1).** A expectativa Elo é côncava acima de 0.5; integrar sobre a incerteza **encolhe `W_e` para ½** (▲v4/D6 — *não* 1/3; o 1/3 é o neutro da V/E/D já com o split de empate). **A v4 propaga a leitura V/E/D inteira no mesmo MC** (a v3 congelava o empate):
```
amostrar dr_s ~ Normal(dr0, σ_dr),  s = 1..S   (S=10^4)
we_s = W_e(dr_s)
pe_s = min( P_E_empírico(dr_s),  2·min(we_s, 1−we_s) − ε )   # cap POR amostra (não no ponto)
pv_s = we_s − pe_s/2 ;  pd_s = 1 − pv_s − pe_s
P_elo(V/E/D) = média(pv_s, pe_s, pd_s)                       # leitura inteira propagada
banda(x)     = [percentil_16, percentil_84](p{x}_s)         # banda = MESMA amostra (D1/A7)
```

E[W_e] propagado (mantido da v3 — reconferido, MC 2×10⁶):

| dr0 | σ_dr=0 | 75 | 150 | 250 |
|---:|---:|---:|---:|---:|
| 150 | 0.703 | 0.696 | 0.679 | 0.651 |
| 300 | 0.849 | 0.841 | 0.819 | 0.781 |
| 500 | 0.947 | 0.942 | 0.929 | 0.898 |

**Efeito do D1 — propagar o empate junto (leitura Elo-direto V/E/D, reconferido em código):**

| caso (dr0) | σ_dr | P(V) | P(E) | P(D) | banda P(V) [p16,p84] |
|---|---:|---:|---:|---:|---:|
| ESP×CPV (572) — ponto v3 | — | 0.928 | 0.072 | 0.000 | — |
| ESP×CPV (572) — propagado v4 | 250 | 0.881 | **0.090** | **0.028** | [0.781, 0.982] |
| URU×KSA (269) — ponto | — | 0.732 | 0.186 | 0.082 | — |
| URU×KSA (269) — propagado v4 | 92 | 0.719 | 0.186 | 0.095 | [0.630, 0.808] |

A v3 encolhia a vitória mas mandava quase tudo para P(D); a v4 distribui corretamente para **empate e derrota** do azarão mal-medido (no extremo, P(E) sobe ~1–2 p.p.). É de graça (mesmo MC) e principiado. Continua atrás do portão de backtest; é a adição de maior retorno acumulada do projeto.

## 4. Cálculos fora da baseline (e por quê) ▲v4 (D5)

**Upgrade priorizado #1 (logo após o 1º backtest): ataque/defesa Poisson + Dixon-Coles** (C6). **▲v4 — regra do fork + independência (D5):** se virar **gerador primário** de λ, **não** existe `P_ad` (o 3º sinal é só o mercado, e `consist_int` é rotulada como consistência interna); se a baseline GD/T_m continuar gerando λ, ATA/DEF entra como `P_ad` independente **com prior de gols/xG histórico, NÃO ∝ Elo**. Decidir por Brier/RPS com IC. **Insight near-term:** Monte Carlo do torneio + **cenários de classificação determinísticos**. Continuam fora: Poisson bivariado; xG ao vivo (sem fonte gratuita p/ 48 seleções); modelos hierárquicos bayesianos (matam auditabilidade); ML/boosting (overfit garantido); ratings por jogador; clima/altitude/viagem como termo de λ (diagnóstico antes); de-vig de Shin.

## 5. Dados necessários por cálculo ▲v4

| Cálculo | Dado | Granularidade | Histórico mínimo |
|---|---|---|---|
| Elo (+ H_hist) + σ_R | data, times, placar, competição, flag neutro, home/away | por jogo | 1950+ (ideal 1872+) |
| Forma (+ dispersão p/ σ_ajuste ▲v4) | idem + data p/ decaimento + curva P(E|dr) | por jogo | últimos 10/time |
| Estilo / Ataque-Defesa | placares + Elo do adversário na data (+ prior xG se P_ad ▲v4) | por jogo | últimos 10–20/time (full p/ AD) |
| Mando 2026 | estádio, cidade, país-sede | por jogo da Copa | só 2026 |
| Poisson | λ_A, λ_B (derivados) | por jogo | — |
| Desfalques (+ `setor` obrigatório ▲v4) | lista de ausentes + tier + setor + status dúvida | por jogo | elenco atual |
| Odds / mercado de previsão ▲v4 | 1X2 decimal + preço Kalshi/Polymarket + timestamp | por jogo | só 2026 (prospectivo) |
| σ_R / regime | nº jogos, diversidade de oposição, semanas do técnico, % liga local | por seleção | janela efetiva |
| σ_ajuste ▲v4 | ΔE em dúvida, n_meio_tier, desvio de forma | por jogo | — |
| Contexto físico (diag.) | descanso, viagem, altitude, temp, idade | por jogo | 2026 + histórico p/ calibrar |
| xG + % bola parada ▲v4 (backtest) | xG e tipo de jogada por gol (StatsBomb) | por jogo | torneios cobertos |
| Validação | resultado final + tudo registrado pré-jogo + sigma_dr + banda + hash_inputs | por jogo | acumula |

## 6. Fontes gratuitas recomendadas (verificadas em 2026-06-15) ▲v4 (D7)

| Fonte | Dado | Grátis? | Key? | Limitações | Confiab. | Papel | Fallback |
|---|---|---|---|---|---|---|---|
| **martj42/international_results** | resultados 1872–2026, torneio, flag neutro, home/away | Sim | Não | atualização por PR (lag horas–dias) | Alta | **nº 1** | openfootball; manual |
| **fixturedownload.com** (wc-2026) | calendário+resultados; base p/ descanso/viagem | Sim | Não | só jogos | Alta | **Sim** | openfootball |
| **football-data.org** | jogos, resultados, classificação (WC no free) | Sim (free) | Sim (grátis) | 10 req/min; sem escalações no free | Alta | automação de resultados | martj42 + manual |
| **Elo próprio** (do martj42, c/ H_hist) + σ_R | rating de força + incerteza | Sim | Não | depende do dataset base | Alta (auditável) | **recomendado** | snapshot eloratings.net |
| **eloratings.net** / **international-football.net** | Elo benchmark / 2º benchmark | Sim | Não | sem API; SPA sobre TSV / metodologia difere | Alta / Média | sanidade | calcular próprio |
| **StatsBomb Open Data** | eventos + **xG** + 360 + **tipo de jogada (bola parada)** ▲v4; WC 2018 e 2022, Euro, WWC | Sim | Não | sem 2014/Copa América; não ao vivo; licença **não-comercial** | Alta | backtest xG + prior de estilo + **piso de λ do azarão** (3.2/D7) | FBref (visual) |
| **Kalshi / Polymarket** ▲v4 (nova) | preço-mercado de previsão (prob. implícita) 1X2/avanço | Sim (leitura pública) | Não p/ ler | cobertura/liquidez variam; ToS restringe scraping → **captura manual** | Média-alta (multiagente) | **benchmark de mercado > 1 casa** (3.7) | odd de 1 casa |
| **Wikidata (SPARQL)** ▲v4 (papel novo) | coords/elevação de estádios **+ data de nomeação do técnico** | Sim | Não | semiestruturado | Média-alta | redundância geo + **regime (semanas no cargo)** | Open-Meteo; infobox Wikipedia |
| **RealGM — xG Tracker WC 2026** | xG por jogo da Copa 2026, pós-jogo | Sim | Não | terceiro de fonte única; copiar à mão | Média (validar vs StatsBomb) | xG **in-tournament** (manual) | StatsBomb (histórico) |
| **Open-Meteo (+Elevation/Geocoding)** | temp/umidade; altitude; coords das sedes | Sim | **Não** | uso não-comercial; efeito pequeno | Alta | calor/altitude/viagem | Wikidata; hardcode |
| **Wikipedia — elencos 2026** | convocações, idade, caps, clube, técnico | Sim | Não | parsing manual | Alta na Copa | convocações/idade/regime | site FIFA |
| **ClubElo (clubelo.com)** ▲v4 (nova, baixa prio.) | Elo de **clubes** (CSV grátis) | Sim | Não | só clubes; prior de talento via clube dos convocados | Média (clubes) | regularizador indireto do minnow (alt. ao valor de mercado) | tiers manuais |
| **openfootball / football.json** ▲v4 (redundância) | resultados/calendário em JSON | Sim | Não | cobertura/atualização variam | Média | **redundância de snapshot** | martj42 |
| **oddspapi.io** (a validar) | odds 1X2 multi-casa + histórico (free tier alegado) | Alegado | Sim | autopromoção do vendor; cobertura de Copa não confirmada | A validar | candidato; **NÃO** depender até testar | captura manual |
| **The Odds API** | odds | **Não serve** (25/dia, NBA/MLB) | — | sem futebol no free | — | **Não** | captura manual |
| **FBref / Transfermarkt** | minutos, valor de mercado, xG visual | Visualização | Não | **ToS restringe scraping** | Alta | só consulta manual (tiers, prior de valor) | tiers manuais |
| **Lesões/desfalques** | — | — | — | **Sem fonte estruturada gratuita p/ 48 seleções** | — | — | JSON manual; RSS na C3 |

Lacunas reconfirmadas (não inventar): odds gratuitas via API (segue captura manual; Kalshi/Polymarket e `oddspapi.io` por captura/validação, não API livre) e lesões estruturadas (JSON manual + RSS na Camada 3). **A FIFA/Coca-Cola World Ranking NÃO é 2º sinal independente** — desde 2018 é baseada em Elo, correlacionada com o backbone. **APIs pagas (Sportmonks, TheStatsAPI, iSports, API-Football) violam o custo-alvo R$ 0 — fora de escopo.**

## 7. Dados que precisarão ser manuais no início
Snapshot do eloratings.net + international-football.net (sanidade, 1x pré-torneio); **tiers + setor de jogadores** só p/ as ~16 seleções com chance real e sob demanda; **estimativa inicial de σ_R/σ_ajuste/regime** p/ o shortlist; **JSON de desfalques com `setor`** por jogo; **odds 1X2 + preço Kalshi/Polymarket** digitados pré-jogo com timestamp; override de mando (México em solo americano); convenção de pênaltis (martj42 registra placar ao fim da prorrogação + `shootouts.csv`).

## 8. Fórmula inicial do modelo (pipeline completo) ▲v4 (D1–D4)

```
ENTRADAS: R_A,σ_A · R_B,σ_B (Elo próprio, já com H_hist) · forma · estilo (of/def) · desfalques c/ setor · flag mando 2026

1) Elo ajustado:    R'_T = R_T + ΔE_forma(T) + ΔE_desfalques_DEF(T)        # ▲v4 (D4): só o setor DEFESA/GOLEIRO entra via dr
2) Diferença:       dr   = R'_A − R'_B + H_host2026                       # 60 se anfitrião, senão 0
   Incerteza:       σ_dr = sqrt(σ_A² + σ_B² + σ_ajuste_A² + σ_ajuste_B²)  # ▲v4 (D3): inclui incerteza dos ajustes
3) Saldo esperado:  GD   = f(dr)                                          # f escolhida por backtest (C5)
4) Total esperado:  T_m  = g(dr) · estilo_A · estilo_B                    # ▲v4 (D2): g escolhida por backtest, NÃO linear por decreto
                                                                          #   candidatos g: T_base+κ|dr|/100 | côncava | saturação suave
5) Gols base:       λ_A0 = (T_m + GD)/2     λ_B0 = (T_m − GD)/2
6) Ajuste ofensivo: λ_A  = λ_A0 · (1 − δ_ata_A)   λ_B = λ_B0 · (1 − δ_ata_B)   # ▲v4 (D4): desfalque OFENSIVO corta o λ_pró do time
                                                                          #   (defensivo já entrou no passo 1 via dr); δ_ata de tier×setor [a calibrar]
   Piso honesto:    λ ← max(λ, λ_min)                                     # regularização; desnecessário se 11.2 (AD, λ=exp>0) for primário
7) Matriz Poisson:  M[i][j] = Pois(i;λ_A)·Pois(j;λ_B),  i,j = 0..10 (resíduo na borda)
8) Saídas Poisson:  V/E/D, over 2.5, BTTS, top placares
9) Leitura Elo-direto PROPAGADA INTEIRA: V/E/D + banda por percentis (3.12/D1, §9)
10) Ensemble (clamp por leitura) + banda por percentis: §§9–10
```

**Forma de GD e T_m — escolher no backtest, JUNTAS (▲v4 D2).** São acopladas em λ; não libertar uma e impor a outra. Linear e saturação suave **coincidem onde há dados** (|dr|≤300) e divergem no **tail esparso** — e só a saturação mantém `λ_B > 0` sem clamp (reconferido em código):

| dr | GD lin | GD tanh | T_m lin | T_m sat | λ_B (lin/lin) | λ_B (tanh/sat) |
|---:|---:|---:|---:|---:|---:|---:|
| 300 | 1.35 | 1.30 | 2.90 | 2.89 | 0.77 | 0.80 |
| 600 | 2.70 | 2.35 | 3.20 | 3.15 | 0.25 | 0.40 |
| 900 | 4.05 | 3.07 | 3.50 | 3.36 | **−0.27** | **0.15** |
| 1100 | 4.95 | 3.38 | 3.70 | 3.47 | **−0.62** | 0.05 |

Decidir por Brier/RPS **com IC** (point-in-time), restrição monótona e **extrapolação cautelosa além do suporte** (alargar σ_dr quando |dr| sai da faixa observada). θ, κ, T_base saem de regressão, não de palpite.

## 9. Ensemble e leitura Elo-direto ▲v4 (D1, D5)

**Curva de empate com restrição (C1), agora propagada (D1).** `P(E|dr)` empírico do martj42 em faixas de |dr| (~26% com |dr|<50 caindo a ~15% com |dr|>300), **truncado** e **integrado sobre σ_dr no mesmo MC** (§3.12). O cap garante coerência **por amostra**:
```
pe_s = min( P_E_empírico(dr_s),  2·min(we_s, 1−we_s) − ε )      # garante P(V),P(D) ∈ [0,1] em CADA amostra
P_elo(V/E/D) = média sobre s ;  banda = percentis 16/84         # ▲v4 (D1/A7): ponto e banda do MESMO sample
```

**Pesos (mantidos da v3):**

| Componente | Peso c/ odds | Peso s/ odds |
|---|---|---|
| P_poisson | 0.45 | 0.56 |
| P_elo (propagado) | 0.35 | 0.44 |
| P_mercado (odds e/ou Kalshi) | 0.20 | 0.00 |

**▲v4 — clamp por leitura (C2):** cada leitura clampada em [0.02,0.96] e renormalizada **antes** do pool. **Fork AD (C6+D5):** se 11.2 for primário, não há P_ad e o 3º sinal é só o mercado; se a baseline gerar λ, AD vira `P_ad` independente **com prior de gols/xG (não Elo)** e os pesos viram ~0.35/0.25/0.20/0.20. **▲v4 (D6):** ponto, banda e confiança usam a **mesma** σ_dr — são correlacionados, não confirmações independentes. Após ≥30 jogos, otimizar pesos minimizando Brier (grid), congelados por fase.

## 10. Cálculo da probabilidade final V/E/D ▲v4 (D1)

```
para cada leitura k:  P_k(x) ← clamp(P_k(x), 0.02, 0.96); renormalizar          # por leitura (C2)
P_final(x) = Σ_k w_k·P_k(x),  x ∈ {V,E,D};  renormalizar
clamp final [0.02,0.96] + renormalizar (iterar 1–2x)
```

**▲v4 — banda de probabilidade por percentis (D1/A7):** publicar, além do ponto, `[percentil_16, percentil_84]` da leitura propagada (a leg de mercado não se move com dr → a banda do ensemble é mais estreita que a de `P_elo` sozinha, o que é correto). **Um cálculo, consistente com o ponto** — não mais um pushforward ±σ separado. No mata-mata, `P(avança) = P(V)+P(E)·(0.5+0.03·sinal(dr))`, V/E/D rotulado como tempo normal.

## 11. Cálculo de gols esperados ▲v4

### 11.1 Baseline (▲v4 D2, D4)
Passos 3–6 da §8: `GD = f(dr)` **e** `T_m = g(dr)·estilo` com **ambas as formas escolhidas por backtest** (não lineares por decreto); **desfalque direcional** (defensivo via dr no passo 1; ofensivo cortando λ_pró no passo 6). `estilo` com shrinkage→1.0; λ mínimo como regularização honesta (documentado, viola T_m/GD no tail só com formas lineares — some com saturação suave ou com 11.2); T_base=2.6 (Copas 2018: 2.64; 2022: 2.69), recalibrar com cautela.

### 11.2 Upgrade #1 — Ataque/Defesa + Dixon-Coles (▲v4 D5)
```
ln λ_A = μ + ATA_A + DEF_B + γ·mando_A
ln λ_B = μ + ATA_B + DEF_A
# ATA_T,DEF_T: MLE sobre gols históricos, com SHRINKAGE → 0 (L2).
# ▲v4 (D5): se P_ad for MEMBRO do ensemble, o prior de ATA/DEF é de GOLS/xG histórico (StatsBomb), NÃO ∝ R_Elo
#            -> P_ad genuinamente independente do backbone. Se for gerador PRIMÁRIO, prior pode ancorar no Elo (não há P_ad).
# Dixon-Coles: M_corr[i][j] = M[i][j]·τ(i,j;λ_A,λ_B,ρ), ρ<0 → corrige 0-0,1-0,0-1,1-1.
# λ = exp(...) > 0 SEMPRE → dispensa o clamp de λ_B (resolve C7/D2 no tail).
```
**Regra do fork (C6+D5):** primário (substitui 11.1) **XOR** `P_ad` independente — nunca os dois. **Pré-requisito de entrada (D6/A8):** recomputar **V/E/D, over 2.5 E BTTS** da matriz corrigida e reconciliar com a curva de empate `P(E|dr)` + cap C1 (a DC **sobe** a P(E) da matriz).

## 12. Cálculo de placares prováveis — mantido da v3
Top-k (k=5) da matriz M, com probabilidade exibida. **Comunicação dinâmica:** "chance de NÃO ser o placar modal" derivada da matriz por jogo (~88% em jogo parelho, ~82% em goleada). Matriz 0..10. Sem Dixon-Coles, 0×0/1×1 levemente subestimados; com 11.2, corrigido (e recomputar V/E/D, §3.2/D6).

## 13. Tratamento matemático de lesões/desfalques ▲v4 (D4)

```json
{"jogo":"BRA-x-MAR-2026-06-15",
 "desfalques_A":[{"nome":"...","tier":1,"setor":"ataque","status":"out"}],
 "desfalques_B":[{"nome":"...","tier":2,"setor":"defesa","status":"duvida"}]}
```
```
tier 1 — estrela/titular indispensável:  base ΔE = −35 Elo   [a calibrar]
tier 2 — titular padrão:                 base ΔE = −15
tier 3 — rotação/reserva relevante:      base ΔE = −5

▲v4 (D4) — ROTEAMENTO POR SETOR (não mais porta única simétrica):
  setor ∈ {defesa, goleiro}:  entra via dr (passo 1 da §8) → baixa λ_pró e SOBE λ_contra  (comportamento correto p/ defesa)
  setor == ataque:            corta λ_pró(T) direto (passo 6) por δ_ata(tier) → NÃO infla o ataque do rival
ΔE_desfalques_DEF(T) = max(−120, Σ ΔE_i sobre setor∈{defesa,goleiro})
δ_ata(T)             = clamp(Σ por tier ofensivo, 0, δ_max)   [a calibrar]

▲v4 (D3) — INCERTEZA: desfalque com status "duvida" alimenta σ_ajuste(T) (§3.12) e derruba a robustez da confiança (§14).
```
"Dúvida" = meio-tier, escalação só ~1h antes → entra em `σ_ajuste`, não só como nota. Parâmetro mais "no olho"; incerteza alta e **agora propagada pelo contrato**, não compensada à mão como nas execuções v2.1.

## 14. Cálculo de nível de confiança ▲v4 (D3, D6)

Confiança ≠ probabilidade: metascore de **quão confiável é a previsão**.

```
separacao    = clamp((p_max − 1/3)/(2/3), 0, 1)
consist_int  = 1 − TV(P_poisson, P_elo)                  # consistência interna (compartilham Elo)
corrob_ext   = 1 − TV(P_modelo, P_mercado)               # =0.5 se sem odd/mercado; mercado de previsão > 1 book (3.7)
dados        = checklist 0–1: ≥8 jogos oficiais (0.4) · escalações confirmadas (0.4) · Elo maduro/não-estreante (0.2)
robustez     = 1 − incerteza de desfalques
g_rating     = 1 − min(0.6, σ_dr / σ_ref)                # ▲v4 (D3): σ_dr JÁ inclui σ_ajuste → escalação volátil derruba a confiança pelo contrato
TV(p,q) = 0.5·Σ_x |p(x) − q(x)|

score = 100 · (0.35·separacao + 0.15·consist_int + 0.15·corrob_ext + 0.20·dados + 0.15·robustez)
        · g_rating · (0.90 se mata-mata) · (0.85 se última rodada c/ incentivo cruzado)
rótulos: ≥65 alta · 40–64 média · <40 baixa
```

**▲v4 (D6/A10) — declarado:** `separacao` (probabilidade), `g_rating` (gate) e a **banda** usam todos a *mesma* σ_dr; um erro de calibração de σ se manifesta como três "confirmações" correlacionadas ("probabilidade humilde + banda larga + confiança baixa"). **Não** tratar como três sinais independentes. Pesos somam 1.00; todos [a calibrar]. **Jogos equilibrados:** separação≈0 força confiança média/baixa — o sistema diz "jogo aberto" e não fabrica favorito.

## 15. Validação pós-jogo ▲v4 (D7)

**Registro pré-jogo (imutável, append-only):** `match_id, timestamp_previsao, fase, times, R'_A, R'_B, sigma_dr, λ_A, λ_B, P(V/E/D), banda_pv, P(over2.5), P(BTTS), top-5 placares, confiança, desfalques (c/ setor), odds, preço_mercado_previsao, versao_modelo, hash_inputs`. **▲v4:** `sigma_dr`, `banda_pv` e `hash_inputs` passam a ser **colunas** (não texto solto); a validação **filtra/segmenta por `versao_modelo`** e **exclui `*-prelim`** (previsões antecipadas) das métricas morning-of. Por imutabilidade, linhas antigas não são reescritas — a migração de esquema é da Camada 2.

**Métricas (convenção: Brier forma-soma, máx 2):**
```
Brier = (1/N) Σ Σ_x (P(x)−o(x))²    baselines: uniforme 0.667 · mercado ≈0.55–0.60 · meta < 0.62 E < mercado
LogLoss = −(1/N) Σ ln P(resultado)  uniforme = ln3 ≈ 1.099
RPS = (1/2)[(P_V−O_V)² + ((P_V+P_E)−(O_V+O_E))²]   # ordinal — reportar as três
# Bootstrap B=10000: IC95 de Brier/RPS/LogLoss. Teste pareado vs mercado: diff_i, IC que NÃO cruze 0.
```

**Acerto vs. calibração:** o que importa é **calibração** (dos jogos a 60%, ~60% aconteceram?). Diagrama de confiabilidade por faixas (≥20 jogos/faixa). **▲v4 — calibrar também a incerteza:** verificar que a **banda** tem cobertura nominal (dos jogos com banda 60–74%, o realizado cai dentro ~68% das vezes) e que `σ_R/σ_ajuste` batem com a variância empírica dos erros por faixa de nº de jogos / volatilidade de escalação. A Copa tem 104 jogos → validação séria é o **backtest histórico** (2014/18/22 + Euros + Copas América ≈ 400+ jogos), pipeline congelado e point-in-time.

## 16. Riscos e limitações ▲v4

**O maior risco continua sendo a falta de validação empírica:** nenhuma linha foi backtestada; θ/κ/T_base/tiers/δ_ata/pesos/σ_R/σ_ajuste/σ_ref são [a calibrar]. **A sofisticação acumulada (v2→v3→v4) não é melhoria comprovada até o backtest** — é coerência e honestidade melhores, não acurácia provada. A cada versão a estrutura cresce e com ela o risco de **falsa confiança**: muita engrenagem, nenhuma medida.

**Mantidos:** amostra pequena (104 jogos; ~10/ano por seleção — o sistema vive de shrinkage e caps); formato de 48 times sem histórico comparável e com incentivos de fim de grupo; fontes gratuitas que atrasam/morrem (snapshot local); eco do mercado (peso ≤0.20); overfitting de pesos (<30 jogos é ruído); prorrogação/pênaltis fora do modelo; escalações ~1h antes; ToS de FBref/Transfermarkt; **apostas: Brier ~0.60 não é edge — não é ferramenta de lucro, e isso fica na interface.**

**Específicos da v4 (e o que ainda é frágil mesmo após as correções):**
- **As correções fechadas não foram medidas.** Propagar o empate (D1), forma de T_m (D2), σ_ajuste (D3) e split direcional (D4) são **mais coerentes**, não comprovadamente mais acurados. δ_ata, a,b,c de σ_ajuste e a forma de T_m são novos [a calibrar] — **overfitting cresce com cada um**; portão de IC-que-não-cruza-zero obrigatório.
- **σ_R, σ_ajuste e σ_ref são estimativas de estimativas** e os três usam a mesma σ_dr (D6/A10) — a humildade só é real se a incerteza estiver calibrada; senão é teatro. Calibrar contra a variância empírica dos erros (§15).
- **σ_dr via RSS ignora covariância** de rating intra-confederação (D6/A9): sinal e magnitude **incertos**, só corrigível com a matriz de covariância da Camada 2.
- **Reconciliação das duas P(E)** (matriz vs curva) ainda **aberta** até a DC entrar (D6/A8) — risco de incoerência de empate quando 11.2 for ligado.
- **Forma funcional de GD/T_m no tail** |dr|>500: pouquíssimos dados, ratings de minnow ruidosos — risco de super/subprever margem, decidir por dados.
- **AD ancorado no Elo** anula a diversidade nova (D5) se a regra de prior não for respeitada.
- **Mercado de previsão (Kalshi/Polymarket)** é melhor que 1 casa, mas tem liquidez desigual e pode ecoar o Elo público — não é onisciente.
- **StatsBomb:** 2018+2022 (sem 2014/Copa América), licença não-comercial, histórico — ativo de backtest, não feed ao vivo; o piso-de-bola-parada (3.2) herda esses limites.

**Incerto mesmo após as correções (declarado):** `H_host2026`, tiers de desfalque, `δ_ata`, `σ_ref`, efeito de altitude/calor, México "quase-casa", incentivos de fim de grupo (a v4, como a v3, os torna **transparentes** via cenários, não os elimina).

## 17. Roadmap por camadas ▲v4
**C1 (agora):** este documento (v4) = contrato congelado. **C2:** ingestão martj42 + fixturedownload → SQLite; **Elo histórico com H_hist + σ_R**; milestone: **backtest 2014/18/22 + Euro/Copa América, Brier < 0.62 (IC) e < Elo público, P(D)≥0 em todo |dr|, confiança não-crescente com σ_dr, banda com cobertura nominal**. **C2.5:** ataque/defesa + Dixon-Coles (11.2), decidindo o fork e o prior (C6/D5); reconciliar as duas P(E) (D6); re-backtest. **C3:** desfalques JSON (com `setor`) → RSS (fórmula não muda). **C4:** ensemble + curva restrita propagada + calibração de θ/κ/T_base/formas/pesos/tiers/δ_ata/σ_ajuste/σ_ref + (se aplicável) P_ad. **C5:** insights — fatores por previsão + Monte Carlo + sensibilidade + **cenários de classificação**. **C6:** interface local. Dependências: 4 exige 2; 5 exige 4; 3 paralelizável.

## 18. Próxima etapa recomendada ▲v4 (ordem importa)

1. **Patches de coerência (baratos, antes do backtest valer):** propagar a leitura Elo-direto inteira + banda por percentis (D1); forma de T_m por backtest junto com GD (D2); `σ_ajuste` em σ_dr (D3); split direcional de desfalque no baseline (D4); resolver o prior do AD (D5); correções textuais/notas (D6); Kalshi/Wikidata/StatsBomb-bola-parada + schema do CSV (D7). *São de baixo custo e evitam que a sofisticação nova vire falsa confiança.*
2. **Rebuild do Elo com mando histórico + σ_R (C2).** Definir `H_hist` (100 ou fit), aplicar a todo jogo não-neutro, estimar `σ_R` por seleção; **só então** validar contra eloratings.net (±25 top-30). *Desbloqueia o resto.*
3. **Decidir as formas de GD E T_m (D2)** e o gerador de λ (baseline vs 11.2) por Brier/RPS **com IC**, juntas.
4. **Extrair point-in-time:** `θ`/forma de GD e T_m, `T_base`/`κ`, curva `P(E|dr)` (truncada), e calibrar `σ_R`/`σ_ajuste`/`σ_ref` contra a variância empírica dos erros (incl. **cobertura da banda**).
5. **Ingerir StatsBomb (2018+2022, Euro, WWC)** → backtest com xG + prior de estilo + **% de bola parada** (piso de λ do azarão).
6. **Contexto físico + regime (técnico via Wikidata) como diagnóstico**, promovendo a λ só com evidência (portão de §16).
7. **Monte Carlo do torneio + cenários de classificação determinísticos** — os insights de maior valor.
8. **Só então** pesos finos do ensemble (≥30 jogos) e `P_ad` (conforme o fork, com prior não-Elo).

**Milestone de aceite:** backtest histórico com Elo corrigido por mando e σ_R, pipeline congelado e point-in-time, **Brier < uniforme com IC que não cruze o baseline**, ≈ Elo público, **P(V),P(D) ∈ [0,1] em todo |dr|**, **confiança não-crescente com σ_dr**, **leitura Elo-direto propagada inteira (P(E) não congelado)**, **formas de GD e T_m escolhidas por dados** e **σ_dr incluindo a incerteza de ajuste quando a escalação não está confirmada**. Sem isso, o resto é decoração.

---
*Documento de planejamento v4 — sem código de implementação, por escopo. Consolida as correções aprovadas em [[camada1-revisao-v3]] (propagação inteira, T_m por dados, σ de ajuste, desfalque direcional, independência do AD, fontes de mercado de previsão) sobre a base da v3 (coerência [0,1] + incerteza de rating) e da v2 (anti-saturação + mando histórico). Tudo [a calibrar] é recalibrado na Camada 2/4. Tabelas reconferidas em código. Fontes verificadas em 2026-06-15; snapshot local é a defesa. Probabilidades, nunca certezas — inclusive sobre o próprio modelo, não-validado até o primeiro backtest.*
