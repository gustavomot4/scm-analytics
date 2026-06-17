---
tags: [camada1, planejamento, historico]
status: historico
tipo: planejamento
data: 2026-06-15
aliases: ["Modelo v3"]
---

# Camada 1 — Planejamento Matemático e de Dados (v3 — incerteza e coerência)
**Projeto:** Sistema de previsão de partidas — Copa do Mundo 2026 (EUA/Canadá/México)
**Data:** 2026-06-15 · **Status:** planejamento (sem código) · **Custo-alvo:** R$ 0
**Supersede:** [[camada1-planejamento-v2]] (v2, 2026-06-15). Base da revisão: [[camada1-revisao-v2]].

> Convenções: probabilidades em [0,1]; V/E/D = vitória A / empate / vitória B; λ = gols esperados; dr = diferença de Elo (A − B, já com mando); W_e = expectativa de pontuação do Elo; σ_R = erro-padrão do rating; σ_dr = erro-padrão da diferença. **[a calibrar]** = estimativa educada a fixar no backtest, não constante da literatura. Marcador **▲v3** sinaliza o que mudou em relação à v2 e por quê. As correções da v2 (saturação de gols, mando histórico, ensemble honesto) continuam válidas e integradas.

---

## 0. Changelog v3 (o que mudou e por quê)

A v2 foi auditada em [[camada1-revisao-v2]] (2ª rodada). A v3 promove as correções aprovadas para o **contrato congelado**. Nenhuma quebra a filosofia da v2 — todas aumentam a **coerência** (probabilidades sempre em [0,1]) e a **honestidade da incerteza**.

| # | Correção | Severidade | Seções |
|---|---|---|---|
| C1 | **P(D) nunca negativo.** A curva de empate ganha a restrição `P(E|dr) ≤ 2·min(W_e, 1−W_e)`. Sem isso, em mismatch alto a leitura Elo-direto produzia `P(D) < 0` (visto em ESP×CPV, dr=572 → −0,4%). | 🟡 coerência | 3.1, 9, 10 |
| C2 | **Clamp por leitura, não só no ensemble final.** Cada leitura (Poisson, Elo, mercado, AD) é clampada em [0.02,0.96] e renormalizada **antes** de entrar na média — senão uma leitura inválida contamina o pool e é "salva" por acidente. | 🟡 coerência | 9, 10 |
| C3 | **Incerteza de rating `σ_R` vira variável de 1ª classe.** Cada rating carrega um erro-padrão (grande para provisórios/estreantes, técnico novo, elenco pouco benchmarkável). Propaga-se para V/E/D (encolhe extremos — Jensen) e gera **banda de probabilidade**. Resolve o problema do minnow (CPV) na própria probabilidade, não só na confiança. | 🟡 modelagem | 3.1, 3.12, 8, 9, 10 |
| C4 | **Confiança mede confiabilidade, não só "quão definido".** Gate multiplicativo `g_rating` (incerteza alta de rating derruba a confiança) + desambiguação do ramo "sem odds". Antes, mismatch contra rating ruidoso pontuava ALTO (ESP×CPV tirou 82, a maior, sendo o rating menos confiável). | 🟡 honestidade | 14 |
| C5 | **Forma funcional do GD escolhida por backtest, não por decreto.** A v2 impôs `GD` estritamente linear em dr; a v3 deixa o backtest escolher entre linear / potência suave / saturação suave com teto alto, com restrição monótona e cautela na extrapolação além do suporte de dados. | 🟡 modelagem | 8, 11.1 |
| C6 | **Fork do ATA/DEF resolvido.** ATA/DEF (Dixon-Coles) é **gerador primário XOR** leitura independente do ensemble — não os dois. Contrato escolhe explicitamente. | 🟡 contrato | 4, 9, 11.2 |
| C7 | **Clamp de λ_B honesto.** Documentado que o piso `λ_B ≥ 0.2` viola `T_m`/`GD` no tail (regularização, não "sem efeito"); some ao adotar o gerador AD (λ>0 por construção). | ⚪ | 8, 11 |
| C8 | **UX do placar modal dinâmica.** "~88% de NÃO ser o placar" deixa de ser constante; é derivado da matriz por jogo (em goleada o modal sobe a ~18%). | ⚪ | 12 |
| C9 | **Registro com `hash_inputs` + filtro por versão.** A coluna passa a existir no CSV; a validação filtra/segmenta por `versao_modelo` (não misturar v0.1/v2.0/v3.0). | ⚪ | 15 |
| C10 | **Fontes atualizadas:** StatsBomb agora cobre **WC 2022** (+360), não só 2018; RealGM xG tracker (manual, in-tournament); `oddspapi.io` candidato a odds gratuitas (validar antes de depender). | ⚪ → dados | 6 |
| C11 | **Flag de troca de técnico + prior de valor/idade** alimentam `σ_R` (não o ponto): regime novo = rating mais incerto. | ⚪ → dados | 3.11, 3.12 |

Princípio mantido desde a v1: **nada de certezas — só probabilidades**; tudo roda local; nenhuma previsão lê a internet no momento do cálculo (snapshot diário em disco). **Esta versão passa a ser `v3.0`.**

---

## 1. Visão geral do sistema em camadas

| Camada | Função | Estado |
|---|---|---|
| 1 | Motor matemático e dados base | **este documento (v3)** |
| 2 | Coleta e normalização (CSV/JSON → SQLite local) | próxima |
| 3 | Detector de notícias/lesões/desfalques | depois da 2 |
| 4 | Sistema de previsão (ensemble) | consome 1–3 |
| 5 | Geração de insights/explicações | consome 4 |
| 6 | Interface local | última |

A Camada 1 define **contratos matemáticos** (entradas, fórmulas, saídas). As demais só alimentam ou consomem esses contratos. Mudança em qualquer fórmula desta camada = nova `versao_modelo`.

## 2. Objetivo da Camada 1

Especificar o pipeline que transforma dados públicos em: P(V), P(E), P(D) **com banda de incerteza**, λ_A, λ_B, placares mais prováveis, P(over 2.5), P(ambos marcam), ajuste por desfalques, score de confiança e métricas de validação. Critério de pronto: qualquer dev implementa a Camada 4 lendo só este documento, cada número de saída é rastreável a uma fórmula e a um dado de entrada (auditabilidade), e **toda probabilidade fica em [0,1] por construção** (▲v3).

## 3. Cálculos recomendados

Pipeline (não modelos paralelos independentes): Elo (+ forma + desfalques + mando) estima a *diferença* de força **e sua incerteza**; fatores ofensivos/defensivos estimam o *total* (e, no upgrade C6, a *direção*) de gols; Poisson converte em distribuição de placares; um mini-ensemble combina leituras; odds são benchmark externo.

### 3.1 Elo Rating (espinha dorsal) ▲v3 (C1, C3)

**Funcionamento.** Cada seleção tem rating R **e erro-padrão σ_R** (▲v3). Após cada jogo:

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

`H_hist` aplica-se a **TODO** jogo não-neutro do martj42 (a maioria do histórico). Sem ele, mandantes "surpreendem" o modelo, os ratings nascem enviesados e o benchmark contra eloratings.net (que usa mando) não fecha. Inicialização em 1500; ratings com <30 jogos são **provisórios**.

**▲v3 — Erro-padrão do rating `σ_R` (novo, seção 3.12).** Cada rating passa a publicar `σ_R`, função de: nº de jogos na janela efetiva, recência, **diversidade de oposição** (quem só jogou contra fracos tem σ alto), e flags de regime (técnico novo, estreante). É o que distingue "1576 medido em 80 jogos contra a elite" de "1576 de um estreante que mal jogou contra top-30". Entra na probabilidade (3.12/8) e na confiança (14).

Metodologia do World Football Elo Ratings; sanidade: dr=+100 → W_e≈0.64; dr=+300 → W_e≈0.85. Benchmark de sanidade contra eloratings.net (±25 nas top-30) e international-football.net (2º benchmark). **Vantagens.** Autocorretivo, robusto a dados esparsos, interpretável. **Limitações.** Reage devagar a troca de geração/técnico (▲v3: agora isso **alarga σ_R** em vez de ficar só como nota); amistosos ruidosos; não separa ataque de defesa (daí 3.4); estreantes mal calibrados (σ_R alto).

### 3.2 Poisson (gerador de placares) — mantido da v2

Gols ~ Poisson independente: `P(X=k)=e^(−λ)λ^k/k!`. Matriz `M[i][j]=P_A(i)·P_B(j)`, **i,j = 0..10**; resíduo (>10) distribuído proporcionalmente na borda.

```
P(V)=Σ M[i][j] (i>j)   P(E)=Σ M[i][i]   P(D)=Σ M[i][j] (i<j)
P(over 2.5)=1 − Σ M[i][j] (i+j ≤ 2)
P(ambos marcam)=(1−e^(−λ_A))·(1−e^(−λ_B))
Placares prováveis = top-k células de M
```

**Limitações.** Independência entre ataques é falsa — subestima 0×0/1×1; **Dixon-Coles (C6) corrige** (quando entrar, recomputar over 2.5 e BTTS da matriz conjunta). Não modela prorrogação/expulsões/estado de jogo. **Mata-mata:** V/E/D = tempo normal; avanço = `P(V)+P(E)·(0.5+ε·sinal(dr))`, ε≈0.03 [a calibrar].

### 3.3 Forma recente — mantido da v2

Janela das **últimas 10 partidas**, peso temporal e desconto de amistosos:

```
w_i = 0.9^(idade_em_meses) · (1.0 oficial · 0.5 amistoso)
PPJ_pond = Σ w_i · pontos_i / Σ w_i
ΔE_forma = 15 · (PPJ_pond − PPJ_esperado)    cap ±30 Elo  [a calibrar]
```

Métrica **ajustada a adversário** (comparar com o esperado pelo Elo do adversário). **Dependências obrigatórias (v2):** (a) `PPJ_esperado = 3·P(V)+1·P(E)` exige a curva de empate `P(E|dr)` (com a restrição C1); (b) no backtest, usar **Elo point-in-time**, nunca o final (anti look-ahead). Risco de dupla contagem com o Elo → cap e peso baixos.

### 3.4 Força ofensiva/defensiva ▲v3 (C6)

**Baseline (total, mantido).** Sobre a janela ponderada:

```
tendência_gols_T = (gols_pró + gols_contra por jogo de T, ajustado pelo Elo médio dos adversários) / média_internacional
estilo_T = shrinkage(tendência_gols_T → 1.0, força = n_jogos/(n_jogos+10))
```

**▲v3 — papel do ATA/DEF resolvido (C6).** O upgrade Dixon-Coles (11.2) gera λ **direcional** (ataque de A × defesa de B). O contrato escolhe **uma** função para ele (não as duas): ou é o **gerador primário** de λ (substitui o total simétrico) **ou** é uma **leitura independente `P_ad`** do ensemble. Ver 9 e 11.2 para a regra. **Limitações.** Gols ≠ qualidade de chance (sem xG ao vivo); ajuste por adversário grosseiro via Elo médio.

### 3.5 Mando de campo / campo neutro — mantido da v2

```
H_host2026 = +60 Elo  para anfitrião jogando no próprio país   [a calibrar]
           = 0         nos demais jogos (neutro)
```

Distinto de `H_hist` (=100, construção do Elo). Caso "quase-casa" (México em solo americano): `bonus_mando_override` manual. Altitude/calor: diagnóstico (3.11), não λ na baseline.

### 3.6 Lesões e desfalques — resumo
Representação completa na **seção 13**. Entrada por JSON manual (detector é Camada 3).

### 3.7 Odds gratuitas (benchmark) — mantido da v2

```
p_i = (1/odd_i) / Σ_j (1/odd_j)        (de-vig proporcional; Shin fica p/ futuro)
```

**Benchmark, não input.** Peso ≤ 0.20 no ensemble só se a odd for capturada manualmente pré-jogo. **Realidade (2026-06):** sem API de odds de Copa gratuita confiável garantida → plano base é **captura manual** (1 min/jogo, com timestamp). `oddspapi.io` é candidato a validar (6). **▲v3 — cautela:** odd de **uma casa** (não fechamento/consenso) é benchmark mais fraco do que parece; não superdimensionar a concordância com 1 book (ver 14).

### 3.8 Ensemble — resumo ▲v3 (C2, C6)
Detalhe em 9–10. Leituras `P_poisson` e `P_elo` **compartilham o Elo** (diversidade real vem do mercado e, no upgrade C6, da leitura AD se for membro independente). **▲v3:** clamp **por leitura** antes de combinar.

### 3.9 Nível de confiança — resumo ▲v3 (C4)
Seção 14. Confiança é metadado, não probabilidade. **▲v3:** gate `g_rating` (incerteza de rating derruba a confiança) e ramo "sem odds" desambiguado.

### 3.10 Validação — resumo ▲v3 (C9)
Seção 15. Brier + LogLoss + RPS + calibração, IC bootstrap, registro pré-jogo imutável **com `hash_inputs`** e **filtro por versão**.

### 3.11 Contexto físico e xG (diagnóstico) — mantido da v2 + ▲v3 (C11)

Variáveis gratuitas e locais; **entram como diagnóstico/modificador de confiança; viram termo de λ só se passarem no portão de backtest** (16):

- **xG (StatsBomb Open Data).** Backtest com "resultado merecido", prior de estilo menos ruidoso que gols brutos, validação do gerador de λ. ▲v3: cobertura agora inclui **WC 2022** além de 2018/Euro/WWC (6). Licença não-comercial.
- **Fadiga/descanso** (calendário) e **descanso diferencial**; **viagem** (haversine entre sedes); **altitude** (Cidade do México ~2.240 m); **calor** (Open-Meteo); **idade média/caps** (Wikipedia).
- **▲v3 — flag de troca de técnico (C11):** técnico assumido há poucos jogos = regime novo → **alarga σ_R** (3.12), não muda o ponto. Derivável de graça (Wikipedia/notícias).

Não perseguir (sem fonte gratuita estruturada p/ seleções): posse de bola, distância percorrida.

### 3.12 Incerteza de rating `σ_R` e propagação ▲v3 (C3) — NOVO

A peça que faltava na v2: tratar o Elo como **distribuição**, não ponto.

```
σ_R(T) = base(n_jogos efetivos, recência) ampliado por:
         + estreante / <30 jogos (provisório)
         + diversidade de oposição baixa (só jogou contra fracos)
         + técnico novo há poucos jogos (3.11)
         + elenco pouco benchmarkável (quase todo de liga local)   [todos a calibrar]
σ_dr = sqrt(σ_R(A)² + σ_R(B)²)
```

**Propagação (Jensen).** A expectativa Elo é côncava acima de 0.5; integrar sobre a incerteza **encolhe extremos para 1/3**:

```
E[W_e] = ∫ W_e(dr) · N(dr; dr0, σ_dr) d(dr)        # MC barato (10^4) ou correção de 2ª ordem
```

| dr0 | σ_dr=0 | 75 | 150 | 250 |
|---:|---:|---:|---:|---:|
| 150 | 0.703 | 0.696 | 0.679 | 0.651 |
| 300 | 0.849 | 0.841 | 0.819 | 0.781 |
| 500 | 0.947 | 0.942 | 0.929 | 0.898 |

É **a** correção para o minnow/estreante (ex.: Cabo Verde): um favorito medido contra ratings provisórios recebe automaticamente probabilidade menos extrema — de graça e principiado, não um band-aid de confiança. Gera também a **banda de probabilidade** publicada (10/14). Entra atrás do portão de backtest como qualquer coisa, mas é a adição de maior retorno.

## 4. Cálculos fora da baseline (e por quê) ▲v3

**Upgrade priorizado #1 (logo após o 1º backtest): ataque/defesa Poisson + Dixon-Coles** (C6) — corrige direção e reforça anti-saturação. **▲v3 — regra do fork:** se ele virar gerador primário de λ, **não** existe `P_ad` separado (a 3ª leitura independente passa a ser só o mercado); se a baseline GD/T_m continuar gerando λ, então ATA/DEF entra como `P_ad` independente. Decidir por Brier/RPS com IC. **Insight near-term:** Monte Carlo do torneio **e cenários de classificação determinísticos** (novo, 6-insights). Continuam fora: Poisson bivariado; xG ao vivo (sem fonte gratuita p/ 48 seleções); modelos hierárquicos bayesianos (matam auditabilidade); ML/boosting (overfit garantido); ratings por jogador; clima/altitude/viagem como termo de λ (entram como diagnóstico antes); de-vig de Shin; ajuste por incentivos de última rodada (sem modelo confiável → enumerar cenários em vez de prever, 6-insights).

## 5. Dados necessários por cálculo ▲v3

| Cálculo | Dado | Granularidade | Histórico mínimo |
|---|---|---|---|
| Elo (+ H_hist) + σ_R | data, times, placar, competição, flag neutro, home/away | por jogo | 1950+ (ideal 1872+) |
| Forma | idem + data p/ decaimento + curva P(E|dr) | por jogo | últimos 10/time |
| Estilo / Ataque-Defesa | placares + Elo do adversário na data | por jogo | últimos 10–20/time (full p/ AD) |
| Mando 2026 | estádio, cidade, país-sede | por jogo da Copa | só 2026 |
| Poisson | λ_A, λ_B (derivados) | por jogo | — |
| Desfalques | lista de ausentes + tier | por jogo | elenco atual |
| Odds | 1X2 decimal + timestamp | por jogo | só 2026 (prospectivo) |
| σ_R / regime | nº jogos, diversidade de oposição, técnico novo, % liga local | por seleção | janela efetiva |
| Contexto físico (diag.) | descanso, viagem, altitude, temp, idade | por jogo | 2026 + histórico p/ calibrar |
| xG (backtest) | xG por jogo (StatsBomb) | por jogo | torneios cobertos |
| Validação | resultado final + tudo registrado pré-jogo + hash_inputs | por jogo | acumula |

## 6. Fontes gratuitas recomendadas (verificadas em 2026-06-15) ▲v3

| Fonte | Dado | Grátis? | Key? | Limitações | Confiab. | Papel | Fallback |
|---|---|---|---|---|---|---|---|
| **martj42/international_results** | resultados 1872–2026, torneio, flag neutro, home/away | Sim | Não | atualização por PR (lag horas–dias) | Alta | **nº 1** | openfootball; manual |
| **fixturedownload.com** (wc-2026) | calendário+resultados; base p/ descanso/viagem | Sim | Não | só jogos | Alta | **Sim** | openfootball |
| **football-data.org** | jogos, resultados, classificação (WC no free) | Sim (free) | Sim (grátis) | 10 req/min; sem escalações no free | Alta | automação de resultados | martj42 + manual |
| **Elo próprio** (do martj42, c/ H_hist) + σ_R | rating de força + incerteza | Sim | Não | depende do dataset base | Alta (auditável) | **recomendado** | snapshot eloratings.net |
| **eloratings.net** / **international-football.net** | Elo benchmark / 2º benchmark | Sim | Não | sem API; SPA sobre TSV / metodologia difere | Alta / Média | sanidade | calcular próprio |
| **StatsBomb Open Data** ▲v3 | eventos + **xG** + 360; **WC 2018 e 2022**, Euro, WWC | Sim | Não | sem 2014/Copa América; não ao vivo; licença **não-comercial** | Alta | **backtest xG + prior** | FBref (visual) |
| **RealGM — xG Tracker WC 2026** ▲v3 | xG por jogo da Copa 2026, pós-jogo | Sim | Não | terceiro de fonte única; copiar à mão; metodologia própria | Média (validar vs StatsBomb) | xG **in-tournament** (manual) | StatsBomb (histórico) |
| **Open-Meteo (+Elevation/Geocoding)** | temp/umidade; altitude; coords das sedes | Sim | **Não** | uso não-comercial; efeito pequeno | Alta | calor/altitude/viagem | Wikidata; hardcode |
| **Wikidata (SPARQL)** | coords/elevação/capacidade de estádios | Sim | Não | semiestruturado | Média-alta | redundância geo | Open-Meteo |
| **Wikipedia — elencos 2026** | convocações, idade, caps, clube, **técnico** | Sim | Não | parsing manual | Alta na Copa | convocações/idade/regime | site FIFA |
| **oddspapi.io** ▲v3 (a validar) | odds 1X2 multi-casa + histórico (free tier alegado) | Alegado | Sim | autopromoção do vendor; limites/cobertura de Copa não confirmados | A validar | candidato; **NÃO** depender até testar | captura manual |
| **Understat** ▲v3 | xG/npxG — **só clubes europeus** | Sim | Não | não cobre seleções | Alta (clubes) | proxy indireto, baixa prio. | ignorar |
| **The Odds API** | odds | **Não serve** (25/dia, NBA/MLB) | — | sem futebol no free | — | **Não** | captura manual |
| **FBref / Transfermarkt** | minutos, valor de mercado, xG visual | Visualização | Não | **ToS restringe scraping** | Alta | só consulta manual (tiers, prior de valor) | tiers manuais |
| **Lesões/desfalques** | — | — | — | **Sem fonte estruturada gratuita p/ 48 seleções** | — | — | JSON manual; RSS na C3 |

Lacunas reconfirmadas (não inventar): odds gratuitas via API (segue captura manual; `oddspapi.io` é candidato a testar, não fato) e lesões estruturadas (JSON manual + RSS na Camada 3). **APIs pagas (Sportmonks, TheStatsAPI, iSports, API-Football) violam o custo-alvo R$ 0 — fora de escopo.**

## 7. Dados que precisarão ser manuais no início
Snapshot do eloratings.net + international-football.net (sanidade, 1x pré-torneio); **tiers de jogadores** só p/ as ~16 seleções com chance real + sob demanda; **estimativa inicial de σ_R/regime** (técnico novo, % liga local) p/ o shortlist; **JSON de desfalques** por jogo; **odds 1X2** digitadas pré-jogo com timestamp; override de mando (México em solo americano); convenção de pênaltis (martj42 registra placar ao fim da prorrogação + `shootouts.csv`).

## 8. Fórmula inicial do modelo (pipeline completo) ▲v3 (C3, C5, C7)

```
ENTRADAS: R_A,σ_A · R_B,σ_B (Elo próprio, já com H_hist) · forma · estilo (of/def) · desfalques · flag mando 2026

1) Elo ajustado:    R'_T = R_T + ΔE_forma(T) + ΔE_desfalques(T)
2) Diferença:       dr   = R'_A − R'_B + H_host2026          # 60 se anfitrião, senão 0
   Incerteza:       σ_dr = sqrt(σ_A² + σ_B²)                 # ▲v3 (C3)
3) Saldo esperado:  GD   = f(dr)                             # ▲v3 (C5): f escolhida por backtest, NÃO linear por decreto
                                                             #   candidatos: θ·dr/100 | θ·(dr/100)^p,p≤1 | G_max·tanh(θ·dr/(100·G_max))
4) Total esperado:  T_m  = (T_base + κ·|dr|/100) · estilo_A · estilo_B
                                                             # T_base=2.6, κ~0.10 [a calibrar]
5) Gols esperados:  λ_A = max(0.2,(T_m+GD)/2)   λ_B = max(0.2,(T_m−GD)/2)
                                                             # ▲v3 (C7): o clamp em 0.2 REGULARIZA mas viola T_m/GD no tail (documentado);
                                                             #   desaparece se 11.2 (AD, λ=exp(...)>0) for o gerador primário.
6) Matriz Poisson:  M[i][j] = Pois(i;λ_A)·Pois(j;λ_B),  i,j = 0..10 (resíduo na borda)
7) Saídas Poisson:  V/E/D, over 2.5, BTTS, top placares (10–12)
8) Leitura Elo-direto (propagada): E[W_e](dr0,σ_dr) + curva P(E|dr) COM restrição C1 (seção 9)
9) Ensemble (clamp por leitura) + banda de probabilidade por σ_dr: seções 9–10
```

**Forma do GD — escolher no backtest (▲v3 C5).** Linear e côncava **coincidem onde há dados** (|dr|≤300) e divergem só no **tail esparso** (|dr|>500), que é justamente onde os ratings de minnow são ruidosos:

| dr | GD linear | GD sat. suave (G_max=4) | λ_A linear | λ_A sat. |
|---:|---:|---:|---:|---:|
| 100 | 0.45 | 0.45 | 1.58 | 1.57 |
| 300 | 1.35 | 1.30 | 2.12 | 2.10 |
| 600 | 2.70 | 2.35 | 2.95 | 2.78 |
| 900 | 4.05 | 3.07 | 3.77 | 3.28 |

Decidir por Brier/RPS **com IC** (point-in-time), com restrição monótona e **extrapolação cautelosa além do suporte** (alargar σ_dr quando |dr| sai da faixa observada). θ, κ, T_base saem de regressão `saldo_real ~ f(dr)` e média de gols por Copa, não de palpite.

## 9. Ensemble e leitura Elo-direto ▲v3 (C1, C2, C3, C6)

**Curva de empate com restrição (C1).** `P(E|dr)` estimado empiricamente do martj42 em faixas de |dr| (~26% com |dr|<50 caindo a ~15% com |dr|>300 — extrair no backtest), **mas truncado**:

```
P(E|dr) := min( P(E_empírico|dr),  2·min(W_e, 1−W_e) − ε )      # garante P(V),P(D) ∈ [0,1]
P(V) = E[W_e] − P(E)/2          P(D) = 1 − P(V) − P(E)           # E[W_e] propagado (C3)
```

Efeito da restrição (P(D) nunca negativo):

| dr | W_e | cap P(E) | P(E) usado | P(V) | P(D) |
|---:|---:|---:|---:|---:|---:|
| 200 | 0.760 | 0.481 | 0.200 | 0.660 | 0.140 |
| 400 | 0.909 | 0.182 | 0.182 | 0.818 | 0.000 |
| 572 | 0.964 | 0.072 | 0.072 | 0.928 | 0.000 |

**Pesos (mantidos da v2):**

| Componente | Peso c/ odds | Peso s/ odds |
|---|---|---|
| P_poisson | 0.45 | 0.56 |
| P_elo (E[W_e] + curva de empate) | 0.35 | 0.44 |
| P_mercado | 0.20 | 0.00 |

**▲v3 — clamp por leitura (C2):** cada leitura é clampada em [0.02,0.96] e renormalizada **antes** de entrar no pool linear. Combinação = média linear, renormalizada. **Diversidade real:** P_poisson e P_elo compartilham o Elo (~0.80 num único sinal + 0.20 mercado). **Fork AD (C6):** se 11.2 for o gerador primário, não há P_ad e o 3º sinal é só o mercado; se a baseline gerar λ, AD vira `P_ad` independente e os pesos viram ~0.35/0.25/0.20/0.20 (Poisson/Elo/AD/mercado). Após ≥30 jogos, otimizar pesos minimizando Brier (grid), congelados por fase.

## 10. Cálculo da probabilidade final V/E/D ▲v3 (C2, C3)

```
para cada leitura k:  P_k(x) ← clamp(P_k(x), 0.02, 0.96); renormalizar          # ▲v3 (C2) por leitura
P_final(x) = Σ_k w_k·P_k(x),  x ∈ {V,E,D};  renormalizar
clamp final [0.02,0.96] + renormalizar (iterar 1–2x)
```

**▲v3 — banda de probabilidade (C3):** publicar, além do ponto, `[P(x | dr0−σ_dr) , P(x | dr0+σ_dr)]` (refazendo o ensemble nas pontas) — a largura comunica que a dúvida vem dos **ratings**, não só do empate. No mata-mata, `P(avança) = P(V)+P(E)·(0.5+0.03·sinal(dr))`, V/E/D rotulado como tempo normal.

## 11. Cálculo de gols esperados ▲v3

### 11.1 Baseline (▲v3 C5, C7)
Passos 3–5 da seção 8, com `f(dr)` escolhida por backtest (não linear por decreto) e o clamp de λ_B documentado como regularização (viola T_m/GD no tail). `estilo` com shrinkage→1.0; desfalques entram **antes**, via ΔE (uma porta); λ mínimo 0.2; T_base=2.6 (Copas 2018: 2.64; 2022: 2.69), recalibrar com cautela (16 jogos ≈ ±0.15 no máx).

### 11.2 Upgrade #1 — Ataque/Defesa + Dixon-Coles (▲v3 C6)

```
ln λ_A = μ + ATA_A + DEF_B + γ·mando_A
ln λ_B = μ + ATA_B + DEF_A
# ATA_T,DEF_T: MLE sobre gols históricos, com SHRINKAGE → 0 (L2); âncora-Elo (prior ∝ R_T) preserva a espinha dorsal.
# Dixon-Coles: M_corr[i][j] = M[i][j]·τ(i,j;λ_A,λ_B,ρ), ρ<0 → corrige 0-0,1-0,0-1,1-1.
# λ = exp(...) > 0 SEMPRE → dispensa o clamp de λ_B (resolve C7).
```

**Regra do fork (C6):** este gerador é **primário** (substitui 11.1) **ou** entra como `P_ad` independente — nunca os dois (ver 9). Quando entrar, recomputar over 2.5/BTTS da matriz corrigida.

## 12. Cálculo de placares prováveis ▲v3 (C8)
Top-k (k=5) da matriz M, com probabilidade exibida. **▲v3 — comunicação dinâmica:** "chance de NÃO ser o placar modal" é **derivada da matriz por jogo** (≈88% em jogo parelho, mas ~82% em goleada, onde o modal sobe a ~18%) — não um número fixo. Matriz 0..10. Sem Dixon-Coles, 0×0/1×1 levemente subestimados; com 11.2, corrigido.

## 13. Tratamento matemático de lesões/desfalques — mantido da v2

```json
{"jogo":"BRA-x-MAR-2026-06-15","desfalques_A":[{"nome":"...","tier":1,"setor":"ataque"}],"desfalques_B":[]}
```

```
tier 1 — estrela/titular indispensável:  ΔE = −35 Elo   [a calibrar]
tier 2 — titular padrão:                 ΔE = −15
tier 3 — rotação/reserva relevante:      ΔE = −5
ΔE_desfalques(T) = max(−120, Σ ΔE_i)
```

"Dúvida" = meio-tier e **derruba a robustez da confiança** (14). Incerteza alta e declarada — parâmetro mais "no olho". Refinamento (junto com 11.2): split direcional (desfalque ofensivo corta λ_pró; defensivo/goleiro infla λ_contra).

## 14. Cálculo de nível de confiança ▲v3 (C4)

Confiança ≠ probabilidade: metascore de **quão confiável é a previsão** (não "quão definido é o jogo").

```
separacao    = clamp((p_max − 1/3)/(2/3), 0, 1)
consist_int  = 1 − TV(P_poisson, P_elo)                  # consistência interna (compartilham Elo)
corrob_ext   = 1 − TV(P_modelo, P_mercado)               # =0.5 se sem odd (ver ramo abaixo); não superdimensionar 1 book (3.7)
dados        = checklist 0–1: ≥8 jogos oficiais (0.4) · escalações confirmadas (0.4) · Elo maduro/não-estreante (0.2)
robustez     = 1 − incerteza de desfalques
g_rating     = 1 − min(0.6, σ_dr / σ_ref)                # ▲v3 (C4): GATE multiplicativo; σ_ref [a calibrar]
TV(p,q) = 0.5·Σ_x |p(x) − q(x)|

score = 100 · (0.35·separacao + 0.15·consist_int + 0.15·corrob_ext + 0.20·dados + 0.15·robustez)
        · g_rating · (0.90 se mata-mata) · (0.85 se última rodada c/ incentivo cruzado)
rótulos: ≥65 alta · 40–64 média · <40 baixa
```

**▲v3 — por que mudou (C4):** sem `g_rating`, mismatch contra rating ruidoso pontuava ALTO (`separacao` domina). Caso real: ESP×CPV tirou 82 (a maior do registro) sendo "o rating menos confiável"; URU×KSA caiu de 67→57 ao aplicar `g_rating` (técnico saudita novo + elenco doméstico elevam σ_dr). **Ramo "sem odds" desambiguado:** definição única → `corrob_ext = 0.5` (neutro) **mantendo os pesos** (não renormalizar). Pesos somam 1.00; todos [a calibrar]. **Jogos equilibrados:** separação≈0 força confiança média/baixa — o sistema diz "jogo aberto" e não fabrica favorito.

## 15. Validação pós-jogo ▲v3 (C9)

**Registro pré-jogo (imutável, append-only):** `match_id, timestamp_previsao, fase, times, R'_A, R'_B, σ_dr, λ_A, λ_B, P(V/E/D) + banda, P(over2.5), P(BTTS), top-5 placares, confiança, desfalques, odds capturadas, versao_modelo, hash_inputs`. **▲v3 (C9):** `hash_inputs` passa a ser obrigatório (prova de imutabilidade) e a validação **filtra/segmenta por `versao_modelo`** — nunca misturar v0.1/v2.0/v3.0 numa mesma métrica.

**Métricas (convenção: Brier forma-soma, máx 2):**

```
Brier = (1/N) Σ Σ_x (P(x)−o(x))²    baselines: uniforme 0.667 · mercado ≈0.55–0.60 · meta < 0.62 E < mercado
LogLoss = −(1/N) Σ ln P(resultado)  uniforme = ln3 ≈ 1.099
RPS = (1/2)[(P_V−O_V)² + ((P_V+P_E)−(O_V+O_E))²]   # ordinal — reportar as três
# Bootstrap B=10000: IC95 de Brier/RPS/LogLoss. Teste pareado vs mercado: diff_i, IC que NÃO cruze 0.
```

**Acerto vs. calibração:** o que importa é **calibração** (dos jogos a 60%, ~60% aconteceram?). Diagrama de confiabilidade por faixas, só com ≥20 jogos/faixa. A Copa tem 104 jogos → validação séria é o **backtest histórico** (2014/18/22 + Euros + Copas América ≈ 400+ jogos), pipeline **congelado e point-in-time**, Brier < uniforme (com IC) e ≈ Elo público. Comparação com mercado: prospectiva em 2026.

## 16. Riscos e limitações ▲v3

**O maior risco continua sendo a falta de validação empírica:** nenhuma linha foi backtestada; θ/κ/T_base/tiers/pesos/σ_R/σ_ref são [a calibrar]; as análises usam Elo de fonte única/estimado. A sofisticação da v3 **não** é melhoria comprovada até o backtest — é coerência melhor, não acurácia provada.

**Mantidos:** amostra pequena (104 jogos p/ validar, ~10/ano por seleção — o sistema vive de shrinkage e caps); formato de 48 times sem histórico comparável e com incentivos de fim de grupo; fontes gratuitas que atrasam/morrem (snapshot local); eco do mercado (odds ≤0.20); overfitting de pesos (<30 jogos é ruído); desfalques no olho; prorrogação/pênaltis fora do modelo; escalações ~1h antes; ToS de FBref/Transfermarkt; **apostas: Brier ~0.60 não é edge — não é ferramenta de lucro, e isso fica na interface.**

**Específicos da v3:**
- **σ_R e σ_ref são, eles próprios, estimados** — a propagação só ajuda se a estimativa de incerteza for razoável; calibrar no backtest (ex.: σ_R consistente com a variância dos erros de previsão por faixa de nº de jogos).
- **Forma funcional do GD no tail** (C5): risco de superprever margem (linear) ou subprever (saturação) — decidir por dados, com pouca evidência em |dr|>500.
- **Overfitting cresce com cada variável** (xG, descanso, viagem, altitude, calor, idade, regime): portão obrigatório (IC que não cruza zero).
- **StatsBomb:** cobertura ampliou (2018+2022) mas sem 2014/Copa América; licença não-comercial; ativo de backtest, não feed ao vivo.
- **"Mercado" de uma casa** (não fechamento) é benchmark mais fraco do que o rótulo sugere.

**Incerto mesmo após as correções (declarado):** `H_host2026`, tiers de desfalque, σ_ref, efeito de altitude/calor, México "quase-casa", incentivos de fim de grupo (a v3 os torna **transparentes** via cenários determinísticos, não os elimina).

## 17. Roadmap por camadas ▲v3
**C1 (agora):** este documento (v3) = contrato congelado. **C2:** ingestão martj42 + fixturedownload → SQLite; **Elo histórico com H_hist + σ_R**; milestone: **backtest 2014/18/22 + Euro/Copa América, Brier < 0.62 (IC) e < Elo público, P(D)≥0 em todo |dr|, confiança não-crescente com σ_dr**. **C2.5:** ataque/defesa + Dixon-Coles (11.2), decidindo o fork (C6); re-backtest. **C3:** desfalques JSON → RSS (fórmula não muda). **C4:** ensemble + curva de empate restrita + calibração de θ/κ/T_base/pesos/tiers/σ_ref + (se aplicável) P_ad. **C5:** insights — fatores por previsão + Monte Carlo + sensibilidade + **cenários de classificação**. **C6:** interface local. Dependências: 4 exige 2; 5 exige 4; 3 paralelizável.

## 18. Próxima etapa recomendada ▲v3 (ordem importa)

1. **Patches de coerência (baratos, antes do backtest valer):** restrição da curva de empate (C1); clamp por leitura (C2); `hash_inputs` + filtro por versão no CSV (C9); resolver o fork AD no contrato (C6); ramo "sem odds" único (C4); linha StatsBomb 2022 (C10). *São de baixo custo e evitam que a sofisticação nova vire falsa confiança.*
2. **Rebuild do Elo com mando histórico + σ_R (C2).** Definir `H_hist` (100 ou fit), aplicar a todo jogo não-neutro, estimar `σ_R` por seleção; **só então** validar contra eloratings.net (±25 top-30). *Desbloqueia o resto.*
3. **Decidir a forma do GD (C5)** e o gerador de λ (baseline vs 11.2) por Brier/RPS **com IC**.
4. **Extrair point-in-time:** `θ`/forma de `f(dr)`, `T_base`/`κ`, curva `P(E|dr)` (truncada), e calibrar `σ_R`/`σ_ref` contra a variância empírica dos erros.
5. **Ingerir StatsBomb (2018+2022, Euro, WWC)** → backtest com xG + prior de estilo.
6. **Contexto físico + regime (técnico novo) como diagnóstico**, promovendo a λ só com evidência (portão de 16).
7. **Monte Carlo do torneio + cenários de classificação determinísticos** — os insights de maior valor.
8. **Só então** pesos finos do ensemble (≥30 jogos) e `P_ad` (conforme o fork).

**Milestone de aceite:** backtest histórico com Elo corrigido por mando e σ_R, pipeline congelado e point-in-time, **Brier < uniforme com IC que não cruze o baseline**, ≈ Elo público, **P(V),P(D) ∈ [0,1] em todo |dr|** e **confiança não-crescente com a incerteza do rating**. Sem isso, o resto é decoração.

---
*Documento de planejamento v3 — sem código de implementação, por escopo. Consolida as correções aprovadas em [[camada1-revisao-v2]] (coerência [0,1] e incerteza honesta) sobre a base da v2 (anti-saturação, mando histórico). Tudo [a calibrar] é recalibrado na Camada 2/4. Fontes verificadas em 2026-06-15; snapshot local é a defesa. Probabilidades, nunca certezas — inclusive sobre o próprio modelo, não-validado até o primeiro backtest.*
