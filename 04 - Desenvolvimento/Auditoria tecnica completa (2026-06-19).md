---
tags: [dev, audit, auditoria, externa, completa]
status: atual
tipo: auditoria
data: 2026-06-19
aliases: ["Auditoria técnica completa", "Audit 2026-06-19"]
---

# Auditoria técnica completa — SCM Analytics (2026-06-19)

Auditoria independente do repositório **`github.com/gustavomot4/scm-analytics`**, na função de **arquiteto de software e auditor técnico**. Não implemento funcionalidades: leio, reproduzo e critico. Toda conclusão cita o arquivo/módulo em que se baseia. Onde uma informação não foi encontrada, declaro explicitamente. Sigo o princípio do próprio projeto: **probabilidades, nunca certezas — e nada é elogiado sem justificativa técnica.**

> **Método.** Li o repositório a partir do GitHub (branch `main`): o `README.md` raiz, todo o pacote **`scm_analytics/scm/`** (20 módulos `.py`), `requirements.txt`, testes (`tests/`, 18 arquivos), e a documentação do vault — `00 - Projeto/` (`CLAUDE.md`, `MODELO_FINAL.md`, `TECH_STACK` referenciado), `03 - Dados/` (`Fontes gratuitas`, `Esquema SQLite`), `04 - Desenvolvimento/` (`Backtest baseline (resultados)`, `Decisoes tecnicas`, **`Auditoria tecnica externa (2026-06-18)`**, `Codigo (estrutura)` referenciado) e `01 - Planejamento/camada1-apendice-formas-v5`. **Reproduzi numericamente** as fórmulas centrais (`predictor`, `elo_engine`) num script isolado e marquei esses resultados como **[verificado]**. Não consegui executar o pipeline completo de ponta a ponta porque **o repositório não versiona a pasta `dados/`** (ver Problema N5) — onde foi preciso, confirmei o comportamento diretamente sobre o código local em `scm_analytics/scm/`.

> **Relação com a auditoria anterior.** O projeto **já passou por uma auditoria interna** ([[Auditoria tecnica externa (2026-06-18)]], 18 achados) cujas correções de alto impacto foram aplicadas na versão **`baseline-v0.3-altitude`**. **Confirmei, no código atual, que essas correções estão de fato presentes** (curva de empate empírica, comparador Elo público, σ informativo na porta da frente, cobertura de Guadalajara, cobertura de banda por faixa, mata-mata, simulador). Esta auditoria **(a) valida o que foi corrigido, (b) mostra o que continua aberto e (c) adiciona achados novos** que a rodada anterior não destacou.

---

## 0. Veredito em uma página

O SCM Analytics é um projeto de **engenharia e disciplina de processo acima da média para o seu porte**: documentação rastreável (nota → fórmula → módulo), decisões registradas como ADRs ([[Decisoes tecnicas]]), contrato matemático congelado (v5.0) e — o ponto mais raro — um **portão estatístico** (IC bootstrap pareado de ΔBrier que não pode cruzar zero, `backtest_harness.gate`) que **efetivamente rejeita** fatores sem evidência por jogo (calor e estilo foram construídos e barrados). Isso é honestidade metodológica incomum.

O motor, na versão atual (`baseline-v0.3-altitude`), faz o básico bem: pipeline point-in-time honesto, coerência `P∈[0,1]` por construção, e — após a v0.3 — **bate o Elo público com IC que não cruza zero** ([[Backtest baseline (resultados)]]: torneios +0,0037, IC [+0,0009, +0,0066]). É a diferença entre "tem algum sinal" e "supera o piso trivial". Mérito real.

Mas três limitações estruturais persistem e definem o teto atual:

1. **O modelo colapsa toda a força de uma seleção num único escalar `dr`**, do qual derivam *ambas* as taxas de gol (`λ_A`, `λ_B`) e a leitura "Elo-direto". O ensemble combina **duas leituras da mesma fonte** (Poisson e Elo, ambas crescem com `dr` — [verificado]); a perna independente (mercado) é zero no histórico. A "combinação de modelos" é, na prática, redundante.
2. **A incerteza ainda é pouco informativa onde importa.** A v0.3 fez `σ_dr` variar por confronto (bom), mas a base `σ_R` continua sendo essencialmente função do nº de jogos (satura em ~40 para qualquer seleção estabelecida — [verificado]), e **a confiança ainda usa o `σ_R` bruto** (`predict_match.py:141`), então a "maturidade" do rating é ~0,8 fixa para todo confronto de elite (Problema N3).
3. **Há divergências entre o que é validado e o que é entregue.** A mais séria: **a "porta da frente" (`predict_match`) não aplica a forma recente** que o backtest valida (Problema N1). E **a maior alavanca do modelo (altitude) não entra na simulação do torneio** (Problema N2), justamente onde o México joga em casa em sede alta.

**Nível técnico.** Engenharia/processo: **alto**. Modelagem estatística efetivamente entregue: **médio** — baseline correto e honesto, mas com aparato (incerteza, ensemble) parcialmente inerte e um sinal de skill **pequeno** sobre o Elo (+0,003 de Brier; o próprio projeto admite "Brier ~0,60 não é vantagem", [[CLAUDE]]).

**Preparo para a Copa 2026.** Como **ferramenta de estudo** que produz probabilidades 1X2 razoáveis e calibradas: **utilizável, com ressalvas**. Como **sistema de previsão sério da Copa**: **ainda não pronto** — faltam consistência entre backtest e produção (N1, N2, N3), diversidade real de modelo (Dixon-Coles / prior não-Elo), dados de jogo (desfalques/escalações) e um laço de validação prospectiva fechado. A **arquitetura suporta** essa evolução; os **modelos atuais não a sustentam** sem os itens das Fases 0–1 do roadmap (§10).

---

## 1. Visão geral do projeto

**Objetivo.** Sistema **local e gratuito (R$ 0)** que prevê partidas de seleções, com foco na **Copa do Mundo 2026**, entregando **P(vitória/empate/derrota), gols esperados (λ), mercados derivados, banda de incerteza e um score de confiança** — declaradamente **probabilidades, não certezas**, e **não** ferramenta de aposta (fontes: `README.md`, `00 - Projeto/CLAUDE.md`, `00 - Projeto/MODELO_FINAL.md`). Restrições inegociáveis ([[CLAUDE]] "Restrições não negociáveis"): custo zero, roda offline (nada lê a internet no cálculo — usa *snapshot* em disco), registro pré-jogo imutável, não inventar dados.

**Como funciona (fluxo principal).** Pipeline linear, com os estágios se comunicando por tabelas SQLite (contrato de I/O por tabela):

```
ingest → elo_engine → features_pit → predictor → backtest_harness → report
 martj42   Elo + σ_R     forma + σ_dr   λ → Poisson + Elo-direto      Brier/RPS    reliability
 (CSV)     (pré-jogo)     (point-in-time)  → ensemble → V/E/D+banda    + IC + portão  + ECE
```

1. **`ingest.py`** carrega o CSV do martj42 (resultados 1872–2026) para `matches`/`teams`, idempotente por `natural_key`.
2. **`elo_engine.py`** reconstrói o Elo cronologicamente e grava o **rating pré-jogo** de cada partida em `match_ratings` (base do anti look-ahead).
3. **`features_pit.py`** monta features usando só jogos anteriores à data (forma recente ajustada a adversário, `dr_adj`, `σ_dr`).
4. **`predictor.py`** converte `dr` em saldo `GD = θ·dr/100` e total `T_m = (T_base+κ·|dr|/100)`, gera a **matriz Poisson** (V/E/D, over, BTTS, placares) e a **leitura "Elo-direto" propagada** (estratos determinísticos + banda 16/84), e as combina num **ensemble** (0,56 Poisson / 0,44 Elo, sem mercado no histórico).
5. **`backtest_harness.py`** mede Brier/LogLoss/RPS com IC bootstrap, compara contra **uniforme** e contra **Elo público** (`evaluate_vs_elo`), e implementa o **portão**.
6. **`report.py`** produz reliability/ECE e cobertura de banda (agregada e por faixa).

A "porta da frente" para um confronto é **`predict_match.py`** (usa o Elo atual de `ratings_current`); **`web.py`** é uma interface Flask local; **`simulate.py`** roda o Monte Carlo do torneio inteiro. Os módulos de fator C2.5 (`altitude`, `heat`, `estilo`, `calibrate*`) avaliam candidatos atrás do portão.

**Módulos e como se relacionam.** Há boa separação entre **núcleo puro** (funções `lambdas`/`poisson_reads`/`elo_direct_read`/`predict`/`markets` em `predictor.py`, sem I/O) e **persistência** (os `run()` de cada estágio). `altitude`/`heat`/`estilo` reusam `predict` + `gate`. `predict_match`/`web`/`simulate` reusam `predict`/`lambdas`. O acoplamento entre estágios é via SQLite, o que os mantém desacoplados (detalhe em §2).

---

## 2. Arquitetura

**Organização de pastas.** Dupla natureza bem resolvida: um **vault Obsidian** (planejamento `01`, modelos `02`, dados `03`, desenvolvimento `04`, referências `05`, análises `06`) e o **pacote Python** (`scm_analytics/scm`). A separação documentação ↔ código é limpa e a rastreabilidade é excelente (cada módulo cita a nota do contrato no docstring; ex.: `elo_engine.py` aponta `02 - Modelos/Elo.md` e `camada1-planejamento-v5 §3.1`). **Ponto forte real**, com justificativa: reduz o custo de manutenção e o risco de o código divergir do contrato sem rastro.

**Separação de responsabilidades / coesão.** Alta. Cada módulo tem responsabilidade única e contrato de I/O por tabela (`03 - Dados/Esquema SQLite.md`). O núcleo matemático é testável sem banco (`tests/test_predictor.py` exercita `predict` direto). `db.py` centraliza schema e conexão.

**Acoplamento.** Baixo no geral, com **três pontos a observar**:

- *Ciclo de import contornado em runtime.* `predictor.run()` importa `altitude.gd_alt` **dentro da função** (comentário "import tardio (evita ciclo predictor<->altitude)"). O ciclo existe porque `altitude.py` importa de `predictor` **e** de `backtest_harness`, que por sua vez importa de `predictor`. Funciona, mas sinaliza que a lógica de **predição** (produção) e a de **portão** (avaliação) estão entrelaçadas. O ideal seria um módulo `factors.py` (termos de λ) consumido pelo `predictor`, com os gates só no harness.
- *Schema implementado é subconjunto do desenhado.* O design (`03 - Dados/Esquema SQLite.md`, `camada2-planejamento-v1 §2.3`) prevê `venues`, `context`, `statsbomb`, `odds_hist`; `db.py` cria só `teams/matches/match_ratings/match_features/predictions/meta`. Logo **xG/odds/contexto não têm onde entrar** sem evoluir o schema — limitação estrutural para a evolução pretendida (Problema P-H).
- *Coeficientes espalhados.* Não há uma camada única de configuração: os parâmetros vivem em dataclasses por módulo (`PredictParams`, `EloParams`, `FeatureParams`) **mais** constantes soltas (`THETA_ALT`, `SIGMA_R_REF`, `WBGT_THRESHOLD`, `DRAW_CURVE`…). Aceitável hoje; atrito quando a calibração precisar varrer tudo de forma coerente.

**Escalabilidade.** O ponto sensível é `features_pit.team_form`: para cada jogo roda duas subconsultas correlacionadas (forma do mandante e do visitante) com filtro por time **e** `date < t`. A v0.3 já adicionou os índices compostos `(home_team_id, date)` e `(away_team_id, date)` em `db.SCHEMA` (D-29), o que mitiga muito o custo. Para a Copa (poucos jogos novos por rodada) o custo é irrelevante; para re-backtests completos sobre os 49.423 jogos, o passo é o gargalo. A propagação por 200 estratos foi acelerada ~8× cacheando os quantis da Normal (D-30) — boa otimização, mesma matemática.

**Manutenibilidade.** Alta: módulos pequenos (60–250 linhas), docstrings densos, nomes claros, testes por módulo. Custos: ausência de `conftest.py` (cada teste reconstrói fixtures e abre seu próprio `:memory:`), conexões SQLite sem *context manager*, `print()` em vez de `logging` (Problema P-I).

**Melhorias arquiteturais sugeridas (com justificativa).** (1) extrair os termos de λ para `factors.py` — quebra o ciclo de import e separa produção de avaliação; (2) evoluir `db.SCHEMA` para o schema-alvo (`venues`/`context`/`odds`) — destrava xG/odds/desfalques; (3) `conftest.py` com fixtures compartilhadas — reduz duplicação e risco de divergência; (4) uma camada fina de config para coeficientes — viabiliza calibração coerente e versionada.

---

## 3. Modelos matemáticos

Avaliação por bloco. As **fórmulas estão aritmeticamente corretas** (reproduzi as contas — ver tabela [verificado] ao fim), mas há problemas de **modelagem** e, sobretudo, de **degenerescência prática** (aparato que existe mas varia pouco) e de **consistência entre o que é validado e o que é entregue**.

### 3.1 Elo (`elo_engine.py`) — sólido; `σ_R` ainda é estrutural-de-`n`
`we(dr)=1/(1+10^(−dr/400))`, `dr=R_A−R_B+mando`, `K` por competição (`k_factor`), `G` por margem de gols (`g_factor`, anti-saturação). Conforme `02 - Modelos/Elo.md`/contrato §3.1 e **[verificado]** (`we(100)≈0,640`). Zero-sum (o que um ganha o outro perde). Observações:

- **`σ_R` é função quase só de `n`.** `sigma_r(n)=floor + (prov−floor)·e^(−n/τ)` (`floor=40, prov=200, τ=20`). **[verificado]**: `σ_R(80)=42,9`, `σ_R(150)=40,1`, `σ_R(400)=40,0`. Como as 48 seleções da Copa são estabelecidas, **todas chegam a `σ_R≈40`**. A v0.3 introduziu `vol_mult` (`features_pit`) para escalar pela (in)consistência recente — bom —, mas é um multiplicador clampado em [0,6; 1,6] sobre uma base que satura: a degenerescência foi **atenuada, não eliminada** (Problema P-B). A recomendação de fundo (σ a partir do **erro do ajuste** de Elo, ou um esquema **Glicko/TrueSkill** cujo RD varia com regularidade e recência) segue não adotada.
- **`k_factor` por palavra-chave** está com a ordem certa ("qualif" antes de "world cup", evitando que eliminatória vire K=60), mas atribui **K=50 a *toda* partida continental** (Euro, Copa América, etc.), enquanto o próprio comentário do código diz "finais continentais 50". Jogos de fase de grupos de um continental recebem K=50 indevidamente (Problema N6, baixo).

### 3.2 Poisson (`predictor.poisson_reads` / `markets`) — correto, mas **independente**
`M[i][j]=Pois(i;λ_A)·Pois(j;λ_B)`, 0..10; V/E/D/over/BTTS/top-5 da matriz. **[verificado]** reproduz a execução manual IRN×NZL (λ=1,40/0,78 → P(V)=0,517, P(E)=0,275, P(D)=0,209, over2.5=0,372, BTTS=0,408; soma=1,000000). Duas ressalvas:

- **Independência de gols.** Assume gols dos dois times independentes; ignora a correlação negativa real (excesso de 0×0/1×1). Isso **enviesa BTTS/under** — exatamente o que a **Dixon-Coles** corrige (reconhecido, no backlog). O `calibrate_total.py` mede e tenta corrigir só o *nível* (T_base), não a *correlação*: o viés medido de BTTS (~+3,8 pp) e over (~+7 pp) em torneios recentes **continua sem correção estrutural** (Problema P-A).
- **Truncamento em 10 sem redistribuir massa.** `poisson_reads` soma a matriz até 10 e renormaliza adiante; a massa truncada é ~9e-6 (numericamente irrelevante, mas é doc≠código se a nota fala em "resíduo na borda").

### 3.3 Curva de empate C1 (`predictor.draw_prob`) — **corrigida na v0.3** ✅
O contrato (`camada1-apendice-formas-v5 §3`) exige `P_E(dr)` como **tabela empírica do martj42 por faixa de |dr|**, e a revisão v5 proibiu o *proxy* fechado. **Confirmei no código** que a v0.3 implementou a tabela empírica congelada `predictor.DRAW_CURVE` (`use_empirical_draw=True` por padrão; `build_draw_curve()` para reconstrução). **[verificado]**: `draw_prob(0)=0,2847`, `draw_prob(100)=0,2629`, `draw_prob(300)=0,1942` — diferente do proxy antigo (0,27 / 0,2219 / 0,1499). Achado #3 da auditoria anterior: **resolvido**. Ressalva menor: a tabela foi construída do `dr` de `match_ratings` (que embute +100 de mando em jogos não-neutros) e é aplicada via `|dr|` a `dr_adj` (neutro nas Copas); a *localização* da distribuição de `dr` em treino e aplicação difere um pouco — efeito de 2ª ordem.

### 3.4 Saldo/Total `f(dr)`, `g(dr)` e o piso de λ (`predictor.lambdas`) — forma linear inválida no tail
`GD=θ·dr/100` (θ=0,45), `T_m=(T_base+κ·|dr|/100)·estilo·heat` (T_base=2,6, κ=0,10). Formas lineares (placeholders do apêndice, confirmadas como quase ótimas em D-17). **Problema (Média-Baixa, P-D):** a forma linear faz `λ_B=(T_m−GD)/2` **ficar negativo** no tail. **[verificado]**: `λ_B` bruto chega a ~0 em `dr≈740` e a **−0,275 em dr=900**; o piso (D-22) o trava em 0,15 **conservando T_m** (`λ_A+λ_B=T_m` exato — também [verificado]). O conserva-total é correto, mas a forma linear é **fisicamente inválida** no tail e o piso passa a *fazer modelagem*. Em confrontos desiguais plausíveis da Copa (dr≈500–600), o modelo já opera perto da borda de validade. A forma **saturante** `f_sat=GD_max·tanh(dr/dr_escala)`, já especificada no apêndice, resolveria — segue não adotada (decisão deveria sair do backtest).

### 3.5 Incerteza e propagação (`features_pit` + `predictor.elo_direct_read`) — elegante, parcialmente alimentada
A propagação determinística por estratos de igual probabilidade é **reprodutível** (sem RNG) e correta: **[verificado]** encolhe o favorito (Jensen — P(V) em dr=300 cai de 0,752 para 0,727 sob σ=150) e mantém `P∈[0,1]`, soma 1. **Mas** o insumo é parcial: o contrato (§3.12) define `σ_ajuste` com 5 termos (desfalque-dúvida, meio-tier, desvio de forma, fuso, descanso); o código implementa **só** `c·desvio_forma` (`features_pit`, `sigma_ajuste_c=80`). A v0.3 passou a somar `banda_mando²` em `predict_match` quando há mando (D-28) — bom —, mas no **backtest** (`features_pit`) a banda de mando **não** entra. Resultado: a incerteza propagada ignora desfalques/fuso/descanso (que dependem de dados ainda não ingeridos).

### 3.6 Ensemble (`predictor.predict`) — diversidade redundante no histórico
Pesos sem-odds `0,56 Poisson / 0,44 Elo`. No histórico **não há perna de mercado** (`camada2-planejamento-v1 §2.1` — sem odds gratuitas). Como Poisson e Elo-direto **derivam do mesmo `dr`**, são **duas leituras correlacionadas da mesma fonte** — **[verificado]**: em dr=200, P(V)_Poisson=0,585 e P(V)_Elo=0,634, ambas subindo juntas com dr. A própria nota `02 - Modelos/Ensemble.md` admite que "a diversidade real vem do mercado". Os pesos *com odds* (0,45/0,35/0,20) nunca foram validados. Conclusão: a combinação de modelos, central no design, é hoje **redundante** na validação — e explica em parte por que o edge sobre o Elo é pequeno (Problema P-A/§3 do veredito).

### 3.7 Altitude (`altitude.py`) — maior alavanca; cobertura corrigida, calibração ainda extrapolada
`GD_alt=θ_alt·(pen_B−pen_A)/1000`, `pen=max(0, alt_sede−alt_casa)`, θ_alt=0,5 (McSharry, BMJ 2007, base CONMEBOL). Portão real **+0,0491, IC [+0,028, +0,070] em 554 jogos** (reproduz [[Backtest baseline (resultados)]]/D-18). A v0.3 **corrigiu a cobertura para 2026** — confirmei `"guadalajara": 1566`/`"zapopan": 1566` e a normalização de acentos `_norm` em `CITY_ALT`; Monterrey (540 m) fica nível do mar (correto). Ressalvas que **continuam**:

- **Magnitude grande e θ extrapolado.** Um termo desloca λ ~0,56 de cada lado; θ=0,5 é da **CONMEBOL** aplicado também à **CONCACAF** (P11, aberto) — não há θ por confederação.
- **Elevações hardcoded.** `CITY_ALT`/`TEAM_HOME_ALT` são dicionários pequenos no código (só 4 seleções "adaptadas"), não carregados via Open-Meteo Elevation como o contrato sugere ("[verificar via Open-Meteo]"). Qualquer grafia divergente de cidade no martj42 **desliga** a altitude silenciosamente.
- **Risco de dupla contagem com o mando** em jogos do México em casa (declarado, B2): `+1,12` de altitude **e** `+40` de mando se somam sem calibração conjunta.
- **Não entra na simulação do torneio** — ver Problema N2 (novo).

### 3.8 Calor e Estilo — **corretamente rejeitados pelo portão** ✅
`heat.py` (E3) e `estilo.py` foram construídos e **barrados**: estilo ΔBrier-BTTS −0,0008, IC [−0,0083, +0,0069] cruza zero (D-23); calor +0,0007, IC [−0,0008, +0,0022] (D-19). Isto é um **ponto forte com justificativa**: a disciplina descartou features plausíveis sem evidência por jogo. (Nota de rigor: o portão do estilo usa um único cutoff treino/teste, não PIT por jogo como o `features_pit`; aceitável para um candidato rejeitado, mas registre a diferença.)

### 3.9 Confiança (`predict_match.confidence`) — desenho bom, insumo de maturidade ainda inerte
`conf=100·reliab(p_max)·maturidade(σ_R)`, com `reliab` isotônica do backtest (`calibrate_confidence`, PAV correto) e `maturidade=1−min(0,5, σ_R/200)`. Desenho sólido. **Porém** (Problema N3, novo) a confiança recebe `sigma_r_avg=(a["sigma_r"]+b["sigma_r"])/2` — o **`σ_R` bruto** (`predict_match.py:141`), não a versão escalada por `vol_mult` que a v0.3 levou ao `σ_dr`. Como `σ_R≈40` para todos, **[verificado]** `maturidade≈0,8` é praticamente constante entre elites → a confiança vira **essencialmente uma função de `p_max`**. O conserto de σ da v0.3 **não chegou** à confiança.

### Modelos mais robustos (o que seria superior, e por quê)
Para um sistema de previsão sério de seleções, em ordem de custo-benefício, **tudo paramétrico e auditável** (respeitando a decisão D-02 de não usar ML opaco):

1. **Dixon-Coles** (correção τ para placares baixos) — corrige o viés de BTTS/under da independência Poisson **e** entrega um gerador direcional de λ. Maior retorno; já no roadmap, deveria subir.
2. **Poisson bivariado / Weibull-count** — captura a correlação de gols **sem** o hack do piso de λ (resolve §3.4 de raiz).
3. **Regressão de força ataque/defesa (Maher 1982; Karlis-Ntzoufras)** como **prior não-Elo** — daria **diversidade real** ao ensemble (hoje redundante, §3.6) e desacopla `λ_A`/`λ_B` do escalar único `dr`.
4. **σ baseado em dados (Glicko/TrueSkill** ou erro-padrão do ajuste de Elo) — resolve a degenerescência de §3.1/§3.9 e torna banda/confiança informativas.
5. **Recalibração isotônica/Platt do 1X2 por faixa** — corrige a superconfiança medida em [0,8–0,9] (Problema P-C); barata e mensurável direto.
6. **Incorporar odds de fechamento** quando houver captura — o único sinal verdadeiramente independente; transforma o ensemble de cosmético em real.

> Bayes hierárquico daria *shrinkage* elegante, mas o projeto o rejeita por auditabilidade/overfit (D-02) — decisão legítima dado o tamanho da amostra por seleção; nenhuma das sugestões 1–6 exige ML opaco.

---

## 4. Fontes de dados

**Inventário** (`03 - Dados/Fontes gratuitas.md`, `camada2-planejamento-v1 §2.1`). Fonte primária: **martj42/international_results** (resultados 1872–2026). Complementares **declaradas**: fixturedownload (calendário), StatsBomb Open Data (xG/bola parada, histórico parcial), Open-Meteo (clima/altitude), Wikidata (elevação/técnico), eloratings.net (benchmark), Kalshi/Polymarket (mercado prospectivo).

**O que está realmente em uso.** Só o **martj42** é ingerido pelo código (`ingest.py`, `MARTJ42_URL`). O `altitude.py` usa **tabelas hardcoded**, não Open-Meteo. O `heat.py` usaria `climatology.json` (Open-Meteo), mas o calor foi rejeitado. **Nenhuma** das demais fontes (fixturedownload, StatsBomb, Wikidata, odds) está integrada ao pipeline. Ou seja: **a base efetiva do sistema é uma única fonte de resultados brutos.**

**Qualidade / confiabilidade / cobertura / atualização.**
- **martj42** é base reconhecida e ampla, porém é **resultado bruto**: sem xG, sem escalações, sem minuto de gol, sem árbitro. Inclui entidades **extintas/não-FIFA** (Iugoslávia, etc.), ruído para benchmark e para a busca de nomes.
- **Cobertura temporal** vai a 1872; o Elo é reconstruído desde 1500. Jogos do séc. XIX inflam a métrica "todos os jogos" (goleadas fáceis) — por isso o recorte honesto é **torneios** (n=2.241). O projeto reconhece e usa esse recorte como aceite.
- **Atualização** é por *snapshot* manual (`ingest --download`, D-03) — coerente com "roda local", mas exige re-rodar o pipeline antes de cada rodada da Copa; **não há automação**.
- **Benchmark de Elo** contra eloratings.net é **manual e nunca automatizado** (`elo_engine.main` só imprime o top-N). A auditoria anterior verificou artefatos (Colômbia > Brasil; valores absolutos ~70 pts acima do eloratings). O invariante "±25 nas top-30" não é medido em código (Problema P-M).
- **Reprodutibilidade dos dados (novo, Problema N5).** O repositório **não versiona `dados/`**: o tree do GitHub não contém `copa2026.json` (sorteio), `results.csv`, `scm.sqlite`, `climatology.json` nem `shootouts.csv`. O `scm_analytics/.gitignore` ignora `dados/*.sqlite` e `dados/*.csv` (intencional, D-13) — **mas não `dados/*.json`**, e ainda assim o `copa2026.json` **não está no repo**. Consequência: **um clone limpo não roda `simulate` out-of-box**, e os números de título publicados (Argentina 18,6% etc., [[Auditoria tecnica externa (2026-06-18)]]) **não são reproduzíveis a partir do repositório**.

**Informações faltantes que mais melhorariam a precisão** (em ordem de impacto):
1. **Escalações/desfalques estruturados** — o maior fator de curto prazo num jogo; hoje **ausente** (Camada 3 não implementada).
2. **xG histórico (StatsBomb)** — prior de estilo muito menos ruidoso que gols brutos; viabiliza o piso de bola parada.
3. **Odds/mercado de fechamento** — sem elas o ensemble não tem diversidade real **e** falta o comparador de mercado do aceite.
4. **Elevação por sede + altitude-de-casa das 48 via Open-Meteo** — substitui os dicionários hardcoded e cobre todas as sedes/seleções.
5. **Minuto do gol (`goalscorers.csv`)** e **sede/horário por jogo** — habilitam "tempo do gol" e calor/fuso.

---

## 5. Qualidade do código

Boa no geral; nível de projeto bem cuidado. Por critério:

- **Organização/legibilidade:** alta. Módulos curtos, docstrings que citam o contrato, nomes consistentes, PT-BR coerente, `from __future__ import annotations`.
- **Modularização:** boa (núcleo puro × I/O; contratos por tabela).
- **Boas práticas / repetição:** SQL **parametrizado** (sem injeção evidente); seeds fixas (reprodutível). **Repetições reais:** a leitura V/E/D-do-Elo é reimplementada **três vezes** — `predictor.elo_direct_read`, `backtest_harness.elo_baseline_read` e `calibrate._elo_read` — com pequenas variações (risco de divergirem); P(V/E/D) também é recomputado em `predictor.markets` além de `poisson_reads`.
- **Complexidade:** baixa, exceto `features_pit.team_form` (consulta correlacionada cara; mitigada por índices).
- **Tratamento de erros:** adequado nas bordas (arquivo ausente → mensagem e exit 1; time não encontrado → sugestão por `difflib`). **Conexões SQLite sem *context manager*** (vazam em caminhos de erro); **`print` em vez de `logging`**.
- **Tipagem:** parcial; dataclasses `frozen=True` para parâmetros (bom). **Sem checagem estática** (mypy) configurada.
- **Performance:** bootstrap vetorizado (numpy, D-15); propagação cacheada (D-30). Gargalo histórico em `features_pit` mitigado por índices.
- **Segurança:** superfície mínima (local, sem rede no cálculo). `web.py` escuta só em `127.0.0.1`, `debug=False`, SQL parametrizado; `ingest --download` e `heat --build-climatology` usam `requests` (rede), isolados e opcionais. Nenhum segredo no repo.
- **Testabilidade:** alta — **18 arquivos de teste** sem rede, determinísticos, com fixtures `:memory:`. **Limitação:** os testes cobrem sobretudo **invariantes** (anti look-ahead, coerência [0,1], soma 1, lógica do portão) e **reprodução das próprias fórmulas** — `test_predictor.test_poisson_reproduces_manual` usa as mesmas contas do código, o que é **circular** (garante estabilidade, não correção externa). Nenhum teste detecta as divergências de modelagem (N1/N2/N3) porque são "comportamento implementado", não bug local.

---

## 6. Regras de negócio

Verifiquei se o que está codificado representa o domínio (futebol de seleções / Copa):

- **Mando = 0 em sede neutra; anfitrião com bônus.** Conceito correto e bem fundamentado (`02 - Modelos/Mando de campo.md`). **Mas:** (a) `H_host2026=+40` **nunca passou pelo portão** (P04, aberto — não há conjunto de calibração de Copa em co-anfitrião); (b) no `predict_match`, o mando é argumento manual (`--mando`), razoável, mas a banda de mando só entra no σ quando o usuário informa o mando.
- **Forma recente** — regra correta no contrato (ajuste curto-prazo ao Elo, ajustado a adversário, cap ±30). **Implementada no backtest** (`features_pit.team_form` → `dr_adj`), **mas NÃO aplicada na porta da frente** (`predict_match` descarta o ponto de forma — Problema N1, crítico para consistência). Ou seja: a regra existe e é validada, mas o usuário final não a recebe.
- **Desfalques direcionais** (ataque corta λ próprio; defesa/goleiro via dr) — regra **correta e diferenciada** no contrato (`02 - Modelos/Desfalques direcionais.md`), mas **não implementada** (Camada 3, JSON manual). O sistema **não considera lesões/suspensões** — limitação grande para previsão real de jogo.
- **Formato e chaveamento da Copa 2026** — `simulate.py` codifica o **chaveamento oficial da FIFA** (R32 73–88 → final 104) e aloca os 8 terceiros por **elegibilidade do Anexo C** com backtracking, validado nas **495 combinações** (`tests/test_simulate.test_assign_thirds_valid_for_all_combos`). Excelente fidelidade ao regulamento. **Simplificação declarada:** desempate de grupo `pts → saldo → gols pró → moeda` — **não modela o confronto direto (head-to-head)** que o regulamento da FIFA usa antes do saldo; e o desempate fino dos terceiros não é linha-a-linha. Efeito pequeno no título, mas é um desvio de regra.
- **Mata-mata / prorrogação / pênaltis** — `predictor.knockout_advance`: `avanço_A=P(V)+P(E)·(0,5+ε·sinal(dr))`, ε=0,03 [a calibrar]. Conceito correto; releitura do 1X2 (D-31). `calibrate_ko.py` mede o ε empírico via `shootouts.csv` (rodar na máquina do usuário; ε segue 0,03 até medir).
- **Registro pré-jogo imutável** — regra correta e essencial (`03 - Dados/Registro de previsoes.md`). **Execução é manual:** o `registro-previsoes.csv` foi preenchido à mão e a coluna "Resultado" está vazia (Problema P-G) → **zero validação prospectiva fechada** até agora.
- **Estilo exposto apesar de rejeitado (novo, N4).** `predict_match` tem `--estilo` (`predict_match.py:161`) que aplica o estilo ao λ, **embora o portão o tenha rejeitado** (D-23). Oferecer ao usuário uma feature que a própria disciplina barrou contradiz o princípio do portão (a web não usa, mas a CLI sim).

---

## 7. Problemas encontrados

Severidade: **Crítica** (compromete a validade do que o sistema afirma) · **Alta** · **Média** · **Baixa**. Coluna **Origem**: `Novo` = achado desta auditoria (2026-06-19); `Aberto` = confirmado ainda em aberto no código atual (vinha da auditoria interna ou do contrato). Todos verificados no código `baseline-v0.3-altitude`.

| # | Problema | Gravidade | Origem | Local | Impacto | Como corrigir |
|---|---|---|---|---|---|---|
| N1 | **A "porta da frente" não aplica a forma recente** que o backtest valida: `predict_match` usa `dr = elo_A − elo_B + mando` e **descarta** o ΔE de forma (só usa a dispersão para σ) | **Alta** | Novo | `predict_match.py:105,119-120` vs `features_pit.py` (`dr_adj = dr_elo + form_home − form_away`) | O modelo entregue ao usuário **difere do modelo validado**; a métrica do backtest não cobre o que a CLI/web produzem (mismatch backtest↔produção) | Aplicar a forma no `predict_match` (somar `form_home − form_away` ao `dr`) **ou** documentar e rebacktestar a variante sem forma; alinhar os dois caminhos |
| N2 | **Altitude (a maior alavanca adotada) não entra no Monte Carlo do torneio** | **Média** (Alta p/ Copa) | Novo | `simulate.build_lambda_table` (`simulate.py:128-138`, `lambdas(dr, p)` sem `gd_alt`/cidade) | A chance de título ignora a vantagem do México em CDMX/Guadalajara — justamente onde altitude muda o favoritismo (México×Alemanha em CDMX: GD_alt≈+1,12). Números de título subestimam sede alta | Passar a sede/cidade de cada jogo ao gerar λ no torneio e aplicar `gd_alt` (e mando do anfitrião) por confronto |
| N3 | **Confiança usa `σ_R` bruto** → "maturidade" ≈ 0,8 constante entre elites; o conserto de σ da v0.3 não chega à confiança | **Média** | Novo | `predict_match.py:141` (`sigma_r_avg = (a["sigma_r"]+b["sigma_r"])/2`) | A confiança vira função quase pura de `p_max`; o componente "maturidade do rating" é cosmético para os jogos que interessam | Usar o `σ_R` escalado por `vol_mult` (ou σ baseado em dados) também na confiança |
| N5 | **Repositório não versiona `dados/`**: faltam `copa2026.json` (sorteio), DB e snapshots → clone não roda `simulate`; números de título não reproduzíveis | **Média** | Novo | tree do GitHub (sem `dados/`); `scm_analytics/.gitignore` ignora só `*.sqlite`/`*.csv` | Reprodutibilidade quebrada: a Funcionalidade #1 (simulador) e os resultados publicados não saem de um clone limpo | Versionar `copa2026.json` (não é dado bruto, é configuração do torneio) e documentar o passo de geração do DB; ou empacotar um *fixture* mínimo |
| P-A | **Poisson independente / sem Dixon-Coles; ensemble sem diversidade real** (Poisson e Elo derivam do mesmo `dr`; mercado=0 no histórico) | **Alta** | Aberto | `predictor.poisson_reads`/`predict`; viés BTTS +3,8pp / over +7pp medido por `calibrate_total` | Viés sistemático de BTTS/under; a "combinação de modelos" é redundante → edge sobre o Elo fica pequeno (+0,003) | Dixon-Coles (correlação) + membro de prior não-Elo (ataque/defesa/xG) e/ou mercado; revalidar pesos |
| P-B | **`σ_R` estruturalmente função de `n`** (satura ~40); `vol_mult` atenua mas não resolve | **Alta** | Aberto | `elo_engine.sigma_r`; `features_pit.vol_mult` | Banda/propagação/confiança pouco informativas entre seleções estabelecidas | Migrar para Glicko/TrueSkill ou estimar σ do erro do ajuste de Elo |
| P-D | **Forma linear de GD inválida no tail** (`λ_B<0` antes do piso; piso faz a modelagem) | **Média** | Aberto | `predictor.lambdas`/`gd_of`; [verificado] `dr=900 → λ_B bruto −0,275` | Em confrontos muito desiguais a saída depende do piso, não do modelo | Adotar forma saturante `tanh` (já no apêndice), decidida no backtest |
| P-C | **Superconfiança em favoritos fortes [0,8–0,9]** — medida, não corrigida | **Média** | Aberto | `report.band_coverage_binned` (obs 0,74 vs banda [0,84–0,92]) | Favoritos da Copa vivem nessa faixa; probabilidades altas demais | Recalibração isotônica/Platt do 1X2 por faixa |
| P-E | **Mando do anfitrião `+40` nunca passou pelo portão** (P04) | **Média** | Aberto | `MODELO_FINAL` (H_host2026 "[a calibrar]"); `predict_match --mando` | Número-chave para 6 anfitriões em 2026 não validado | Montar conjunto de calibração de Copa/co-anfitrião e gatear mando×altitude juntos |
| P-F | **Camada 3 (desfalques/escalações) ausente** | **Média** | Aberto | sem módulo; contrato `Desfalques direcionais` | Sistema não considera o maior fator de curto prazo (lesões/suspensões) | Implementar entrada JSON manual → δ_ataque (corta λ próprio) e σ |
| P-G | **Zero validação prospectiva fechada** — registro manual, coluna "Resultado" vazia | **Média** | Aberto | `03 - Dados/registro-previsoes.csv`; `06 - Analises/*` | Nenhum Brier prospectivo real medido; previsões manuais com inputs ≠ código | Gerar o registro pelo `predict_match` (carimba versão/hash) e preencher resultados pós-jogo |
| P-H | **Schema implementado é subconjunto** (sem `venues`/`context`/`statsbomb`/`odds`) | **Média** | Aberto | `db.SCHEMA` vs `03 - Dados/Esquema SQLite.md` | Bloqueia xG/odds/contexto — a evolução planejada não "encaixa" sem migração | Evoluir o schema para o alvo antes da Camada 3+ |
| N6 | **K=50 para toda partida continental** (não só finais) | **Baixa** | Novo | `elo_engine.k_factor` (comentário diz "finais continentais") | Jogos de grupo de Euro/Copa América recebem K alto demais → ratings levemente enviesados | Detectar fase "final/decisão" ou rebaixar continental de grupo para K=40 |
| N4 | **`--estilo` exposto na CLI apesar de rejeitado pelo portão** (D-23) | **Baixa** | Novo | `predict_match.py:161,132` | Contradiz a disciplina do portão; usuário pode ligar uma feature sem skill por jogo | Remover o flag ou marcá-lo claramente como experimental/desativado |
| N7 | **`markets()` definida após o guard `if __name__=="__main__"`** | **Baixa** | Novo | fim de `predictor.py` | Estilo/legibilidade; função "escondida" abaixo do main | Mover `markets()` para junto das demais funções puras |
| P-I | **Faxina:** sem `conftest.py`; conexões SQLite sem context manager; `print` vs `logging`; leitura Elo-direto duplicada em 3 módulos | **Baixa** | Aberto | `tests/*`; `db.connect`; vários `main`; `predictor`/`backtest_harness`/`calibrate` | Manutenção/robustez; risco de as 3 leituras Elo divergirem | Centralizar a leitura Elo-direto; `conftest.py`; context managers; `logging` |
| P-J | **Dependências não pinadas** (`>=`) apesar de TECH_STACK dizer "pinadas" | **Baixa** | Aberto | `requirements.txt` | Reprodutibilidade frágil no tempo | Pinar versões exatas (`==`) ou usar lock |
| P-K | **Documentação inconsistente:** contagem de testes (README diz "73" e "86"; há 18 arquivos) e **deriva de versão** (CLAUDE.md cita `v0.2`/`v0.2.1`; código é `v0.3`) | **Baixa** | Aberto | `README.md`, `CLAUDE.md`, `predictor.MODEL_VERSION` | Confunde novos leitores/agentes | Reconciliar contagens e versão; marcar `contexto-handoff` como histórico |
| P-L | **`natural_key` sem cidade** → jogos no mesmo dia/torneio podem colidir | **Baixa** | Aberto | `ingest.load_results` | Risco teórico de perder um jogo (raro) | Incluir cidade/ordem no `natural_key` |
| P-M | **Benchmark de Elo não automatizado; ratings com artefatos** | **Baixa** | Aberto | `elo_engine.main` (só imprime); Colômbia>Brasil, valores inflados | Sem sanidade reprodutível; ratings absolutos divergem do eloratings | Script de comparação vs snapshot eloratings; considerar recência/regularização |

---

## 8. Melhorias (priorizadas por impacto)

**Prioridade 1 — consistência e validade (antes de confiar em qualquer número):**

1. **Alinhar produção e backtest:** aplicar a forma no `predict_match` (N1) e a **altitude na simulação** (N2). Sem isso, o que o usuário vê não é o que foi validado. Custo baixo, impacto altíssimo na credibilidade.
2. **σ informativo de verdade** (Glicko/TrueSkill ou erro do ajuste de Elo) e **usá-lo também na confiança** (P-B, N3). Destrava banda/propagação/confiança, hoje quase inertes.
3. **Fechar o laço prospectivo** (P-G): gerar o registro pelo código, carimbar versão/hash, preencher resultados → primeiro **Brier prospectivo real** da Copa.
4. **Versionar a configuração do torneio** (`copa2026.json`) e documentar a geração do DB (N5) → resultados reproduzíveis.

**Prioridade 2 — precisão e robustez do modelo:**

5. **Dixon-Coles** + **membro de prior não-Elo** no ensemble (P-A) — corrige BTTS/under e dá diversidade real.
6. **Forma saturante de GD/T_m** no tail (P-D) e **recalibração isotônica do 1X2** (P-C).
7. **Calibrar mando×altitude juntos** e por confederação (P-E, §3.7).

**Prioridade 3 — dados e domínio:**

8. **Camada 3 (desfalques/escalações)** — maior fator jogo-a-jogo (P-F).
9. **Evoluir o schema** (`venues`/`context`/`odds`/`statsbomb`) (P-H) e integrar **odds** quando houver captura.
10. **Automatizar o snapshot** e o **benchmark de Elo** (P-M).

**Prioridade 4 — qualidade/manutenção:** centralizar a leitura Elo-direto, `conftest.py`, context managers, `logging`, pinar dependências, reconciliar a documentação (P-I, P-J, P-K, P-L, N4, N6, N7).

> **Sobre estatística (igual à conclusão da auditoria interna, e reforçada aqui):** o maior retorno **não** é adicionar fatores — a v5 já tem fatores demais para a amostra. É **fortalecer o baseline, a consistência e a validação**: produção = backtest, σ informativo, Dixon-Coles, diversidade real e validação prospectiva. "Mais variáveis" sem isso só aumenta graus de liberdade contra amostras pequenas (o risco nº 1 declarado em `camada1-planejamento-v5 §16`).

---

## 9. Funcionalidades futuras (com justificativa)

Pensando em previsão/análise da Copa 2026. **Observação:** o simulador de torneio e o mata-mata, sugeridos na auditoria anterior, **já foram entregues** (D-31/D-32/D-33) — as sugestões abaixo são as próximas fronteiras.

1. **Simulador com altitude/mando por sede e head-to-head no desempate** (evolução do `simulate.py`). *Justificativa:* hoje o torneio ignora a maior alavanca (N2) e o critério de desempate da FIFA; corrigir isso torna a chance de título fiel ao regulamento e às sedes reais.
2. **Comparador de mercado** (Kalshi/Polymarket por captura manual com timestamp) na interface. *Justificativa:* o próprio projeto define mercado como benchmark (D-08); expor onde o modelo concorda/diverge é honesto e informativo, e prepara a perna independente do ensemble.
3. **Explicador de previsão** ("por que este número"): decompor `dr` em Elo/forma/altitude/mando e mostrar a sensibilidade. *Justificativa:* auditabilidade é valor central do projeto; concretizá-la para o usuário é diferencial barato.
4. **Camada 3 de desfalques via JSON** com efeito direcional em λ e σ. *Justificativa:* é o fator que mais muda um jogo específico e hoje está totalmente ausente (P-F).
5. **Cenários de classificação** ("quem precisa de quê na última rodada") + flag de jogo-morto. *Justificativa:* captura motivação/rotação sem fingir prever o imprevisível.
6. **Backtest dirigido de 2018/2022** com comparação a previsores públicos (ex.: Opta) como teto externo. *Justificativa:* dá um comparador realista acima do Elo/uniforme.
7. **Mercados de placar exato + "tempo do gol"** (ao ingerir `goalscorers.csv`) com base Dixon-Coles. *Justificativa:* completa a oferta de mercados com base correlacionada correta.
8. **Atualização agendada do snapshot** antes de cada rodada. *Justificativa:* operacionaliza o uso na Copa sem virar serviço online (respeita "roda local").

---

## 10. Roadmap (ordem de prioridade)

**Fase 0 — Consistência e validação (antes de confiar em qualquer número):**
- Alinhar **produção ↔ backtest**: forma no `predict_match` (N1), **altitude na simulação** (N2), `σ_R` informativo na confiança (N3).
- Versionar `copa2026.json` + documentar geração do DB (N5).
- Iniciar o **registro prospectivo gerado por código** (P-G).
- *Resultado:* o que o usuário vê passa a ser o que foi validado, e começa a existir Brier prospectivo real. **Sem isto, o resto é decoração.**

**Fase 1 — Núcleo estatístico:**
- **σ baseado em dados** (Glicko/TrueSkill) (P-B) → banda/confiança úteis.
- **Forma saturante** (P-D) e **recalibração isotônica do 1X2** (P-C).
- **Gatear mando do anfitrião** e calibrar **mando×altitude** por confederação (P-E, §3.7).

**Fase 2 — Precisão de modelo:**
- **Dixon-Coles** + **prior não-Elo** no ensemble (P-A) — corrige BTTS/under e dá diversidade real.
- **Camada 3** (desfalques) (P-F) — maior fator jogo-a-jogo.
- **Confronto direto** no desempate de grupo do simulador (§6).

**Fase 3 — Produto/valor:**
- **Comparador de mercado** + **explicador de previsão** na interface.
- **Simulador fiel** (altitude/mando/head-to-head) com a chance de título corrigida.

**Fase 4 — Infra/manutenção (contínuo):**
- Evoluir schema (P-H), faxina (P-I), pinagem (P-J), reconciliar doc/versão (P-K, N4, N6, N7), benchmark de Elo automatizado (P-M), `natural_key` com cidade (P-L).

**Pode esperar (corretamente despriorizado pelo projeto):** afinação fina de pesos do ensemble (só com ≥30 jogos), xG ao vivo das 48 (sem fonte), árbitro individual (lacuna declarada).

---

## 11. Conclusão

**Pontos fortes (com justificativa técnica).**
- **Disciplina de processo rara:** contrato congelado (v5.0), ADRs ([[Decisoes tecnicas]]), múltiplas rodadas de auditoria, fatores ancorados em literatura. Rastreabilidade nota→fórmula→código exemplar.
- **Portão estatístico que realmente barra:** o IC-bootstrap-pareado-que-não-cruza-zero (`backtest_harness.gate`) está correto e **[verificado]** reproduz a rejeição de calor/estilo e a adoção de altitude. Rejeitar features plausíveis por falta de evidência por jogo é honestidade que quase nenhum projeto pratica.
- **Point-in-time levado a sério:** rating pré-jogo persistido (`match_ratings`), features só com passado, teste anti look-ahead dedicado.
- **v0.3 corrigiu o essencial da auditoria anterior** — **confirmei no código**: curva de empate empírica (§3.3), comparador **Elo público** (e o modelo o supera com IC>0), σ por confronto, cobertura de Guadalajara, cobertura de banda por faixa, mata-mata e simulador oficial da FIFA.
- **Engenharia limpa, local, reprodutível em lógica, R$ 0**, com testes determinísticos e coerência [0,1] por construção.

**Pontos fracos (com justificativa técnica).**
- **Divergências produção↔validação:** a porta da frente não aplica a forma validada (N1) e a simulação ignora a altitude adotada (N2) — o usuário não recebe exatamente o modelo medido.
- **Aparato de incerteza ainda parcialmente inerte:** `σ_R` estruturalmente preso a `n` (P-B) e confiança usando σ bruto (N3) → banda/maturidade pouco informativas entre elites.
- **Sinal de skill pequeno:** o edge sobre o Elo público é real, porém modesto (+0,003 de Brier), porque o ensemble é redundante e a Poisson é independente (P-A).
- **Lacunas de domínio para a Copa:** sem desfalques (P-F), mando do anfitrião não gateado (P-E), altitude ainda extrapolada para a CONCACAF (§3.7).
- **Validação prospectiva ainda zero** (P-G) e **dados do torneio não versionados** (N5).

**O que mais chamou a atenção.** O **contraste entre a qualidade do planejamento e a inércia/inconsistência de partes da execução.** A v0.3 fechou as divergências mais graves que a auditoria interna apontou (curva de empate, comparador Elo) — mérito real e verificável. Mas surgem, no mesmo código, **novas inconsistências do tipo "o que se valida ≠ o que se entrega"**: a forma some na porta da frente, a altitude some no torneio, o conserto de σ não chega à confiança. São baratas de corrigir e, uma vez corrigidas, elevam imediatamente a credibilidade do sistema. O segundo destaque é o portão: continua sendo o melhor ativo do projeto.

**Nível técnico.** Engenharia e processo: **alto**. Modelagem estatística efetivamente entregue: **médio** — baseline correto e honesto, comparador agora não-trivial, mas com diversidade de modelo redundante, incerteza parcialmente inerte e divergências produção↔backtest. É claramente trabalho de alguém competente e com forte cultura de honestidade metodológica; o teto atual vem da distância entre o que o contrato promete e o que o código entrega, e de um sinal de skill ainda pequeno.

**Preparo para análises da Copa 2026.** Como **ferramenta de estudo** que produz probabilidades 1X2 razoáveis e calibradas na média, com confiança honesta e simulador de torneio: **utilizável, com ressalvas**. Como **sistema de previsão sério da Copa**: **ainda não pronto**. Faltam, em ordem: (1) produção = backtest (forma, altitude no torneio, σ na confiança); (2) σ informativo e banda que signifique algo; (3) cobrir desfalques; (4) diversidade real de modelo (Dixon-Coles / prior não-Elo) para crescer o edge; (5) fechar o laço prospectivo. **A arquitetura suporta essa evolução** (estágios desacoplados, contrato versionado, portão), mas os **modelos atuais não a sustentam sem as Fases 0–1**. A filosofia "congela o contrato, mede com portão, nunca afirma certezas" é a base certa — o que falta é fazer o código honrar o que o contrato promete, de ponta a ponta, e medir contra adversários à altura ao longo da própria Copa.

---

### Anexo A — Verificações numéricas executadas (2026-06-19)

Reimplementei as funções centrais (`predictor`/`elo_engine`) num script isolado e confirmei:

| Verificação | Resultado | Confere? |
|---|---|---|
| Poisson IRN×NZL (λ=1,40/0,78) | P(V)=0,517 · P(E)=0,275 · P(D)=0,209 · over2.5=0,372 · BTTS=0,408 · soma=1,000000 | sim (reproduz `test_predictor` e a execução manual) |
| `λ_B` no tail sem piso | `dr=740 → λ_B≈0`; `dr=900 → λ_B bruto −0,275`; piso conserva `λ_A+λ_B=T_m` exato | confirma P-D e D-22 |
| Curva de empate (atual) | C1 empírica: 0,2847 (dr=0), 0,2629 (100), 0,1942 (300) ≠ proxy antigo (0,27/0,2219/0,1499) | confirma §3.3 corrigido (≠ proxy) |
| `σ_R` vs `n` | 200 (n=0) → 42,9 (n=80) → 40,1 (n=150) → 40,0 (n=400) | confirma P-B (satura ~40) |
| Maturidade da confiança | `maturidade(σ_R=40)=0,8` (usa σ bruto) | confirma N3 |
| Propagação (Jensen) | P(V) dr=300: 0,752 (σ=0) → 0,727 (σ=150); encolhe o favorito | confirma §3.5 |
| Ensemble correlacionado | dr=200: P(V)_Poisson=0,585 e P(V)_Elo=0,634 sobem juntos | confirma §3.6 |

### Anexo B — Achados confirmados diretamente no código local (`scm_analytics/scm/`)

| Achado | Evidência |
|---|---|
| N1 forma descartada na porta da frente | `predict_match.py:105` `dr = a["elo"] - b["elo"] + mando`; `:119-120` `_, dev_a, n_fa = team_form(...)` (1º retorno descartado) |
| N2 altitude ausente no torneio | `simulate.py:138` `la, lb = lambdas(dr, p)` em `build_lambda_table` — sem `gd_alt`/cidade |
| N3 confiança com σ bruto | `predict_match.py:141` `sigma_r_avg = (a["sigma_r"] + b["sigma_r"]) / 2.0` |
| N4 estilo exposto | `predict_match.py:161` `--estilo`; `:132` aplica `team_styles` (rejeitado em D-23) |
| N5 dados não versionados | tree do GitHub sem `dados/`; `scm_analytics/.gitignore` cobre só `dados/*.sqlite` e `dados/*.csv` |
| Versão do modelo | `predictor.py:24` `MODEL_VERSION = "baseline-v0.3-altitude"`; `tests/` = 18 arquivos |

---
*Auditoria independente — 2026-06-19. Baseada na leitura do repositório `gustavomot4/scm-analytics` (código `scm_analytics/` + vault `00`–`06`) e em verificação numérica das fórmulas centrais. Sem implementação de funcionalidades. Conclusões citam arquivo/módulo; números marcados [verificado] foram reproduzidos em código. Relacionado: [[Auditoria tecnica externa (2026-06-18)]] · [[Backtest baseline (resultados)]] · [[Decisoes tecnicas]] · [[MODELO_FINAL]] · [[camada1-apendice-formas-v5]].*

---

## Follow-up (2026-06-19) — correções de consistência aplicadas (Fase 0)

Aplicadas e verificadas (harness numpy+sqlite — **pytest indisponível no sandbox**; rodar `python -m pytest -q` na máquina do usuário) as correções que **não adicionam termos novos** a λ/dr (logo dispensam portão): apenas alinham a produção ao modelo já validado.

| # | Problema | Estado | Evidência |
|---|---|---|---|
| N1 | Forma descartada na porta da frente | ✅ **corrigido** (D-34) | `predict_match` agora faz `dr = elo_A − elo_B + (forma_A − forma_B) + mando`; teste novo `test_dr_includes_recent_form` ([verificado] dr=−130,17 = Elo −185,99 + forma 55,81) |
| N3 | Confiança com σ_R bruto | ✅ **corrigido** (D-35) | `sigma_r_avg = (sr_a + sr_b)/2` (σ escalado por `vol_mult`); [verificado] conf muda de 27,81 (bruto) p/ 26,06 (escalado) |
| N4 | `--estilo` exposto sem aviso | ✅ **corrigido** (D-36) | ajuda da CLI marca `[EXPERIMENTAL] … REJEITADO pelo portão` |

**Verificação:** harness reproduz os invariantes dos testes existentes de `predict_match`/`predictor`/`simulate` (coerência [0,1], soma 1, Σcampeão=1, Σpassar=32, altitude/mando favorecem o mandante, etc.) — **26/26 ok** após as mudanças, no FS nativo (a mount do sandbox serve `.py` recém-escritos de forma intermitente/stale → D-16; verificação feita sobre cópia em `/tmp`).

**Não incluído nesta rodada** (Fase 1+ do roadmap, exigem dados e/ou portão de backtest — fora do escopo "consistência"): **N2** (altitude no Monte Carlo do `simulate` — precisa do mapa jogo→sede de 2026, **não inventar**), **P-A** (Dixon-Coles / diversidade real do ensemble), **P-B** (σ estrutural — Glicko/TrueSkill), **P-C** (recalibração isotônica), **P-D** (forma saturante), **P-E** (mando do anfitrião no portão), **P-F** (Camada 3 — desfalques), **P-G** (validação prospectiva fechada), **P-H** (schema-alvo). Continuam no [[BACKLOG]].

## Follow-up (b) (2026-06-19) — Fases 1–3 (com portão real no DB local)

Reproduzi primeiro os números do backtest no `dados/scm.sqlite` (Brier 0,5366; +0,0028 vs Elo público IC[+0,0023,+0,0033]) — então o portão abaixo é real, não estimado.

| # | Item | Estado | Evidência |
|---|---|---|---|
| N2 | Altitude no Monte Carlo | ✅ **adotado** (D-37) | `simulate` aplica `gd_alt` nos jogos de grupo do anfitrião (`copa2026.json` `altitude_venues`). México: avanço 98,5%→99,9%, título 3,1%→4,0%; Σcampeão=1, Σpassa=32 |
| P-G | Validação prospectiva | ✅ **entregue** (D-38) | `scm/registrar.py` register/settle/report, imutável (versão+hash). Fecha o laço da Copa |
| P-F | Camada 3 (desfalques) | ✅ **mecanismo entregue** (D-41) | `scm/desfalques.py` + hook; ataque-chave do mandante reduz P(V)/λ_a. Magnitudes [a calibrar]; dados via JSON do usuário |
| P-A | Dixon-Coles | 🔴 **testado, REJEITADO** (D-39) | ρ_MLE=−0,06 mas BTTS ΔBrier **−0,0007 IC[−0,0008,−0,0006]** (piora) e placar não significativo. Viés é de nível (T_base), não correlação. Candidato OFF |
| P-C | Recalibração 1X2 | 🔴 **testada, REJEITADA** (D-40) | temperatura T*=1,0 (nada a corrigir); isotônica piora fora de amostra (ΔBrier −0,0021 IC<0). Modelo já calibrado. Candidato OFF |
| P-B | σ informativo (Glicko) | 🟡 **candidato** (D-42) | `scm/sigma_glicko.py`: RD varia 51–64 nas top-14 (era ~40 fixo) → degenerescência resolvida. Adotar = rebuild + portão de banda na máquina do usuário |
| P-I/J | Higiene | ✅ **parcial** (D-43) | `predictor.ved_from_elo` (núcleo único, idêntico em 165 pts de grade); `conftest.py`; `requirements` com teto de major |

**Conclusão desta rodada.** Os ganhos de **produto/validação** entraram (altitude no torneio, registro prospectivo, mecanismo de desfalques). Os ganhos de **precisão paramétrica** (DC, recalibração) **não passaram o portão** — confirmando que, com os dados atuais, o núcleo Elo→Poisson está perto do teto e que o caminho para mais acurácia é **dado novo** (desfalques/odds/xG) e **σ informativo** (Glicko), não mais fórmulas. Ainda **abertos** (Fase 2–3): adotar σ-Glicko após o portão de banda (P-B), mando do anfitrião no portão (P-E), schema-alvo (P-H), odds/mercado, e preencher o registro prospectivo a cada rodada (P-G em uso).
