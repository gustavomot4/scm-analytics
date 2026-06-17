---
tags: [camada1, auditoria, historico]
status: historico
tipo: auditoria
data: 2026-06-15
aliases: ["Auditoria 1"]
---

# Camada 1 — Revisão Crítica (Auditoria)
**Projeto:** Sistema de previsão de partidas — Copa do Mundo 2026
**Documento auditado:** [[camada1-planejamento-v1]] (v 2026-06-12)
**Data da revisão:** 2026-06-15 · **Status:** auditoria de planejamento · **Custo-alvo:** R$ 0

> Convenções herdadas do documento original (V/E/D, λ, dr, W_e). Itens marcados **[a calibrar]** são parâmetros, não fatos. Severidade: 🔴 estrutural (corrigir antes do backtest) · 🟡 relevante (corrigir no backtest) · ⚪ menor (anotar).

---

## 1. Resumo da revisão

O documento original é, no geral, **sólido e honesto**: a arquitetura em pipeline (Elo dá a *diferença*, estilo dá o *total*, Poisson gera placares, ensemble combina, mercado é benchmark) é coerente; o tratamento de incerteza é maduro (caps, shrinkage, [chutes iniciais] declarados); a disciplina de "snapshot local, nada lê a internet na hora" e "previsão registrada antes do kickoff, imutável" está correta; e a recusa explícita em inventar fontes (odds e lesões) é exatamente a postura certa. Não há necessidade de reescrever a Camada 1 — ela precisa de **correções pontuais e três adições de dados**.

O que **não** está sólido e precisa mudar antes de o backtest valer:

- 🔴 **O gerador de gols satura.** `GD = c·(W_e − 0.5)` impõe um teto de ±1,5 gol de saldo esperado *qualquer* que seja o mismatch. O sistema fica matematicamente incapaz de prever uma goleada — justo no formato de 48 times, onde o próprio documento prevê mais mismatches. É o erro mais importante.
- 🔴 **Mando histórico indefinido.** O Elo é calculado sobre 1872–2026 (maioria jogos casa/fora), mas a seção de mando só define bônus para os anfitriões de 2026 e "0 no neutro". Sem um termo de mando no *cálculo histórico*, os ratings nascem enviesados. Há uma contradição entre "calcular Elo próprio do histórico completo" e a especificação de mando.
- 🟡 **O ensemble tem menos diversidade do que aparenta.** `P_poisson` e `P_elo` saem ambos do mesmo Elo/W_e; concordam por construção. A métrica de "concordância" da confiança mede consistência interna, não corroboração independente.
- 🟡 **`estilo` joga fora a direção.** O documento calcula fatores ataque/defesa e depois não os usa em λ — usa um fator de *total* multiplicativo. A decomposição ataque×defesa (Maher/Dixon-Coles), já prevista para a V1.5, resolve isto e o item da saturação de uma vez.

Adições de dados que são **gratuitas, locais e que o documento subestimou**: **xG via StatsBomb Open Data** (para backtest e prior de estilo), e **fadiga/viagem/altitude/calor derivados de graça** do próprio calendário + Open-Meteo (sem API key). Detalhe nas seções 3 e 4.

Veredito de tech lead: aprovar a Camada 1 **condicionada** a corrigir os dois 🔴 antes de congelar o contrato matemático. Os dois 🟡 podem ser resolvidos junto com a implementação do backtest (Camada 2).

---

## 2. Erros e inconsistências encontrados

### 2.1 🔴 Saturação do saldo esperado — o modelo não consegue prever goleada

No passo 4 da seção 8: `GD = c·(W_e − 0.5)`, com `c = 3.0`. Como `W_e ∈ (0,1)`, então `(W_e − 0.5) ∈ (−0.5, 0.5)` e portanto **`GD ∈ (−1.5, 1.5)` por construção**, para qualquer dr. Verificando:

| dr | W_e | GD = 3·(W_e−0.5) | λ_favorito (T_m=2.6) |
|---:|---:|---:|---:|
| 300 | 0.849 | 1.05 | 1.83 |
| 500 | 0.947 | 1.34 | 1.97 |
| 700 | 0.983 | 1.45 | 2.02 |
| 1000 | 0.997 | 1.49 | 2.05 |

Um abismo de 700 pontos de Elo produz praticamente o mesmo saldo esperado que 300. O λ do favorito nunca passa de ~2,05, então o sistema **não consegue expressar uma expectativa de 4×0 ou 5×0** — exatamente os jogos que o formato de 48 times vai criar (e que o próprio documento teme nas "caudas do Poisson mal calibradas em goleadas", seção 16). A raiz é parametrizar gols em `(W_e − 0.5)`, que satura porque a logística satura. A nota da seção 8 ("c sai de regressão `saldo ~ (W_e − 0.5)`") **herda a saturação** — a regressão certa é contra `dr`, não contra `W_e`. Correção na seção 5.1.

### 2.2 🔴 Mando de campo ausente no cálculo do Elo histórico

A seção 3.1 atualiza o Elo com `dr = R_A − R_B + bônus_mando` sobre o histórico 1872–2026. A seção 3.5 define `bônus_mando` **somente** como "+60 para anfitrião de 2026" e "0 nos demais jogos (neutro)". Mas a esmagadora maioria dos jogos históricos do dataset martj42 é **casa/fora, não neutra** (o dataset tem coluna `neutral` e a designação home/away justamente para isso). Se o bônus for 0 em todo jogo que não seja de anfitrião-2026, o cálculo trata todo jogo casa/fora como neutro → os mandantes ganham mais do que o modelo espera → os ratings ficam sistematicamente mal calibrados e mais ruidosos.

Isto é uma **inconsistência interna**: "calcular Elo próprio rodando o algoritmo sobre o histórico completo" (3.1) é incompatível com a especificação de mando de 3.5. São **dois parâmetros diferentes** que o documento fundiu num só por omissão:

- `H_hist` — vantagem de mando aplicada a **todo** jogo não-neutro do histórico, na construção do Elo. O eloratings.net usa **+100** e é exatamente isto que estabiliza os ratings ([eloratings.net/about](https://www.eloratings.net/about)). Deve ser fixado em 100 ou, melhor, ajustado (fit) maximizando acurácia preditiva no histórico.
- `H_host2026` — o "+60" da seção 3.5, aplicado **só** a EUA/MEX/CAN jogando em solo próprio na previsão de 2026.

Sem `H_hist`, o benchmark de sanidade "desvio ±25 vs eloratings.net" da seção 3.1/18 vai falhar — porque o eloratings *usa* mando e o nosso cálculo não usaria.

### 2.3 🟡 Diversidade do ensemble superestimada; "concordância" é parcialmente mecânica

A seção 9 combina três leituras: `P_poisson`, `P_elo`, `P_mercado`. Mas `P_poisson` e `P_elo` **não são independentes**: o λ do Poisson vem de `GD`, que vem de `W_e`, que vem do Elo; e `P_elo` é o mesmo `W_e` mais a curva de empate. As duas leituras compartilham o sinal de Elo e só divergem em *como o empate é alocado* e em como o total de gols inclina o V/D. Consequências:

1. O ensemble tem **~2 sinais efetivamente independentes** (família-Elo + mercado), não 3. O peso combinado 0.45+0.35 = 0.80 em duas leituras correlacionadas é, na prática, ~0.80 num único sinal Elo.
2. A `concordância` da confiança (seção 14), medida como distância TV entre `P_poisson` e `P_elo`, mede **consistência interna do tratamento de empate**, não corroboração externa. Ela vai parecer tranquilizadoramente alta mesmo quando o Elo compartilhado estiver errado — dando falsa confiança.

Não é um erro de fórmula, é um erro de *interpretação* que infla a confiança. Correção na seção 5.4 (introduzir uma leitura genuinamente independente e/ou relabelar a concordância).

### 2.4 🟡 `estilo` descarta a direção (ataque vs. defesa)

A seção 3.4 calcula `tendência_gols_T = (gols_pró + gols_contra)/média` — um fator de **total** que soma o que o time faz e o que sofre — e a seção 8 usa `T_m = T_base·estilo_A·estilo_B`. Ironicamente, a mesma seção 3.4 calcula "fatores ataque/defesa (gols pró ajustados, gols contra ajustados)" e os **descarta** ("alimentam a explicação dos insights e o split de V1.5"), não λ. Isso é desperdiçar a informação mais útil: o λ de A deveria depender do **ataque de A contra a defesa de B**, não de um total agregado simétrico. O modelo padrão de futebol (Maher 1982; base do Dixon-Coles que o documento já planeja) faz exatamente isso. Como o Dixon-Coles já está no roadmap (V1.5), **antecipá-lo resolve 2.1 e 2.4 juntos**. Correção na seção 5.2.

### 2.5 🟡 `ΔE_forma` depende da curva de empate e exige Elo ponto-no-tempo

A seção 3.3 usa `PPJ_esperado_por_Elo`. Pontos esperados = `3·P(V) + 1·P(E)`, o que **exige separar P(V) de P(E)** — ou seja, exige a curva de empate `P(E|dr)` que o documento só promete extrair depois (seção 9). Há uma dependência não declarada: a forma não pode ser computada antes da curva de empate. Além disso, no backtest, `PPJ_esperado` precisa usar o **Elo na data de cada jogo** (point-in-time), não o Elo final, sob pena de vazamento (look-ahead). Anotar ambos como pré-requisitos.

### 2.6 ⚪ Itens menores (anotar, não bloqueiam)

- **G descontínuo em N=2 (1,5) vs N=3 ((11+3)/8 = 1,75).** Não é erro — é fiel ao eloratings.net. Só documentar que o salto é intencional.
- **Resíduo da cauda em `M[8][8]`.** Hoje é desprezível (λ≈1,4). **Mas se a saturação 2.1 for corrigida, os λ de favoritos vão crescer** e a cauda passa a importar: estender a matriz para 0..10 e distribuir o resíduo proporcionalmente, recomputando over 2.5 e BTTS da grade maior.
- **BTTS e over assumem independência.** Se Dixon-Coles/bivariado entrar (5.2), recomputar BTTS e P(0×0)/P(1×1) da matriz conjunta — senão fica inconsistente com o V/E/D corrigido.
- **Convenção do Brier.** A seção 15 usa a forma "soma sobre classes" (uniforme = 0,667, máx = 2). Está internamente consistente, mas ao comparar com Brier de mercado publicado, confirmar que o número externo está na mesma convenção (a forma "média sobre classes" dá uniforme = 0,222 — fator 3 de diferença). Fixar a convenção no registro.
- **Clamp [0.02, 0.96] + renormalizar.** Correto, mas a renormalização pós-clamp pode reempurrar um valor para fora de [0.02,0.96]; iterar 1–2x ou aceitar o drift mínimo e documentar.

---

## 3. Dados e variáveis adicionais propostos

Critério: só entram variáveis **gratuitas, locais e deriváveis** — e cada uma entra primeiro como *diagnóstico*, virando termo do modelo só se passar no backtest (seção 7). Prioridade decrescente:

### 3.1 xG (expected goals) — **a maior lacuna recuperável**
O documento afirma "não existe fonte gratuita estruturada de xG para seleções". Isso é **parcialmente incorreto**: o **StatsBomb Open Data** publica dados de eventos com xG, de graça e sem API key, para vários torneios de seleções (incluindo Copa do Mundo masculina 2018, Eurocopa, Copa do Mundo Feminina 2019/2023). Não cobre as 48 seleções nem é ao vivo, mas é ouro para: (a) **backtest enriquecido** (medir resultado "merecido" por xG, não só placar); (b) um **prior de estilo** melhor que gols brutos (xG é menos ruidoso que gols em amostra pequena); (c) **validar** o gerador de λ contra xG real. Licença é não-comercial — compatível com uso pessoal/estudo, não com redistribuição.

### 3.2 Fadiga / descanso / viagem — **grátis, derivável do calendário**
O documento descarta fadiga como "estimativa gratuita ruim", mas a *matéria-prima* é grátis e já está em mãos:

- **Dias de descanso** e **descanso diferencial** (um time jogou há 3 dias, o outro há 5): derivável direto da lista de jogos (fixturedownload, já usada). Efeito de descanso assimétrico é dos mais documentados e é de graça.
- **Distância de viagem** entre cidades de jogos consecutivos: as 16 sedes têm coordenadas públicas; haversine entre elas é trivial. Coordenadas via **Open-Meteo Geocoding** (sem key) ou hardcoded (16 constantes).

Entra como pequeno ajuste e/ou penalidade de confiança, não como grande fator.

### 3.3 Altitude — **grátis, estática**
Cidade do México a ~2.240 m afeta seleções não-aclimatadas (efeito documentado em eliminatórias CONMEBOL). A elevação de cada estádio é pública (Open-Meteo **Elevation API**, sem key, ou Wikidata). Na V1, no mínimo um **redutor de confiança** para visitante não-aclimatado jogando na Cidade do México; eventualmente um pequeno ajuste em λ.

### 3.4 Calor / temperatura no kickoff — **grátis, sem key**
Junho-julho em sedes dos EUA/México pode ter calor extremo, que reduz ritmo e total de gols (documentado). **Open-Meteo** dá temperatura/umidade histórica (desde 1940) e previsão de 16 dias, **sem API key e sem rate limit para uso não-comercial** ([open-meteo.com](https://open-meteo.com/)). Efeito é pequeno e fácil de overfittar — candidato, não certeza.

### 3.5 Idade média / experiência do elenco — **barato, fonte já usada**
Idade média e número de convocações ("caps") são extraíveis das páginas de elenco da Wikipedia (já listada como fonte). Proxy de experiência/volatilidade: elencos muito jovens tendem a maior variância. Custo baixo (parsing do que já se coleta).

### 3.6 O que **não** vale a pena perseguir (honestidade)
- **Posse de bola, distância percorrida:** sem fonte gratuita estruturada para seleções; posse é fraco preditor (descreve estilo, não resultado). Baixa prioridade.
- **Odds históricas internacionais:** continuam sem fonte gratuita decente (football-data.co.uk só cobre clubes). A comparação com mercado segue **prospectiva** (captura manual em 2026), como o documento já diz. Não inventar.

---

## 4. Fontes de dados adicionais (tabela)

Mesmos critérios da seção 6 do documento original. Verificadas em 2026-06-15; disponibilidade pode mudar — **snapshot local é a defesa** (princípio já adotado).

| Fonte | Dado | Grátis? | Key? | Limitações | Confiab. | Papel | Fallback |
|---|---|---|---|---|---|---|---|
| **StatsBomb Open Data** (GitHub `statsbomb/open-data`) | eventos + **xG**, escalações, freeze-frames; WC 2018, Euro, WWC 2019/2023 etc. | Sim | Não | Só torneios selecionados; não cobre as 48 seleções; **não é ao vivo**; licença **não-comercial** | Alta (curada) | Backtest com xG + prior de estilo | FBref (visual, manual) |
| **Open-Meteo** (`open-meteo.com`) | temperatura/umidade no kickoff (histórico desde 1940 + previsão 16 dias) | Sim | **Não** | Uso não-comercial; efeito do clima é pequeno/incerto | Alta | Feature de calor + confiança | Ignorar (clima é opcional) |
| **Open-Meteo Elevation API** | altitude do estádio (lat/lon → metros) | Sim | **Não** | — | Alta | Flag de altitude (Cidade do México) | Wikidata; hardcode 16 sedes |
| **Open-Meteo Geocoding API** | coordenadas das cidades-sede | Sim | **Não** | — | Alta | Distância de viagem (haversine) | Hardcode 16 coordenadas |
| **Wikidata** (SPARQL) | coordenadas/elevação/capacidade de estádios; metadados | Sim | Não | Semiestruturado; SPARQL tem curva | Média-alta | Redundância p/ altitude/geo | Open-Meteo; hardcode |
| **Calendário (fixturedownload, já usada)** | dias de descanso, congestão, sequência de cidades | Sim | Não | Nenhuma nova (derivação, não nova fonte) | Alta | Fadiga/descanso diferencial | openfootball |
| **Wikipedia — elencos 2026 (já usada)** | idade, nº de caps, clube por jogador | Sim | Não | Parsing manual/semiestruturado | Alta na Copa | Idade média / experiência | site da FIFA (manual) |
| **international-football.net** | Elo alternativo de seleções | Sim | Não | Sem API; metodologia difere do eloratings | Média | 2º benchmark de sanidade do Elo próprio | eloratings.net |

Lacunas **mantidas e reconfirmadas** (não inventar fonte): odds gratuitas via API (segue captura manual) e lesões estruturadas para 48 seleções (segue JSON manual + RSS na Camada 3).

---

## 5. Modelos revisados (fórmulas / pseudocódigo)

### 5.1 Correção mínima da saturação de gols (resolve 2.1)
Parar de parametrizar saldo em `W_e`. Regredir o saldo observado contra `dr` diretamente:

```
# Ajuste (backtest, point-in-time): saldo_real_i ~ dr_i
GD_esperado = θ · (dr / 100)          # θ [a calibrar], chute inicial ~0.45 gol por 100 Elo
# Sanidade com θ=0.45: dr=300 → GD=1.35 ; dr=600 → GD=2.70 ; dr=900 → GD=4.05
# (agora goleadas são EXPRIMÍVEIS, ao contrário do teto de 1.5 atual)
```

Mantém `W_e` apenas onde ele é bom: na leitura V/E/D do Elo-direto (com a curva de empate). O total `T_m` deve passar a depender também do mismatch (goleadas têm mais gols), não só de estilo:

```
T_m = (T_base + κ·|dr|/100) · estilo_A · estilo_B     # κ [a calibrar], pequeno
λ_A = max(0.2, (T_m + GD_esperado)/2)
λ_B = max(0.2, (T_m − GD_esperado)/2)
```

### 5.2 Correção estrutural recomendada: antecipar o ataque/defesa (resolve 2.1 + 2.4)
Em vez do total simétrico, gerar λ direto por **regressão Poisson com ataque/defesa** (base do Dixon-Coles, já no roadmap V1.5 — antecipar):

```
ln λ_A = μ + ATA_A + DEF_B + γ·mando_A
ln λ_B = μ + ATA_B + DEF_A
# ATA_T, DEF_T: parâmetros por time, estimados por máxima verossimilhança
#   sobre gols históricos, REGULARIZADOS (shrink → 0) p/ amostra pequena de seleções.
# Opção Elo-âncora (preserva a espinha dorsal do projeto):
#   usar (ATA_T − DEF_T) com PRIOR ∝ Elo_T, mantendo Elo como regularizador.
```

Vantagens sobre o atual: dá direção (ataque de A × defesa de B), total e diferença de forma coerente; **permite goleada naturalmente**; é o padrão da literatura; e continua **auditável** (os parâmetros ATA/DEF por time são inspecionáveis). Sobre esta base, Dixon-Coles é só o termo de correção `τ(λ_A,λ_B,ρ)` para placares baixos. Recomendação de tech lead: **a V1 deveria nascer com 5.1; a 5.2 deveria subir de V1.5 para "logo após o primeiro backtest"**, porque conserta o erro 🔴 mais grave.

### 5.3 Mando histórico (resolve 2.2)
Separar explicitamente os dois parâmetros no contrato:

```
# CONSTRUÇÃO DO ELO (sobre todo o histórico martj42):
dr_update = R_A − R_B + (H_hist se NOT neutral else 0)     # H_hist = 100 (eloratings) ou fit
# PREVISÃO 2026:
bonus_mando = H_host2026 (=60 [a calibrar]) se anfitrião jogando em solo próprio, senão 0
# Validar: SÓ com H_hist o benchmark "±25 vs eloratings.net top-30" pode fechar.
```

### 5.4 Diversidade real do ensemble e confiança honesta (resolve 2.3)
Duas opções (não exclusivas):

```
# (a) Adicionar uma leitura GENUINAMENTE independente:
#     P_ad = V/E/D derivado do modelo ataque/defesa de 5.2 (NÃO ancorado em W_e).
#     Ensemble passa a ter 3 sinais de fato independentes: {Elo-direto, ataque/defesa, mercado}.
# (b) Relabelar a métrica de confiança:
#     'concordancia' entre P_poisson e P_elo  →  rotular como 'consistência interna' (peso menor).
#     Criar termo separado 'gap_mercado' = 1 − TV(P_modelo, P_mercado)  → corroboração externa real.
```

### 5.5 Validação com incerteza (anti-autoengano)
Adicionar quantificação de incerteza às métricas — com 104 jogos (e mesmo ~400 no backtest), estimativas pontuais enganam:

```
# Bootstrap (reamostrar jogos com reposição, B=10000):
IC95(Brier), IC95(RPS), IC95(LogLoss)
# Teste pareado modelo vs mercado (por jogo): diff_i = Brier_modelo_i − Brier_mercado_i
#   reportar média de diff com IC bootstrap (ou Wilcoxon). Bater o mercado exige IC que NÃO cruze 0.
```

---

## 6. Novos insights habilitados

Com os dados atuais + as adições da seção 3, o sistema pode entregar (sem custo e sem sair do local):

1. **Simulação Monte Carlo do torneio** — `P(avançar do grupo)`, `P(chegar à semi/final)`, `P(título)`, chaveamento mais provável. O documento a classifica como "produto derivado V1.5", mas é **quase de graça** assim que o modelo de jogo existe (simular a chave milhares de vezes) e é o insight de maior valor percebido. Recomendo promover.
2. **Sensibilidade por previsão como saída padrão** — a execução manual CAN×BIH **já fez isto** (base 60% · Elo−40 → 57% · mando 0 → 55% · sem Davies → 62%). Formalizar como saída de toda previsão serve diretamente ao requisito "probabilidades, não certezas" e à auditabilidade. Está demonstrado; falta padronizar.
3. **Resultado "merecido" por xG (StatsBomb, no backtest)** — detectar seleções vencendo por sub/sobre-desempenho de xG → sinal de regressão à média ("o time X vem ganhando acima do xG, tende a cair"). Insight genuinamente novo, impossível só com placares.
4. **Flags de contexto físico** — "Seleção Y joga na altitude da Cidade do México com 3 dias de descanso contra 5 do adversário": narrativa de fadiga/altitude derivada de graça do calendário + Open-Meteo.
5. **Clash de estilos** — com ataque/defesa (5.2): "dois times de bloco baixo → total esperado baixo, over 2.5 improvável", explicado pelos parâmetros, não por palpite.
6. **Honestidade calibrada na própria saída** — "o placar mais provável (1×0, 12%) ainda tem ~88% de chance de NÃO acontecer": o documento já pede isto na UX; com a matriz corrigida vira número confiável.

---

## 7. Riscos e limitações

**Remanescentes do documento original (continuam válidos):** amostra pequena em tudo (104 jogos para validar, ~10/ano por seleção); formato de 48 times sem histórico comparável e com incentivos de fim de grupo que nenhum modelo de força captura; fontes gratuitas que atrasam/morrem (mitigado por snapshot local); eco do mercado se o peso de odds subir; desfalques "no olho" (−35/−15/−5) como elo mais fraco; prorrogação/pênaltis fora do modelo; escalações que só saem ~1h antes.

**Novos riscos introduzidos pelas melhorias propostas:**

- **Overfitting é o risco central e ele cresce.** Cada variável nova (xG, descanso, viagem, altitude, calor, idade) multiplica os graus de liberdade contra amostras minúsculas. Disciplina obrigatória: **toda variável entra como diagnóstico e só vira termo do modelo se melhorar Brier/RPS com IC que não cruze zero** (seção 5.5). Sem esse portão, as adições pioram o sistema.
- **Antecipar o ataque/defesa (5.2) aumenta a complexidade** e exige dados suficientes por seleção; sem shrinkage forte, seleções com poucos jogos contra elite ganham parâmetros ATA/DEF instáveis. A regularização Elo-âncora é o que segura isso — não é opcional.
- **Licença e cobertura do StatsBomb:** não-comercial (ok para estudo pessoal, não para redistribuir/comercializar dados derivados) e cobre só alguns torneios — é **ativo de backtest/enriquecimento, não feed ao vivo das 48 seleções**. Não construir dependência operacional sobre ele.
- **Efeitos de clima/altitude/viagem são pequenos e incertos.** Risco real de adicionar ruído. Mantê-los como **modificadores de confiança antes de virarem termos de λ**.
- **Staleness das fontes:** verifiquei disponibilidade em 2026-06-15, mas ToS e free tiers mudam. A disciplina de snapshot local (já no documento) deve cobrir explicitamente StatsBomb e Open-Meteo.
- **Mesmo corrigido, não é ferramenta de lucro.** Brier ~0,58–0,60 não é edge sobre mercado com margem. Manter o aviso na interface — corrigir a saturação melhora placares, não transforma o sistema em vantagem de aposta.

**O que continua genuinamente incerto (declarado):** o tamanho real do efeito de mando na Copa (`H_host2026`), os tiers de desfalque, o impacto de altitude/calor, e qualquer coisa sobre o México como "quase-casa" em solo americano. Nenhuma das melhorias propostas resolve isto — apenas as torna explícitas e calibráveis.

---

## 8. Próximos passos recomendados

Ordem importa: **consertar a base do Elo antes de qualquer outra coisa**, porque tudo a jusante depende dela.

1. **Rebuild do Elo com mando histórico (corrige 2.2).** Definir `H_hist` (100 ou fit), aplicar a todo jogo não-neutro do martj42, recomputar a série, e **só então** validar contra eloratings.net (±25 nas top-30). Sem isto, o benchmark de sanidade não fecha. *Desbloqueia todo o resto.*
2. **Trocar o gerador de gols (corrige 2.1, idealmente 2.4 junto).** Implementar 5.1 (regredir saldo em `dr`) como piso; e avaliar 5.2 (ataque/defesa Poisson, base Dixon-Coles) como o gerador de λ. Decidir entre os dois por Brier/RPS **com IC** (5.5).
3. **Extrair as constantes em aberto point-in-time:** `θ` (saldo×dr) no lugar de `c`; `T_base` e `κ`; e a curva `P(E|dr)` em faixas de |dr|. Tudo só com dados anteriores a cada jogo (anti-look-ahead, ver 2.5).
4. **Ingerir StatsBomb Open Data** (WC 2018, Euro, WWC 2023) para backtest com xG e para testar o prior de estilo baseado em xG vs. gols brutos.
5. **Adicionar features de contexto físico como diagnóstico** (dias de descanso, km de viagem via Open-Meteo geo, flag de altitude, temp no kickoff). Promover a termo do modelo **só** com evidência de backtest (portão da seção 7).
6. **Reforçar a validação** com bootstrap IC + teste pareado vs mercado (5.5) antes de declarar qualquer vitória.
7. **Construir o Monte Carlo do torneio** e padronizar a **saída de sensibilidade por previsão** (já demonstrada no CAN×BIH) — os dois insights de maior valor.
8. **Só então** ajustar pesos finos do ensemble (≥30 jogos) e introduzir a leitura independente ataque/defesa para restaurar a diversidade real do ensemble (2.3).

**Milestone de aceite (atualiza o do documento):** backtest 2014/18/22 + Euro/Copa América rodando o pipeline **congelado e point-in-time**, com Elo já corrigido por mando histórico, exigindo **Brier < uniforme com IC que não cruze o baseline** e desempenho ≈ Elo público. Sem isso, o resto é decoração — princípio do documento original, que esta revisão mantém.

---
*Auditoria de planejamento — sem código de implementação, por escopo. Correções 🔴 (saturação de gols, mando histórico) devem entrar antes de congelar o contrato matemático da Camada 1; 🟡 podem acompanhar a Camada 2. Fontes verificadas em 2026-06-15; snapshot local é a defesa contra mudança de disponibilidade.*
