---
tags: [camada1, planejamento, historico]
status: historico
tipo: planejamento
data: 2026-06-15
aliases: ["Modelo v2"]
---

# Camada 1 — Planejamento Matemático e de Dados (v2 — corrigido)
**Projeto:** Sistema de previsão de partidas — Copa do Mundo 2026 (EUA/Canadá/México)
**Data:** 2026-06-15 · **Status:** planejamento (sem código) · **Custo-alvo:** R$ 0
**Supersede:** [[camada1-planejamento-v1]] (v1, 2026-06-12). Base da revisão: [[camada1-revisao]].

> Convenções: probabilidades em [0,1]; V/E/D = vitória A / empate / vitória B; λ = gols esperados; dr = diferença de Elo (A − B, já com mando); W_e = expectativa de pontuação do Elo. **[a calibrar]** = estimativa educada a fixar no backtest, não constante da literatura. Marcador **▲v2** sinaliza o que mudou em relação à v1 e por quê.

---

## 0. Changelog v2 (o que mudou e por quê)

| # | Correção | Severidade | Seções |
|---|---|---|---|
| C1 | **Gerador de gols não satura mais.** `GD = c·(W_e−0.5)` (teto ±1,5 gol) → `GD = θ·(dr/100)`; total `T_m` agora sensível ao mismatch. Goleadas tornam-se exprimíveis. | 🔴 estrutural | 8, 11 |
| C2 | **Mando explícito no Elo histórico.** Separa `H_hist` (mando aplicado a TODO jogo não-neutro do histórico, p/ construir o Elo) de `H_host2026` (bônus de anfitrião, só na previsão de 2026). | 🔴 estrutural | 3.1, 3.5, 8 |
| C3 | **Ataque/Defesa promovido a gerador de λ** (base Dixon-Coles) como upgrade priorizado #1 — corrige a perda de direção do `estilo`. Baseline V1 = fix simples (C1). | 🟡 → upgrade | 3.4, 4, 11 |
| C4 | **Ensemble e confiança honestos.** `P_poisson` e `P_elo` compartilham o Elo → a "concordância" vira `consistência_interna` (peso menor) e cria-se `corroboração_externa` (gap vs mercado). | 🟡 | 9, 14 |
| C5 | **Forma sem vazamento.** `PPJ_esperado` exige a curva de empate e Elo ponto-no-tempo (point-in-time) — dependência agora declarada. | 🟡 | 3.3 |
| C6 | **Validação com incerteza.** Bootstrap IC em Brier/RPS/LogLoss + teste pareado modelo-vs-mercado. Convenção do Brier fixada (forma soma). | 🟡 | 15 |
| C7 | **Dados gratuitos antes subestimados:** xG (StatsBomb Open Data) p/ backtest/prior; fadiga/viagem/altitude/calor deriváveis de graça (calendário + Open-Meteo). Entram como **diagnóstico**, promovidos só por backtest. | ⚪ → dados | 3.11, 5, 6 |
| C8 | **Matriz Poisson 0..10** (não 0..8) e BTTS/over recomputados da matriz quando Dixon-Coles entrar — consistência após C1. | ⚪ | 3.2, 11, 12 |
| C9 | **Insights promovidos:** Monte Carlo do torneio e sensibilidade por previsão viram saída de primeira classe. | ⚪ → produto | 4, 6-insights |

Princípio mantido da v1: **nada de certezas — só probabilidades**; tudo roda local; nenhuma previsão lê a internet no momento do cálculo (snapshot diário em disco).

---

## 1. Visão geral do sistema em camadas

| Camada | Função | Estado |
|---|---|---|
| 1 | Motor matemático e dados base | **este documento (v2)** |
| 2 | Coleta e normalização (CSV/JSON → SQLite local) | próxima |
| 3 | Detector de notícias/lesões/desfalques | depois da 2 |
| 4 | Sistema de previsão (ensemble) | consome 1–3 |
| 5 | Geração de insights/explicações | consome 4 |
| 6 | Interface local | última |

A Camada 1 define **contratos matemáticos** (entradas, fórmulas, saídas). As demais só alimentam ou consomem esses contratos. Mudança em qualquer fórmula desta camada = nova `versao_modelo` (esta passa a ser **v2.0**).

## 2. Objetivo da Camada 1

Especificar o pipeline que transforma dados públicos em: P(V), P(E), P(D), λ_A, λ_B, placares mais prováveis, P(over 2.5), P(ambos marcam), ajuste por desfalques, score de confiança e métricas de validação. Critério de pronto: qualquer dev implementa a Camada 4 lendo só este documento, e cada número de saída é rastreável a uma fórmula e a um dado de entrada (auditabilidade).

## 3. Cálculos recomendados

Pipeline (não modelos paralelos independentes): Elo (+ forma + desfalques + mando) estima a *diferença* de força; fatores ofensivos/defensivos estimam o *total* (e, no upgrade C3, a *direção*) de gols; Poisson converte em distribuição de placares; um mini-ensemble combina leituras; odds são benchmark externo.

### 3.1 Elo Rating (espinha dorsal) ▲v2 (C2)

**Funcionamento.** Cada seleção tem rating R. Após cada jogo:

```
R_novo = R_antigo + K · G · (W − W_e)
W_e = 1 / (1 + 10^(−dr/400))        dr = R_A − R_B + mando
W  = 1 vitória · 0.5 empate · 0 derrota
K  = 60 Copa · 50 continentais · 40 eliminatórias · 30 Nations League · 20 amistosos
G  = 1 (margem ≤1) · 1.5 (margem 2) · (11+N)/8 (margem N ≥ 3)
```

**▲v2 — Dois parâmetros de mando, antes fundidos por omissão.** O `mando` em `dr` NÃO é o mesmo número na construção do Elo e na previsão de 2026:

```
mando = H_hist        se construindo o Elo histórico E o jogo NÃO é neutro   # ver abaixo
      = H_host2026     se previsão 2026 E anfitrião jogando em solo próprio   # seção 3.5
      = 0              jogo neutro
```

- **`H_hist` = 100** (padrão eloratings.net) ou ajustado (fit) maximizando acurácia preditiva no histórico. **Aplica-se a TODO jogo não-neutro** do martj42 (a maioria do histórico é casa/fora — o dataset traz a flag `neutral` e a designação home/away justamente para isto). *Sem H_hist, todo jogo casa/fora seria tratado como neutro, os mandantes "surpreenderiam" o modelo e os ratings nasceriam enviesados/ruidosos — e o benchmark de sanidade contra eloratings.net (que usa mando) jamais fecharia.*
- **`H_host2026` = 60 [a calibrar]** (seção 3.5): efeito menor e específico, só para EUA/MEX/CAN em casa em 2026.

É a metodologia do World Football Elo Ratings (eloratings.net): mando, peso por competição e multiplicador de margem; inicialização em 1500; ratings com <30 jogos são **provisórios** (flag de baixa confiança). Sanidade: dr=+100 → W_e≈0.64; dr=+300 → W_e≈0.85.

**Inicialização.** Calcular **Elo próprio** sobre o histórico completo 1872–2026 (dataset martj42, seção 6), todos em 1500, **com H_hist aplicado aos jogos não-neutros**. Converge décadas antes de 2026, é reprodutível e permite variar K/G/H. O eloratings.net vira benchmark de sanidade (desvio aceitável: ±25 nas top-30; international-football.net como 2º benchmark). Alternativa rejeitada: converter ranking FIFA (sem multiplicador de margem nem mando; congela em amistosos fora de data FIFA — pior sinal).

**Vantagens.** Autocorretivo, robusto a dados esparsos (~10 jogos/ano por seleção), interpretável, padrão-ouro em seleções. **Limitações.** Reage devagar a mudança de geração/técnico; amistosos ruidosos mesmo com K=20; não separa ataque de defesa (daí 3.4); estreantes via repescagem chegam mal calibrados (flag de baixa confiança). **Aplicabilidade à Copa.** Alta: ratings chegam maduros das eliminatórias; K=60 reage dentro do torneio.

### 3.2 Poisson (gerador de placares) ▲v2 (C8)

**Funcionamento.** Gols de cada time ~ Poisson independente: `P(X=k) = e^(−λ) λ^k / k!`. Matriz `M[i][j] = P_A(i)·P_B(j)`. **▲v2: i,j = 0..10** (não 0..8) — necessário porque, corrigida a saturação (C1), os λ de favoritos crescem e a cauda passa a importar; somar o resíduo (>10) distribuído proporcionalmente na borda, não numa única célula.

**Derivações:**

```
P(V) = Σ M[i][j] (i>j)      P(E) = Σ M[i][i]      P(D) = Σ M[i][j] (i<j)
P(over 2.5)     = 1 − Σ M[i][j] (i+j ≤ 2)
P(ambos marcam) = (1 − e^(−λ_A)) · (1 − e^(−λ_B))
Placares prováveis = top-k células de M
```

**Limitações.** Independência entre ataques é falsa — subestima 0×0/1×1 e o empate em ~1–2 p.p.; **Dixon-Coles (C3) corrige isto e entra junto com o ataque/defesa** (quando entrar, recomputar over 2.5 e BTTS da matriz conjunta corrigida, não das fórmulas independentes). Não modela prorrogação, expulsões, estado de jogo. Em "biriba" de última rodada, nenhum Poisson salva → confiança baixa. **Aplicabilidade.** Alta para 90 min. No mata-mata, V/E/D = tempo normal; avanço = `P(V) + P(E)·(0.5 + ε·sinal(dr))`, ε ≈ 0.03 **[a calibrar]** (pênaltis ~ moeda).

### 3.3 Forma recente ▲v2 (C5)

**Funcionamento.** Janela das **últimas 10 partidas** (≈12–18 meses em seleções). Peso temporal exponencial e desconto de amistosos:

```
w_i = 0.9^(idade_em_meses) · (1.0 oficial · 0.5 amistoso)
PPJ_pond = Σ w_i · pontos_i / Σ w_i
```

Métrica **ajustada a adversário**: comparar o resultado com o esperado pelo Elo do adversário (senão "ganhou de 5 fracos" vira forma ótima). Conversão em ajuste de rating:

```
ΔE_forma = 15 · (PPJ_pond − PPJ_esperado)    cap ±30 Elo  [a calibrar]
```

**▲v2 — duas dependências antes implícitas, agora obrigatórias:** (a) `PPJ_esperado` = `3·P(V) + 1·P(E)` por jogo **exige a curva de empate `P(E|dr)`** (seção 9) — a forma não pode ser computada antes dela; (b) no backtest, usar **Elo na data de cada jogo (point-in-time)**, nunca o Elo final — senão há vazamento (look-ahead).

**Limitações.** Amostra minúscula; amistosos pré-Copa têm times experimentais (daí o cap agressivo); risco de dupla contagem com o Elo (que já absorveu esses jogos) — cap e peso baixo existem para isso. **Aplicabilidade.** Média; dentro do torneio o próprio K=60 já carrega a forma.

### 3.4 Força ofensiva/defensiva ▲v2 (C3)

**Baseline V1 (total, mantido).** Sobre a janela ponderada da forma:

```
tendência_gols_T = (gols_pró + gols_contra por jogo de T, ajustado pelo Elo médio dos adversários) / média_internacional
estilo_T = shrinkage(tendência_gols_T → 1.0, força = n_jogos/(n_jogos+10))
```

O shrinkage bayesiano (prior 1.0) impede que 6 jogos extremos definam o estilo. Na V1 o `estilo` escala o **total** (seção 8, passo 4).

**▲v2 — Upgrade priorizado #1 (direção de gols).** A v1 calculava fatores ataque/defesa e os descartava (só "explicação"). Isso joga fora a informação mais útil: o λ de A depende do **ataque de A contra a defesa de B**, não de um total simétrico. O upgrade gera λ direto por regressão Poisson com ataque/defesa (base Dixon-Coles) — ver seção 11.2. Promovido de "V1.5" para **logo após o 1º backtest**, porque conserta o erro 🔴 de direção e reforça a correção de saturação.

**Limitações.** Gols ≠ qualidade de chance (sem xG no fluxo ao vivo; xG histórico via StatsBomb entra no backtest, seção 3.11); ajuste por adversário é grosseiro via Elo médio. **Aplicabilidade.** Alta exatamente onde o Elo é cego: totais e direção de gols.

### 3.5 Mando de campo / campo neutro ▲v2 (C2)

Na Copa 2026 quase tudo é neutro, exceto **EUA, México e Canadá em casa**:

```
H_host2026 = +60 Elo  para anfitrião jogando no próprio país   [a calibrar]
           = 0         nos demais jogos (neutro)
```

Distinto de `H_hist` (=100, seção 3.1), que é parâmetro de **construção** do Elo, não de previsão. Justificativa do 60 < 100: público de Copa é mais misto que em eliminatória, mas anfitriões sobre-desempenham de forma consistente. Caso sem solução limpa: **México tem torcida majoritária em vários estádios dos EUA** ("quase-casa") — V1 ignora, mas o schema de partida prevê `bonus_mando_override` manual. Altitude (Cidade do México, 2.240 m) e calor: tratados como diagnóstico em 3.11, não no λ da V1.

**Dados.** Calendário com estádio/cidade/país (fixturedownload/openfootball) + flag `anfitriao_em_casa`. **Limitação.** O valor 60 é incerto (amostra de anfitriões é pequena: 1 a cada 4 anos).

### 3.6 Lesões e desfalques — resumo
Representação completa na **seção 13**. V1: entrada por JSON manual (o detector de notícias é Camada 3).

### 3.7 Odds gratuitas (benchmark)

```
p_i = (1/odd_i) / Σ_j (1/odd_j)        (de-vig proporcional; Shin fica p/ V2)
```

**Benchmark, não input.** O mercado é o preditor mais calibrado disponível; comparar Brier do modelo vs. do mercado é o teste de honestidade do projeto. Peso ≤ 0.20 no ensemble **só se** a odd for capturada manualmente pré-jogo; sem odd, renormalizar. **Realidade (2026-06):** The Odds API degradou o free tier (25 req/dia, só NBA/MLB). Sem API de odds de Copa gratuita confiável — plano real é **captura manual** (1 min/jogo, com timestamp), digitada em CSV. Não inventar fonte.

### 3.8 Ensemble — resumo ▲v2 (C4)
Detalhe nas seções 9–10. **▲v2:** as leituras `P_poisson` e `P_elo` **compartilham o Elo** — não são independentes. A diversidade real do ensemble vem do mercado (V1) e, no upgrade C3, da leitura ataque/defesa (que não passa por W_e). Tratado em 9 e 14.

### 3.9 Nível de confiança — resumo
Seção 14. Confiança é metadado sobre a previsão, não probabilidade. **▲v2:** "concordância" foi desmembrada em consistência interna (peso menor) + corroboração externa.

### 3.10 Validação — resumo
Seção 15. Brier + LogLoss + RPS + calibração, **com IC bootstrap** (C6) e registro pré-jogo imutável.

### 3.11 Contexto físico e xG (diagnóstico) ▲v2 (C7) — NOVO

Variáveis gratuitas e locais que a v1 subestimou. **Entram como diagnóstico e/ou modificador de confiança; viram termo de λ apenas se passarem no portão de backtest** (seção 16) — caso contrário só adicionam ruído:

- **xG (StatsBomb Open Data).** Eventos com xG, grátis e sem key, para torneios selecionados (Copa 2018, Euro, Copa Feminina 2019/2023). Não cobre as 48 seleções nem é ao vivo. Usos: backtest com "resultado merecido" (xG vs placar), prior de estilo menos ruidoso que gols brutos, e validação do gerador de λ. Licença não-comercial (ok p/ estudo).
- **Fadiga / descanso (calendário, já em mãos).** Dias de descanso e **descanso diferencial** entre os dois times — derivável direto de fixturedownload. Efeito assimétrico é dos mais documentados e custa zero.
- **Viagem (haversine entre sedes).** Distância entre cidades de jogos consecutivos; coordenadas via Open-Meteo Geocoding (sem key) ou hardcode das 16 sedes.
- **Altitude (estática, grátis).** Cidade do México ~2.240 m. Elevação via Open-Meteo Elevation API (sem key) ou Wikidata. V1: redutor de confiança para visitante não-aclimatado; eventual ajuste em λ.
- **Calor (Open-Meteo, sem key).** Temperatura/umidade no kickoff (histórico desde 1940 + previsão 16 dias). Calor extremo reduz ritmo/total de gols. Efeito pequeno, fácil de overfittar — candidato.
- **Idade média / caps do elenco (Wikipedia, já usada).** Proxy de experiência/volatilidade. Custo baixo.

Não perseguir (sem fonte gratuita estruturada p/ seleções, baixo valor): posse de bola, distância percorrida.

## 4. Cálculos fora da V1 (e por quê) ▲v2

**Upgrade priorizado #1 (logo após o 1º backtest): ataque/defesa Poisson + Dixon-Coles** (C3) — corrige direção e reforça anti-saturação; ~poucas dezenas de linhas. **Insight near-term (barato): simulação Monte Carlo do torneio** (C9) — produto derivado do modelo de jogo. Continuam fora: **Poisson bivariado** (ganho marginal sobre Dixon-Coles, custo alto); **xG ao vivo** (sem fonte gratuita p/ as 48 seleções — só backtest); **modelos hierárquicos bayesianos** (matam a auditabilidade da V1); **ML/boosting** (~100 jogos + features fracas = overfit); **ratings por jogador** (manual proibitivo p/ 48 seleções); **clima/altitude/viagem como termo de λ** (entram antes como diagnóstico, 3.11); **de-vig de Shin**; **ajuste por incentivos de última rodada** (sem modelo confiável → confiança baixa).

## 5. Dados necessários por cálculo ▲v2

| Cálculo | Dado | Granularidade | Histórico mínimo |
|---|---|---|---|
| Elo (+ H_hist) | data, times, placar, competição, flag neutro, home/away | por jogo | 1950+ (ideal 1872+) |
| Forma | idem + data p/ decaimento + curva P(E|dr) | por jogo | últimos 10/time |
| Estilo / Ataque-Defesa | placares + Elo do adversário na data | por jogo | últimos 10–20/time (full p/ ataque/defesa) |
| Mando 2026 | estádio, cidade, país-sede | por jogo da Copa | só 2026 |
| Poisson | λ_A, λ_B (derivados) | por jogo | — |
| Desfalques | lista de ausentes + tier | por jogo | elenco atual |
| Odds | 1X2 decimal + timestamp | por jogo | só 2026 (prospectivo) |
| Contexto físico (diag.) | descanso, viagem, altitude, temp, idade | por jogo | 2026 + histórico p/ calibrar |
| xG (backtest) | xG por jogo (StatsBomb) | por jogo | torneios cobertos |
| Validação | resultado final + tudo registrado pré-jogo | por jogo | acumula |

## 6. Fontes gratuitas recomendadas (verificadas em 2026-06-15) ▲v2

| Fonte | Dado | Grátis? | Key? | Limitações | Confiab. | Papel | Fallback |
|---|---|---|---|---|---|---|---|
| **martj42/international_results** | resultados 1872–2026, torneio, flag neutro, home/away | Sim | Não | atualização por PR (horas–dias de lag) | Alta | **nº 1** | openfootball; manual |
| **fixturedownload.com** (wc-2026) | calendário+resultados; **base p/ descanso/viagem** | Sim | Não | só jogos | Alta | **Sim** | openfootball/worldcup.json |
| **openfootball/worldcup.json** | calendário/resultados 2026 JSON | Sim | Não | lag comunitário | Média-alta | redundância | fixturedownload |
| **football-data.org** | jogos, resultados, classificação | Sim (free) | Sim (grátis) | 10 req/min; sem escalações no free | Alta | automação de resultados | martj42 + manual |
| **Elo próprio** (do martj42, c/ H_hist) | rating de força | Sim | Não | depende do dataset base | Alta (auditável) | **recomendado** | snapshot eloratings.net |
| **eloratings.net** | Elo benchmark | Sim | Não | sem API; SPA sobre TSV | Alta | sanidade | calcular próprio |
| **international-football.net** ▲ | Elo alternativo | Sim | Não | metodologia difere | Média | **2º benchmark** de sanidade | eloratings.net |
| **StatsBomb Open Data** (GitHub) ▲ | eventos + **xG**, escalações; WC2018/Euro/WWC | Sim | Não | só torneios selec.; não ao vivo; licença **não-comercial** | Alta | **backtest xG + prior** | FBref (visual) |
| **Open-Meteo** ▲ | temp/umidade kickoff (1940+ e previsão) | Sim | **Não** | uso não-comercial; efeito pequeno | Alta | calor + confiança | ignorar |
| **Open-Meteo Elevation/Geocoding** ▲ | altitude do estádio; coordenadas das sedes | Sim | **Não** | — | Alta | altitude + viagem (haversine) | Wikidata; hardcode |
| **Wikidata (SPARQL)** ▲ | coords/elevação/capacidade de estádios | Sim | Não | semiestruturado | Média-alta | redundância geo | Open-Meteo |
| **Wikipedia — elencos 2026** | convocações, idade, caps, clube | Sim | Não | parsing manual | Alta na Copa | convocações + idade | site FIFA |
| **BALLDONTLIE FIFA API** | jogos, elencos, odds | Free tier | Sim | limites não documentados — testar | Média (validar) | opcional | nenhum |
| **The Odds API** | odds | **Não serve** (25/dia, NBA/MLB) | — | sem futebol no free | — | **Não** | captura manual |
| **FBref / Transfermarkt** | minutos, valor de mercado, xG visual | Visualização | Não | **ToS restringe scraping**; manual pontual | Alta | só consulta manual | tiers manuais |
| **Lesões/desfalques** | — | — | — | **Sem fonte estruturada gratuita p/ 48 seleções** | — | — | JSON manual (V1); RSS na C3 |

Lacunas reconfirmadas (não inventar): odds gratuitas via API (segue captura manual) e lesões estruturadas (segue JSON manual + RSS na Camada 3).

## 7. Dados que precisarão ser manuais no início
Snapshot do eloratings.net + international-football.net para sanidade (1x, pré-torneio); **tiers de jogadores** só para as ~16 seleções com chance real + sob demanda; **JSON de desfalques** por jogo; **odds 1X2** digitadas pré-jogo com timestamp; override de mando (México em solo americano); resultado de pênaltis (conferir convenção do martj42: registra placar ao fim da prorrogação + `shootouts.csv` separado).

## 8. Fórmula inicial do modelo (pipeline completo) ▲v2 (C1, C2)

```
ENTRADAS: R_A, R_B (Elo próprio, já com H_hist) · forma · estilo (of/def) · desfalques · flag mando 2026

1) Elo ajustado:    R'_T = R_T + ΔE_forma(T) + ΔE_desfalques(T)
2) Diferença:       dr   = R'_A − R'_B + H_host2026         # H_host2026 = 60 se anfitrião, senão 0
3) Saldo esperado:  GD   = θ · (dr/100)                     # ▲v2: θ ~ 0.45 [a calibrar]. NÃO satura.
4) Total esperado:  T_m  = (T_base + κ·|dr|/100) · estilo_A · estilo_B
                                                            # ▲v2: T_base=2.6, κ~0.10 [a calibrar]. Mismatch → mais gols.
5) Gols esperados:  λ_A = max(0.2, (T_m + GD)/2)   λ_B = max(0.2, (T_m − GD)/2)
6) Matriz Poisson:  M[i][j] = Pois(i;λ_A)·Pois(j;λ_B),  i,j = 0..10 (resíduo distribuído)
7) Saídas Poisson:  V/E/D, over 2.5, BTTS, top placares (seções 10–12)
8) Leitura Elo-direto (independente p/ ensemble): W_e + curva P(E|dr) (seção 9)
9) Ensemble final:  seção 9–10
```

**Sanidade ▲v2 (θ=0.45, κ=0.10, T_base=2.6, estilos=1.0):**

| dr | GD = θ·dr/100 | T_m | λ_A | λ_B | leitura |
|---:|---:|---:|---:|---:|---|
| 100 | 0.45 | 2.70 | 1.58 | 1.13 | favorito leve |
| 300 | 1.35 | 2.90 | 2.13 | 0.78 | favorito claro (~2×1) |
| 600 | 2.70 | 3.20 | 2.95 | 0.25 | goleada provável (~3×0) |
| 900 | 4.05 | 3.50 | 3.78 | 0.20 | goleada (~4×0) |

Compare com a v1 (teto λ_favorito ≈ 2.05 e GD ≤ 1.5 **para qualquer dr**): agora o sistema **exprime goleada**, sem violar nada (λ_B clampa em 0.2, o azarão nunca fica sem chance). θ, κ e T_base saem de **regressão `saldo_real ~ dr/100` e média de gols por Copa no histórico** (point-in-time), não de palpite.

## 9. Pesos iniciais do ensemble ▲v2 (C4)

| Componente | O que é | Peso c/ odds | Peso s/ odds |
|---|---|---|---|
| P_poisson | V/E/D da matriz do pipeline (passo 8) | 0.45 | 0.56 |
| P_elo | V/E/D direto: W_e + curva de empate | 0.35 | 0.44 |
| P_mercado | odds de-vigadas (quando capturadas) | 0.20 | 0.00 |

`P_elo` precisa da curva de empate (W_e não separa empate de vitória): estimar `P(E|dr)` **empiricamente do martj42** em faixas de |dr| (ordem de grandeza: ~26% com |dr|<50, caindo a ~15% com |dr|>300 — **extrair as curvas reais no backtest**). Então `P(V) = W_e − P(E)/2`, `P(D) = 1 − P(V) − P(E)`.

Combinação: **média linear em espaço de probabilidade** (pool linear), renormalizada. **▲v2 — diversidade real:** `P_poisson` e `P_elo` compartilham o Elo, logo o par 0.45+0.35 é, na prática, ~0.80 num único sinal Elo + 0.20 de mercado. Implicações: (1) não ler concordância Poisson↔Elo como corroboração (seção 14); (2) o **upgrade C3 adiciona `P_ad`** (ataque/defesa, não ancorado em W_e) como 3ª leitura genuinamente independente — quando entrar, redistribuir para algo como 0.35/0.25/0.20/0.20 (Poisson/Elo/AD/mercado). Ajuste futuro: após ≥30 jogos, otimizar pesos minimizando Brier em janela móvel (grid search); congelar pesos durante cada fase do torneio.

## 10. Cálculo da probabilidade final V/E/D

```
P_final(x) = w_p·P_poisson(x) + w_e·P_elo(x) + w_m·P_mercado(x),   x ∈ {V,E,D}
renormalizar: P_final(x) ← P_final(x) / Σ_x P_final(x)
```

Pós-processamento: clamp de cada probabilidade em [0.02, 0.96] e **renormalizar (iterar 1–2x** para o clamp não ser desfeito pela renormalização) — nunca prometer certeza (requisito do produto). No mata-mata, publicar `P(avança) = P(V) + P(E)·(0.5 + 0.03·sinal(dr))` com rótulo de que V/E/D é tempo normal.

## 11. Cálculo de gols esperados ▲v2

### 11.1 Baseline V1 (corrigido — C1)
É o passo 3–5 da seção 8. Pontos de atenção: (a) `estilo` usa shrinkage → 1.0 (sem isso, 3 jogos de 4 gols viram "ataque infinito"); (b) **GD é linear em dr (`θ·dr/100`), não em `W_e−0.5`** — é o que remove a saturação; (c) `T_m` cresce com |dr| (κ) porque mismatch gera mais gols; (d) desfalques entram **antes**, via ΔE no Elo ajustado (uma porta, sem dupla contagem); (e) λ mínimo 0.2; (f) T_base=2.6 vem da média de gols/jogo das últimas Copas (2018: 2.64; 2022: 2.69) — recalibrar após a 1ª rodada com cautela (16 jogos é amostra fraca; mover no máx ±0.15).

### 11.2 Upgrade priorizado #1 — Ataque/Defesa + Dixon-Coles (C3)
Substitui o total simétrico por geração direcional de λ:

```
ln λ_A = μ + ATA_A + DEF_B + γ·mando_A
ln λ_B = μ + ATA_B + DEF_A
# ATA_T, DEF_T: parâmetros por time, MLE sobre gols históricos, com SHRINKAGE → 0 (L2)
#   — indispensável p/ seleções com poucos jogos contra elite.
# Âncora-Elo (preserva a espinha dorsal): prior penalizando desvio de (ATA_T − DEF_T) vs f(R_T).
# Dixon-Coles: M_corrigida[i][j] = M[i][j] · τ(i,j; λ_A,λ_B,ρ), ρ<0  → corrige 0-0,1-0,0-1,1-1.
```

Vantagens: dá **direção** (ataque de A × defesa de B), total e diferença coerentes; permite goleada; padrão da literatura; **auditável** (ATA/DEF por time inspecionáveis). Quando entrar, recomputar over 2.5 e BTTS da matriz conjunta corrigida e adicionar `P_ad` ao ensemble (seção 9).

## 12. Cálculo de placares prováveis ▲v2
Top-k células da matriz M (k=5), com probabilidade exibida. Com λs típicos, o placar modal fica ~10–12% — **comunicar que "placar mais provável" ainda é improvável** (~88% de chance de NÃO ser ele): requisito de UX que nasce da matemática daqui. Matriz **0..10** (C8). Sem Dixon-Coles, 0×0/1×1 levemente subestimados (viés conhecido); com 11.2, corrigido.

## 13. Tratamento matemático de lesões/desfalques

Entrada (V1, manual; Camada 3 automatiza a *detecção*, nunca a fórmula):

```json
{"jogo": "BRA-x-MAR-2026-06-15", "desfalques_A": [{"nome":"...","tier":1,"setor":"ataque"}], "desfalques_B": []}
```

**Tiers** (proxy de minutos/titularidade nos últimos 12 meses, atribuição manual via FBref/Transfermarkt visual):

```
tier 1 — estrela/titular indispensável:  ΔE = −35 Elo   [a calibrar]
tier 2 — titular padrão:                 ΔE = −15
tier 3 — rotação/reserva relevante:      ΔE = −5
ΔE_desfalques(T) = max(−120, Σ ΔE_i)     (cap: elenco de 26 não vira juvenil)
```

Ordem de grandeza defensável: −35 Elo move W_e em ~5 p.p. num jogo parelho (compatível com estimativas públicas; "Messi ≈ 50 Elo" é topo de escala). **Incerteza alta e declarada** — é o parâmetro mais "no olho" do sistema. Refinamento V1.5 (junto com 11.2): split direcional — desfalque ofensivo corta λ_pró, defensivo/goleiro infla λ_contra. Na V1, tudo agregado no Elo (uma porta). "Dúvida" = meio-tier e derruba a robustez da confiança (seção 14).

## 14. Cálculo de nível de confiança ▲v2 (C4)

Confiança ≠ probabilidade: metascore de quanto o sistema acredita na própria distribuição.

```
separação    = clamp((p_max − 1/3)/(2/3), 0, 1)                 # jogo definido pontua alto
consist_int  = 1 − TV(P_poisson, P_elo)                          # ▲v2: consistência INTERNA (compartilham Elo)
corrob_ext   = 1 − TV(P_modelo, P_mercado)  (=0.5 neutro se sem odd)   # ▲v2: corroboração EXTERNA real
dados        = checklist 0–1: ≥8 jogos oficiais (0.4) · escalações confirmadas (0.4) · Elo maduro/não-estreante (0.2)
robustez     = 1 − incerteza de desfalques (dúvidas derrubam)
TV(p,q) = 0.5 · Σ_x |p(x) − q(x)|

score = 100 · (0.35·separação + 0.15·consist_int + 0.15·corrob_ext + 0.20·dados + 0.15·robustez)
        × 0.90 se mata-mata  × 0.85 se última rodada com incentivo cruzado
rótulos: ≥65 alta · 40–64 média · <40 baixa
```

**▲v2 — por que mudou:** na v1 a "concordância" entre Poisson e Elo entrava com peso 0.25, mas as duas leituras compartilham o Elo → ela media consistência interna do tratamento de empate, não corroboração, e inflava a confiança. Agora: `consist_int` (peso menor, 0.15) e `corrob_ext` vs mercado (0.15). Sem odd, `corrob_ext`=0.5 (neutro) e renormaliza-se o restante. Pesos somam 1.00; todos **[a calibrar]**. **Jogos equilibrados:** separação≈0 força confiança média/baixa por construção — o sistema diz "jogo aberto, V 34% / E 30% / D 36%" e **não** fabrica favorito.

## 15. Validação pós-jogo ▲v2 (C6)

**Registro pré-jogo (imutável, append-only):** `match_id, timestamp_previsao, fase, times, R'_A, R'_B, λ_A, λ_B, P(V/E/D), P(over2.5), P(BTTS), top-5 placares, confiança, desfalques, odds capturadas, versao_modelo, hash_inputs`. Previsão registrada **antes** do kickoff nunca é editada — sem isso, qualquer métrica é autoengano.

**Métricas (convenção fixada: Brier forma-soma, máx 2):**

```
Brier (multiclasse, soma) = (1/N) Σ_jogos Σ_x (P(x) − o(x))²
   baselines: uniforme = 0.667 · mercado ≈ 0.55–0.60 · meta: < 0.62 E < mercado
LogLoss = −(1/N) Σ ln P(resultado)        uniforme = ln3 ≈ 1.099
RPS = (1/2)[(P_V − O_V)² + ((P_V+P_E) − (O_V+O_E))²]   # ordinal, a mais adequada p/ 1X2 — reportar as três
```

**▲v2 — incerteza obrigatória (anti-autoengano):**

```
# Bootstrap (reamostrar jogos c/ reposição, B=10000): IC95 de Brier, RPS, LogLoss.
# Teste pareado modelo vs mercado, por jogo: diff_i = Brier_modelo_i − Brier_mercado_i
#   reportar média(diff) com IC bootstrap (ou Wilcoxon). "Bater o mercado" exige IC que NÃO cruze 0.
# Ao importar Brier de mercado publicado, confirmar a MESMA convenção (soma vs média = fator 3).
```

**Acerto vs. calibração:** "acertou o resultado" (argmax) é fraco — chutar o favorito dá ~50%. O que importa é **calibração**: dos jogos em que o sistema disse 60%, ~60% aconteceram? Diagrama de confiabilidade por faixas (33–45, 45–60, 60–75, >75), **só com ≥20 jogos por faixa**. A Copa tem 104 jogos → barra de erro grande; por isso a validação séria é o **backtest histórico** (Copas 2014/18/22 + Euros + Copas América ≈ 400+ jogos), pipeline **congelado e point-in-time**, exigindo Brier < uniforme (com IC) e ≈ Elo público. Comparação com mercado em jogos passados é inviável (sem odds históricas internacionais gratuitas) → será **prospectiva** em 2026, com as odds capturadas manualmente.

## 16. Riscos e limitações ▲v2

**Mantidos da v1:** amostra pequena em tudo (104 jogos p/ validar, ~10/ano por seleção — o sistema vive de shrinkage e caps; quem promete precisão está vendendo); formato de 48 times sem histórico comparável e com incentivos de fim de grupo que nenhum modelo de força capta; fontes gratuitas que atrasam/morrem (mitigação: snapshot local diário; nada lê a internet na hora); eco do mercado (manter odds ≤0.20); overfitting de pesos (<30 jogos é ruído); desfalques no olho (−35/−15/−5, elo mais fraco); prorrogação/pênaltis fora do modelo; escalações ~1h antes (previsão oficial = snapshot da manhã); ToS de FBref/Transfermarkt (só consulta visual); **apostas: Brier ~0.60 não é edge sobre mercado com margem — não é ferramenta de lucro, e isso fica escrito na interface.**

**Novos (introduzidos pelas melhorias):**
- **Overfitting cresce com cada variável nova** (xG, descanso, viagem, altitude, calor, idade) contra amostras minúsculas. **Portão obrigatório:** toda variável entra como diagnóstico e só vira termo de λ se melhorar Brier/RPS com **IC que não cruze zero** (seção 15). Sem o portão, as adições pioram o sistema.
- **Ataque/Defesa (11.2) exige dados suficientes por seleção;** sem shrinkage forte + âncora-Elo, ATA/DEF de seleções com poucos jogos ficam instáveis.
- **StatsBomb:** licença não-comercial e cobertura parcial (alguns torneios) → **ativo de backtest/enriquecimento, não feed ao vivo das 48 seleções.** Não construir dependência operacional sobre ele.
- **Clima/altitude/viagem têm efeito pequeno e incerto** → manter como modificadores de confiança antes de virarem termos de λ.
- **Staleness das fontes:** verificadas em 2026-06-15, mas ToS/free tiers mudam; a disciplina de snapshot local cobre StatsBomb e Open-Meteo.

**Incerto mesmo após as correções (declarado):** tamanho real de `H_host2026`, tiers de desfalque, efeito de altitude/calor, México como "quase-casa". As correções tornam isso explícito e calibrável — não o eliminam.

## 17. Roadmap por camadas ▲v2

**C1 (agora):** este documento (v2) aprovado = contrato matemático congelado (mudança → nova versao_modelo). **C2:** ingestão martj42 + fixturedownload → SQLite; **cálculo do Elo histórico com H_hist**; milestone de saída: **backtest 2014/18/22 + Euro/Copa América com Brier < 0.62 (IC) e < Elo público**. **C2.5 (novo upgrade priorizado):** ataque/defesa + Dixon-Coles (11.2) e re-backtest. **C3:** desfalques — JSON manual → RSS/notícias no mesmo JSON (fórmula da seção 13 não muda). **C4:** ensemble + curva de empate + calibração dos [a calibrar] (θ, κ, T_base, pesos, tiers) + leitura independente P_ad. **C5:** insights — cada previsão com fatores (Elo base, ajustes, λs, confiança, porquês), **+ Monte Carlo do torneio + sensibilidade por previsão**. **C6:** interface local lendo o SQLite. Dependências: 4 exige 2; 5 exige 4; 3 é paralelizável.

## 18. Próxima etapa recomendada ▲v2 (ordem importa)

1. **Rebuild do Elo com mando histórico (C2).** Definir `H_hist` (100 ou fit), aplicar a todo jogo não-neutro do martj42, recomputar e **só então** validar contra eloratings.net (±25 top-30) e international-football.net. *Desbloqueia todo o resto.*
2. **Trocar o gerador de gols (C1).** Implementar `GD = θ·dr/100` + `T_m` sensível a mismatch (11.1); avaliar 11.2 (ataque/defesa) como gerador primário. Decidir entre os dois por Brier/RPS **com IC**.
3. **Extrair as constantes em aberto point-in-time:** `θ` (saldo×dr/100), `T_base`/`κ`, e a curva `P(E|dr)`. Só com dados anteriores a cada jogo (anti-look-ahead, seção 3.3).
4. **Ingerir StatsBomb Open Data** (WC2018, Euro, WWC2023) → backtest com xG + teste do prior de estilo (xG vs gols).
5. **Adicionar contexto físico como diagnóstico** (descanso, viagem via Open-Meteo, altitude, temp). Promover a termo de λ só com evidência de backtest (portão da seção 16).
6. **Reforçar a validação** com bootstrap IC + teste pareado vs mercado (15) antes de declarar vitória.
7. **Construir Monte Carlo do torneio** e padronizar a **saída de sensibilidade por previsão** (já demonstrada no CAN×BIH) — os insights de maior valor.
8. **Só então** ajustar pesos finos do ensemble (≥30 jogos) e introduzir `P_ad` para restaurar a diversidade real (seção 9).

**Milestone de aceite:** backtest histórico com Elo corrigido por mando, pipeline congelado e point-in-time, **Brier < uniforme com IC que não cruze o baseline** e ≈ Elo público. Sem isso, o resto é decoração.

---
*Documento de planejamento v2 — sem código de implementação, por escopo. Correções 🔴 (C1 saturação de gols, C2 mando histórico) integradas ao contrato matemático. Tudo [a calibrar] é recalibrado na Camada 2/4. Fontes verificadas em 2026-06-15; snapshot local é a defesa contra mudança de disponibilidade.*
