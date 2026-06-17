---
tags: [camada1, planejamento, historico]
status: historico
tipo: planejamento
data: 2026-06-12
aliases: ["Modelo v1"]
---

# Camada 1 — Planejamento Matemático e de Dados
**Projeto:** Sistema de previsão de partidas — Copa do Mundo 2026 (EUA/Canadá/México)
**Data:** 2026-06-12 · **Status:** planejamento (sem código) · **Custo-alvo:** R$ 0

> Convenções: probabilidades em [0,1]; V/E/D = vitória A / empate / vitória B; λ = gols esperados; dr = diferença de Elo (A − B, já com bônus de mando). Valores marcados como **[chute inicial]** são estimativas educadas a calibrar em backtest — não são constantes da literatura.

---

## 1. Visão geral do sistema em camadas

| Camada | Função | Estado |
|---|---|---|
| 1 | Motor matemático e dados base | **este documento** |
| 2 | Coleta e normalização (CSV/JSON → SQLite local) | próxima |
| 3 | Detector de notícias/lesões/desfalques | depois da 2 |
| 4 | Sistema de previsão (ensemble) | consome 1–3 |
| 5 | Geração de insights/explicações | consome 4 |
| 6 | Interface local | última |

Princípio arquitetural: a Camada 1 define **contratos matemáticos** (entradas, fórmulas, saídas). As camadas seguintes só alimentam ou consomem esses contratos. Tudo roda local, com snapshot diário das fontes em disco — nenhuma previsão pode depender de fonte online no momento do cálculo.

## 2. Objetivo da Camada 1

Especificar o pipeline que transforma dados públicos em: P(V), P(E), P(D), λ_A, λ_B, placares mais prováveis, P(over 2.5), P(ambos marcam), ajuste por desfalques, score de confiança e métricas de validação. Critério de pronto: qualquer dev implementa a Camada 4 lendo só este documento, e o modelo é auditável (cada número de saída rastreável a uma fórmula e a um dado de entrada).

## 3. Cálculos recomendados

Arquitetura em **pipeline**, não modelos paralelos independentes: Elo (+ forma + desfalques + mando) estima a *diferença* de força; fatores ofensivos/defensivos estimam o *total* de gols; Poisson converte (diferença, total) em distribuição de placares; um mini-ensemble combina as leituras de probabilidade; odds servem de benchmark externo.

### 3.1 Elo Rating (espinha dorsal)

**Funcionamento.** Cada seleção tem um rating R. Após cada jogo:

```
R_novo = R_antigo + K · G · (W − W_e)
W_e = 1 / (1 + 10^(−dr/400))        dr = R_A − R_B + bônus_mando
W  = 1 vitória · 0.5 empate · 0 derrota
K  = 60 Copa do Mundo · 50 continentais · 40 eliminatórias · 30 Nations League · 20 amistosos
G  = 1 (margem ≤1) · 1.5 (margem 2) · (11+N)/8 (margem N ≥ 3)
```

É a metodologia do World Football Elo Ratings (eloratings.net), que usa +100 de mando padrão. Sanidade: dr=+100 → W_e≈0.64; dr=+300 → W_e≈0.85.

**Inicialização.** Recomendado: **calcular Elo próprio** rodando o algoritmo sobre o histórico completo 1872–2026 (dataset martj42, seção 6), todos começando em 1500. Converge décadas antes de 2026, é reprodutível, sem dependência de scraping, e permite variar K/G. O eloratings.net vira benchmark de sanidade (desvio típico aceitável: ±25 pontos nas top 30; se maior, revisar implementação). Alternativa rejeitada: converter ranking FIFA — desde 2018 a FIFA usa fórmula tipo-Elo, mas sem multiplicador de margem e sem mando, e o ranking congela em amistosos fora de data FIFA; pior sinal.

**Dados.** Data, times, placar, tipo de competição, flag de campo neutro — tudo no dataset martj42.

**Vantagens.** Autocorrertivo, robusto a dados esparsos (seleções jogam ~10 jogos/ano), interpretável, padrão-ouro em futebol de seleções.

**Limitações.** Reage devagar a mudanças bruscas (troca de geração/técnico); amistosos são ruidosos mesmo com K=20; não separa ataque de defesa (por isso os fatores da seção 3.4); seleções com poucos jogos contra elite (estreantes via repescagem) chegam com rating mal calibrado — flag de baixa confiança.

**Aplicabilidade à Copa.** Alta: ratings chegam "maduros" das eliminatórias; atualização pós-jogo com K=60 reage dentro do próprio torneio.

### 3.2 Poisson (gerador de placares)

**Funcionamento.** Gols de cada time ~ Poisson independente: `P(X=k) = e^(−λ) λ^k / k!`. Matriz de placares `M[i][j] = P_A(i)·P_B(j)` para i,j = 0..8 (cauda >8 é desprezível, somar resíduo na última célula).

**Derivações da matriz:**

```
P(V) = Σ M[i][j] para i>j      P(E) = Σ M[i][i]      P(D) = Σ M[i][j] para i<j
P(over 2.5)  = 1 − Σ M[i][j] para i+j ≤ 2
P(ambos marcam) = (1 − e^(−λ_A)) · (1 − e^(−λ_B))
Placares prováveis = top-k células de M
```

**Dados.** Apenas λ_A e λ_B, produzidos pelas seções 11.

**Vantagens.** Barato, fecha todas as saídas do sistema (placar, V/E/D, over, BTTS) com um único par de parâmetros; bem estudado (Maher 1982).

**Limitações.** Independência entre os ataques é falsa — subestima 0x0/1x1 e o empate em ~1–2 p.p.; correção de Dixon-Coles fica para V1.5 (seção 4). Não modela prorrogação, expulsões, estado do jogo. Em jogos de "biriba" (último jogo de grupo com resultado combinando para ambos), nenhum Poisson salva — tratar via confiança baixa.

**Aplicabilidade à Copa.** Alta para 90 minutos. No mata-mata, V/E/D refere-se ao tempo normal; avanço = `P(V) + P(E)·(0.5 + ε·sinal(dr))`, ε ≈ 0.03 **[chute inicial]** para o favorito (pênaltis são quase moeda).

### 3.3 Forma recente

**Funcionamento.** Janela das **últimas 10 partidas oficiais ou amistosos** (≈ 12–18 meses em seleções — janela maior dilui, menor é ruído puro). Peso temporal exponencial e desconto de amistosos:

```
w_i = 0.9^(idade_em_meses) · (1.0 se oficial · 0.5 se amistoso)
PPJ_pond = Σ w_i · pontos_i / Σ w_i
```

Métrica central **ajustada a adversário**: comparar resultado obtido com o esperado pelo Elo do adversário (sobre/subdesempenho), senão "ganhou de 5 fracos" vira forma ótima. Conversão em ajuste de rating:

```
ΔE_forma = 15 · (PPJ_pond − PPJ_esperado_por_Elo)    cap em ±30 pontos Elo  [chute inicial]
```

**Dados.** Mesmos do Elo. xG por jogo de seleções **não existe em fonte gratuita estruturada** — fora da V1, declarado.

**Vantagens.** Captura momento que o Elo demora a absorver (técnico novo, geração em ascensão).

**Limitações.** Amostra minúscula e amistosos pré-Copa têm times mistos/experimentais — por isso o cap agressivo. Risco real de dupla contagem com o Elo (que já absorveu esses jogos); o cap e o peso baixo existem para isso.

**Aplicabilidade à Copa.** Média. Útil na fase de grupos; dentro do torneio a própria atualização Elo (K=60) já carrega a forma.

### 3.4 Força ofensiva e defensiva

**Funcionamento.** O Elo define a *diferença* esperada; o estilo define o *total*. Para cada time, sobre a mesma janela ponderada da forma:

```
tendência_gols_T = (gols_pró + gols_contra por jogo de T, ajustado por Elo médio dos adversários) / média_internacional
estilo_T = shrinkage(tendência_gols_T → 1.0, força = n_jogos/(n_jogos+10))
```

O shrinkage bayesiano (prior = 1.0, média global) impede que 6 jogos extremos definam o estilo. Separadamente, fatores ataque/defesa (gols pró ajustados, gols contra ajustados) alimentam a explicação dos insights (Camada 5) e o split direcional de desfalques (V1.5). Desempenho vs. fortes/fracos: particionar por Elo do adversário (corte: top 30) — na V1 apenas como **diagnóstico** exibido, não como termo do modelo (amostra pequena demais para virar parâmetro).

**Dados.** Placares por jogo + Elo do adversário na data — dataset martj42 + série Elo própria.

**Vantagens.** Diferencia "Espanha 3x2" de "Marrocos 1x0" com mesmo Elo; melhora over/under e BTTS sem tocar no V/E/D.

**Limitações.** Gols ≠ qualidade de chance (sem xG); ajuste por adversário é grosseiro via Elo médio.

**Aplicabilidade à Copa.** Alta exatamente onde o Elo é cego: totais de gols.

### 3.5 Mando de campo / campo neutro

**Funcionamento.** Na Copa 2026 quase tudo é neutro, com três exceções: **EUA, México e Canadá jogando em casa**. Aplicação:

```
bônus_mando = +60 Elo para anfitrião em jogo no próprio país   [chute inicial]
            = 0 nos demais jogos (neutro)
```

Justificativa do 60 (e não 100 padrão): público de Copa é mais misto que em eliminatória, mas histórico de anfitriões sobre-desempenhando é consistente. Caso conhecido sem solução limpa: **México tem torcida majoritária em vários estádios dos EUA** ("quase-casa") — V1 ignora, mas o schema de partida deve prever um campo manual `bonus_mando_override` para o operador setar caso a caso. Altitude (Cidade do México, 2.240 m) e calor: não modelados na V1, listados em riscos.

**Dados.** Calendário com estádio/cidade/país (fixturedownload/openfootball) + flag derivada `anfitriao_em_casa`.

**Vantagens/Limitações.** Custo zero e captura o maior efeito sistemático de localização; mas o valor 60 é incerto e a amostra histórica de anfitriões é pequena (1 a cada 4 anos).

### 3.6 Lesões e desfalques — resumo

Representação matemática completa na **seção 13**. Na V1 a entrada é um JSON manual (sem detector de notícias, que é Camada 3).

### 3.7 Odds gratuitas (benchmark)

**Funcionamento.** Converter odds decimais em probabilidades implícitas e remover a margem (vig):

```
p_i = (1/odd_i) / Σ_j (1/odd_j)        (normalização proporcional; método de Shin fica p/ V2)
```

**Uso recomendado: benchmark, não input.** O mercado é o preditor mais calibrado disponível; comparar Brier do modelo vs. Brier do mercado é o teste de honestidade do projeto. Usar odds como *feature* com peso alto faz o sistema virar um espelho caro do mercado — perde a razão de existir. Compromisso V1: peso ≤ 0.20 no ensemble **somente se** a odd for capturada manualmente pré-jogo; sem odd, renormalizar (seção 9 do doc — pesos).

**Dados/realidade das fontes (verificado em 2026-06):** The Odds API **degradou o free tier** (25 req/dia, só NBA/MLB — não serve). Não há API de odds de Copa gratuita confiável garantida; ver seção 6. Fallback: captura manual (1 min/jogo) de um agregador, digitada num CSV.

**Limitações.** Disponibilidade legal/regional varia; odds de abertura ≠ fechamento (usar a mais próxima do kickoff que conseguir registrar, com timestamp).

### 3.8 Ensemble — resumo

Detalhado nas seções 9–10. Três leituras de probabilidade (Poisson-pipeline, Elo-direto, mercado) combinadas por média ponderada linear em espaço de probabilidade.

### 3.9 Nível de confiança — resumo

Detalhado na seção 14. Confiança é metadado sobre a previsão, não probabilidade.

### 3.10 Validação — resumo

Detalhado na seção 15. Brier + Log Loss + calibração, com registro pré-jogo imutável.

## 4. Cálculos fora da V1 (e por quê)

Correção de **Dixon-Coles** para placares baixos (V1.5 — primeira melhoria após backtest, ~10 linhas de código no futuro); **Poisson bivariado** (ganho marginal sobre Dixon-Coles, custo alto); **xG** (não há fonte gratuita estruturada para seleções — bloqueado por dados, não por matemática); **modelos hierárquicos bayesianos** (Stan/PyMC — melhor incerteza, mas mata a auditabilidade da V1); **ML/gradient boosting** (com ~100 jogos de Copa e features fracas, overfitta na certa); **simulação Monte Carlo do torneio inteiro** (P(título), P(avançar do grupo) — útil e barato, mas é produto derivado: V1.5); **ratings por jogador** (dados manuais proibitivos para 48 seleções); **clima/altitude/viagens/fadiga** (efeito real, estimativa gratuita ruim); **de-vig de Shin**; **ajuste por estado de jogo/incentivos de última rodada** (12 grupos + 8 melhores terceiros criam incentivos estranhos — sem modelo confiável, tratar via score de confiança baixo).

## 5. Dados necessários por cálculo

| Cálculo | Dado | Granularidade | Histórico mínimo |
|---|---|---|---|
| Elo | data, times, placar, competição, flag neutro | por jogo | 1950+ (ideal 1872+) |
| Forma | idem + data p/ decaimento | por jogo | últimos 10 jogos/time |
| Estilo (of/def) | placares + Elo do adversário na data | por jogo | últimos 10–20 jogos/time |
| Mando | estádio, cidade, país-sede | por jogo da Copa | só 2026 |
| Poisson | λ_A, λ_B (derivados) | por jogo | — |
| Desfalques | lista de ausentes + tier por jogador | por jogo | elenco atual |
| Odds | 1X2 decimal + timestamp | por jogo | só 2026 (prospectivo) |
| Validação | resultado final + tudo registrado pré-jogo | por jogo | acumula |

## 6. Fontes gratuitas recomendadas (verificadas em 12/06/2026)

| Fonte | Dado | Grátis? | Key? | Limitações | Confiab. | MVP? | Fallback |
|---|---|---|---|---|---|---|---|
| **martj42/international_results** (GitHub/Kaggle) | resultados internacionais 1872–2026, torneio, flag neutro | Sim | Não | atualização por PR da comunidade (horas–dias de lag na Copa) | Alta | **Sim — fonte nº 1** | openfootball; digitação manual (≤6 jogos/dia) |
| **fixturedownload.com** (fifa-world-cup-2026) | calendário + resultados, CSV/JSON/ICS | Sim | Não | sem estatísticas, só jogos | Alta | **Sim** (calendário) | openfootball/worldcup.json |
| **openfootball/worldcup.json** (GitHub) | calendário/resultados 2026 em JSON, domínio público | Sim | Não | lag de atualização comunitária | Média-alta | Sim (redundância) | fixturedownload |
| **football-data.org** | jogos, resultados, classificação (WC no free tier) | Sim (free tier) | Sim (grátis) | 10 req/min; placar com atraso; **sem escalações no free** | Alta | Sim (automação de resultados) | martj42 + manual |
| **Elo próprio** (calculado do martj42) | rating de força | Sim | Não | depende da qualidade do dataset base | Alta (auditável) | **Sim — recomendado** | snapshot manual do eloratings.net |
| **eloratings.net** | Elo de seleções (benchmark) | Sim | Não | sem API oficial; site é SPA sobre TSV; política de reuso permissiva | Alta | Sim (sanidade) | calcular próprio |
| **Ranking FIFA** (fifa.com / Wikipedia) | ranking oficial | Sim | Não | trimestral, metodologia pior que Elo p/ previsão | Alta (oficial) | Não (só referência) | — |
| **Wikipedia** (2026 FIFA World Cup squads) | convocações, nº camisa, clube | Sim | Não | semiestruturado; exige parsing/cópia manual | Alta durante Copa | Sim (convocações) | site da FIFA (manual) |
| **BALLDONTLIE FIFA API** | jogos, elencos, escalações, odds (2018/22/26) | Free tier existe | Sim | limites do free tier não documentados publicamente — **testar antes de depender** | Média (a validar) | Talvez (bônus) | nenhum — tratar como opcional |
| **The Odds API** | odds | **Não serve mais**: free = 25 req/dia, só NBA/MLB | — | sem futebol no free | — | **Não** | captura manual |
| **FBref / Transfermarkt** | minutos jogados, valor de mercado | Visualização sim | Não | **ToS restringe scraping**; uso manual pontual apenas | Alta | Só consulta manual | tiers manuais |
| **Lesões/desfalques** | — | — | — | **Não existe fonte estruturada gratuita confiável cobrindo 48 seleções. Ponto final.** | — | — | entrada manual (V1); RSS de BBC/ESPN/ge na Camada 3 |

Duas lacunas declaradas explicitamente: (a) **odds gratuitas via API** — nada confiável garantido em 2026; plano real é captura manual; (b) **lesões estruturadas** — inexistente; plano real é JSON manual agora e detector de notícias na Camada 3. Não inventar fonte.

## 7. Dados que precisarão ser manuais no início

Snapshot do eloratings.net para sanidade (1x, pré-torneio); **tiers de importância de jogadores** — só para as ~16 seleções com chance real de ir longe + sob demanda (26 jogadores × 48 seleções manualmente é inviável e desnecessário); **JSON de desfalques** por jogo; **odds 1X2** digitadas pré-jogo com timestamp; override de mando (caso México-em-solo-americano); resultado de pênaltis (o dataset base registra o placar de 90/120 min — conferir convenção do martj42 para mata-mata, que registra o placar ao fim da prorrogação e tem shootouts.csv separado).

## 8. Fórmula inicial do modelo (pipeline completo)

```
ENTRADAS: R_A, R_B (Elo próprio) · forma · estilo · desfalques · flag mando

1) Elo ajustado:      R'_T = R_T + ΔE_forma(T) + ΔE_desfalques(T)
2) Diferença:         dr   = R'_A − R'_B + bônus_mando
3) Expectativa Elo:   W_e  = 1/(1 + 10^(−dr/400))
4) Saldo esperado:    GD   = c · (W_e − 0.5)          c = 3.0  [chute inicial, calibrar]
5) Total esperado:    T_m  = T_base · estilo_A · estilo_B      T_base = 2.6  [calibrar no histórico de Copas]
6) Gols esperados:    λ_A = max(0.2, (T_m + GD)/2)    λ_B = max(0.2, (T_m − GD)/2)
7) Matriz Poisson:    M[i][j] = Pois(i; λ_A) · Pois(j; λ_B),  i,j = 0..8
8) Saídas Poisson:    V/E/D, over 2.5, BTTS, top placares (seções 10–12)
9) Ensemble final:    seção 9–10
```

Sanidade do passo 4–6: dr=300 → W_e=0.85 → GD≈1.05 → λ≈(1.83, 0.78) com T_m=2.6. Favorito claro por ~1 gol: plausível. A constante c sai de regressão `saldo_real ~ (W_e − 0.5)` no histórico — fazer no backtest antes de confiar no 3.0.

## 9. Pesos iniciais do ensemble

| Componente | O que é | Peso c/ odds | Peso s/ odds |
|---|---|---|---|
| P_poisson | V/E/D da matriz do pipeline (passo 8) | 0.45 | 0.56 |
| P_elo | V/E/D direto do Elo: vitória/empate via curva empírica de empate (abaixo) | 0.35 | 0.44 |
| P_mercado | odds de-vigadas (quando capturadas) | 0.20 | 0.00 |

`P_elo` precisa de uma curva de empate, pois W_e não separa empate de vitória: estimar `P(E | dr)` empiricamente do dataset histórico em faixas de |dr| (em seleções, ~26% quando |dr|<50, caindo para ~15% quando |dr|>300 — **extrair as curvas reais do martj42 no backtest**, os números aqui são ordem de grandeza). Então `P(V) = W_e − P(E)/2`, `P(D) = 1 − P(V) − P(E)`.

Combinação: **média linear em espaço de probabilidade** (pool linear), renormalizada. Pool logarítmico (geométrico) é mais "afiado" mas pune discordância — avaliar na V2. Critério de ajuste futuro dos pesos: após ≥30 jogos avaliados, otimizar pesos minimizando Brier em janela móvel (grid search basta para 3 pesos); congelar pesos durante cada fase do torneio para não overfittar em 5 jogos. Os valores 0.45/0.35/0.20 são **[chute inicial]** com uma lógica: Poisson carrega mais informação (usa tudo), Elo-direto é o âncora robusto, mercado pequeno o suficiente para não virar espelho.

## 10. Cálculo da probabilidade final V/E/D

```
P_final(x) = w_p·P_poisson(x) + w_e·P_elo(x) + w_m·P_mercado(x),   x ∈ {V, E, D}
renormalizar: P_final(x) ← P_final(x) / Σ_x P_final(x)
```

Pós-processamento mínimo: clamp de cada probabilidade em [0.02, 0.96] (nunca prometer certeza — requisito do produto) e renormalizar de novo. No mata-mata, publicar também `P(avança) = P(V) + P(E)·(0.5 + 0.03·sinal(dr))` com rótulo claro de que V/E/D é tempo normal.

## 11. Cálculo de gols esperados

É o passo 4–6 da seção 8. Pontos de atenção: (a) `estilo` usa shrinkage para 1.0 — sem isso, uma Argélia com 3 jogos de 4 gols vira time de ataque infinito; (b) desfalques entram **antes** (via ΔE no Elo ajustado) e não direto em λ na V1 — uma única porta de entrada evita dupla contagem; (c) λ mínimo 0.2 evita matriz degenerada; (d) T_base = 2.6 vem da média de gols/jogo das últimas Copas (2018: 2.64; 2022: 2.69; grupos de 2026 com 48 times podem ter mais goleadas — recalibrar após a 1ª rodada com ~16 jogos, mas com cautela: 16 jogos é amostra fraca, mover no máximo ±0.15).

## 12. Cálculo de placares prováveis

Top-k células da matriz M (k=5), com a probabilidade de cada placar exibida. Observações: com λs típicos (1.4 × 1.1), o placar modal costuma ser 1x1/1x0 com ~10–12% — **comunicar que "placar mais provável" ainda é improvável** (~88% de chance de NÃO ser o placar apontado); é requisito de UX da Camada 5/6, mas nasce da matemática daqui. Sem Dixon-Coles, 0x0 e 1x1 estão levemente subestimados na V1 — registrado como viés conhecido.

## 13. Tratamento matemático de lesões/desfalques

Entrada (V1, manual; Camada 3 automatizará a *detecção*, nunca a fórmula):

```json
{"jogo": "BRA-x-MAR-2026-06-15", "desfalques_A": [{"nome": "...", "tier": 1, "setor": "ataque"}], "desfalques_B": []}
```

**Tiers de importância** (proxy de minutos jogados/titularidade nos últimos 12 meses — atribuição manual, consultando FBref/Transfermarkt visualmente):

```
tier 1 — estrela/titular indispensável:  ΔE = −35 Elo   [chute inicial]
tier 2 — titular padrão:                 ΔE = −15
tier 3 — rotação/reserva relevante:      ΔE = −5
ΔE_desfalques(T) = max(−120, Σ ΔE_i)     (cap: elenco de Copa tem 26 jogadores; o time não vira juvenil)
```

Ordem de grandeza defensável: −35 Elo num jogo parelho move W_e em ~5 p.p., compatível com estimativas públicas do efeito de perder um jogador decisivo (ex.: análises do tipo Messi ≈ 50 Elo são topo de escala, raras). **Incerteza alta e declarada** — é o parâmetro mais "no olho" do sistema; calibração real só virá com volume de casos.

Refinamento V1.5 (não agora): split direcional — desfalque ofensivo corta λ_pró (`λ_A × (1−0.06·n_t1_ataque)`), defensivo/goleiro infla λ_contra. Na V1, tudo entra agregado no Elo (uma porta, sem dupla contagem). "Dúvida" (jogador questionável) entra como meio-tier e derruba o componente de robustez da confiança (seção 14).

## 14. Cálculo de nível de confiança

Confiança ≠ probabilidade: é um metascore de quanto o sistema acredita na própria distribuição.

```
separação   = clamp((p_max − 1/3) / (2/3), 0, 1)        → jogo definido pontua alto
concordância = 1 − média das distâncias TV entre P_poisson, P_elo (e P_mercado se houver)
               TV(p,q) = 0.5 · Σ_x |p(x) − q(x)|
dados       = checklist 0–1: ≥8 jogos oficiais na janela de cada time (0.4) ·
              elenco/desfalques confirmados (0.4) · Elo do adversário maduro, não-estreante (0.2)
robustez    = 1 − incerteza de desfalques (dúvidas pendentes derrubam)

score = 100 · (0.40·separação + 0.25·concordância + 0.20·dados + 0.15·robustez)
        × 0.90 se mata-mata  × 0.85 se última rodada de grupo com incentivo cruzado
rótulos: ≥65 alta · 40–64 média · <40 baixa
```

**Jogos equilibrados:** separação ≈ 0 força confiança média/baixa por construção — o sistema deve dizer "jogo aberto, V 34% / E 30% / D 36%" e **não** fabricar um favorito. Pesos do score são [chute inicial]; o fator mata-mata reflete variância de jogo único + prorrogação fora do modelo.

## 15. Validação pós-jogo

**Registro pré-jogo (imutável, append-only — SQLite ou CSV):** `match_id, timestamp_previsao, fase, times, R'_A, R'_B, λ_A, λ_B, P(V/E/D), P(over2.5), P(BTTS), top-5 placares, confiança, desfalques considerados, odds capturadas (se houver), versão_modelo, hash_dos_inputs`. Previsão registrada **antes** do kickoff nunca é editada — sem isso, qualquer métrica é autoengano.

**Métricas (pós-jogo, acumuladas):**

```
Brier (multiclasse, soma) = (1/N) Σ_jogos Σ_x (P(x) − resultado(x))²
   baselines: uniforme (⅓,⅓,⅓) = 0.667 · meta V1: < 0.62 · mercado ≈ 0.55–0.60 (ordem de grandeza)
Log Loss = −(1/N) Σ ln P(resultado)        uniforme = ln 3 ≈ 1.099 — pune overconfiança com força
RPS = (1/2)[(P_V − O_V)² + (P_V+P_E − O_V−O_E)²]   — métrica ordinal, a mais adequada p/ 1X2; reportar as três
```

**Acerto vs. calibração:** "acertou o resultado" (argmax) é métrica fraca e enganosa — chutar o favorito sempre dá ~50% de acerto. O que importa: calibração — dos jogos em que o sistema disse 60%, ~60% aconteceram? Diagrama de confiabilidade em faixas (33–45, 45–60, 60–75, >75). **Aviso de amostra: a Copa tem 104 jogos** — métricas em 104 jogos têm barra de erro grande; faixas de calibração só com ≥20 jogos por faixa. Por isso a validação séria é o **backtest histórico** (Copas 2014/18/22 + Euros + Copas América ≈ 400+ jogos) antes do torneio valer: rodar o pipeline congelado no tempo (só dados anteriores a cada jogo) e exigir Brier < uniforme e ≈ Elo público. Comparação com mercado em jogos passados exigiria odds históricas internacionais, que **não têm fonte gratuita decente** — comparação com mercado será só prospectiva, em 2026, com as odds capturadas manualmente.

## 16. Riscos e limitações

**Amostra pequena em tudo**: 104 jogos para validar, ~10 jogos/ano por seleção para estimar — o sistema inteiro vive de shrinkage e caps; quem prometer precisão aqui está vendendo. **Formato novo de 48 times**: sem histórico comparável; grupos com mais mismatches (caudas do Poisson mal calibradas em goleadas) e a regra dos 8 melhores terceiros cria incentivos de fim de grupo que nenhum modelo de força captura. **Fontes gratuitas morrem ou atrasam**: mitigação obrigatória — snapshot local diário; nenhum cálculo lê a internet na hora. **Eco do mercado**: peso de odds alto demais transforma o projeto em proxy do mercado — manter ≤0.20 e medir-se contra ele, não copiá-lo. **Overfitting dos pesos**: ajustar ensemble com <30 jogos é ler ruído. **Desfalques no olho**: tier manual com −35/−15/−5 é o elo mais fraco da V1, declarado. **Prorrogação/pênaltis** fora do modelo (ε=0.03 é cosmético). **Escalações saem ~1h antes** — fontes gratuitas não garantem isso a tempo; previsão oficial do sistema é a do snapshot da manhã do jogo. **Altitude/calor/viagens** (México 2.240 m, verões americanos) não modelados. **ToS**: FBref/Transfermarkt apenas consulta visual; sem scraping agressivo — é restrição do projeto, não cortesia. **Apostas**: o sistema entrega probabilidades para estudo; Brier ~0.60 não é edge sobre mercado com margem — não é ferramenta de lucro, e isso deve estar escrito na interface.

## 17. Roadmap por camadas

**C1 (agora):** este documento aprovado = contrato matemático congelado (mudanças viram versão_modelo nova). **C2:** ingestão martj42 + fixturedownload → SQLite local; cálculo do Elo histórico próprio; **milestone de saída: backtest 2014/18/22 + Euro/Copa América com Brier < 0.62**. **C3:** desfalques — JSON manual primeiro, depois RSS/notícias alimentando o mesmo JSON (a fórmula da seção 13 não muda). **C4:** ensemble + curva de empate empírica + calibração dos [chutes iniciais] (c, T_base, pesos, tiers). **C5:** insights — cada previsão sai com os fatores: Elo base, ajustes, λs, confiança e porquês. **C6:** interface local lendo o SQLite. Dependências: 4 exige 2; 5 exige 4; 3 é paralelizável.

## 18. Próxima etapa recomendada

Iniciar a **Camada 2 com escopo mínimo e um único critério de aceite: o backtest**. Concretamente: (1) baixar martj42 e congelar snapshot; (2) implementar o Elo da seção 3.1 e validar contra eloratings.net (desvio ±25 nas top 30); (3) extrair do histórico as três constantes que este documento deixou em aberto — c (regressão saldo × W_e), T_base (média de gols em Copas) e a curva P(E | dr); (4) rodar o pipeline congelado nas Copas 2014/18/22 e reportar Brier/LogLoss/RPS vs. uniforme e vs. Elo-direto. Só depois disso vale a pena discutir pesos finos de ensemble ou qualquer camada acima — sem backtest aprovado, o resto é decoração.

---
*Documento de planejamento — não contém código por decisão de escopo. Tudo marcado [chute inicial] deve ser recalibrado na Camada 2/4. Fontes verificadas em 12/06/2026; disponibilidade pode mudar durante o torneio — snapshot local é a defesa.*


