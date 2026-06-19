---
tags: [dev, audit, auditoria, externa]
status: atual
tipo: auditoria
data: 2026-06-18
aliases: ["Auditoria técnica externa", "Audit 2026-06-18"]
---

# Auditoria técnica externa — SCM Analytics (2026-06-18)

Auditoria independente do repositório (vault Obsidian + `scm_analytics/`), na função de **arquiteto de software e auditor técnico**. Não implementa funcionalidades; lê, executa e critica. Todas as conclusões citam o arquivo/módulo em que se baseiam. Onde uma informação não foi encontrada, isso é declarado. Princípio adotado do próprio projeto: **probabilidades, nunca certezas — e nada é elogiado sem justificativa técnica**.

> **Método.** Li toda a documentação (`00`–`06`) e todo o código (`scm/`, 16 módulos; `tests/`, 16 arquivos). **Executei** o sistema de ponta a ponta sobre os dados reais (martj42, 49.423 jogos): `pytest` (86/86 verdes), pipeline completo (`ingest → elo_engine → features_pit → predictor`), `backtest_harness`, `report`, e os portões `altitude`/`estilo`/`calibrate_total`. Reproduzi as métricas-chave de forma independente. Resultados empíricos aparecem ao longo do texto marcados como **[verificado]**.

> **Contexto importante.** O projeto **já passou por uma auditoria anterior** (`SCM_Analytics_Analise_Tecnica.docx`, respondida em [[Resposta ao audit tecnico]], achados P01–P12). Esta auditoria **verifica aquelas respostas** e vai além. Vários pontos abaixo confirmam achados já conhecidos e ainda abertos (P02, P05, P08, P11); outros são novos.

---

## 0. Veredito em uma página

O SCM Analytics é um **projeto de engenharia incomumente disciplinado para o seu porte**: documentação rastreável, decisões registradas (ADRs), contrato matemático congelado e auditado, e — o ponto mais raro — um **portão estatístico** (IC bootstrap pareado que não pode cruzar zero) que efetivamente **rejeita** fatores que não se sustentam (calor, estilo, calibração de coeficientes). Isso é honestidade metodológica que a maioria dos projetos de previsão esportiva não tem. **[verificado]**: 86/86 testes passam; o baseline bate o baseline uniforme com folga e IC sólido (todos os jogos Brier 0,5375; torneios 0,5598), e está bem calibrado (ECE ≈ 0,025).

Dito isso, há uma **distância material entre a sofisticação do contrato e o que o código realmente entrega**, e a validação responde a uma pergunta fraca. Os três problemas mais sérios:

1. **A validação só compara contra o "uniforme" (1/3,1/3,1/3)** — um piso trivial que qualquer Elo ingênuo supera. A comparação contra **Elo público e mercado**, que o próprio desenho do backtest exige como critério de aceite ([[camada2-planejamento-v1]] §5.1), **não está implementada**. Bater o uniforme **não** demonstra que o modelo é competitivo.
2. **A incerteza (σ) é, na prática, quase constante** para os confrontos que importam. `σ_R` é uma função determinística do nº de jogos e satura em ~40 para toda seleção estabelecida → no `predict_match`, `σ_dr = 80` para Brasil×Argentina, México×Alemanha e Espanha×Cabo Verde, **idêntico** **[verificado]**. A "propagação de incerteza", a "banda" e a "maturidade da confiança" — descritas como a conquista central da v3/v4 — carregam pouquíssima informação por confronto.
3. **A curva de empate empírica (C1) nunca foi implementada**; o que roda é exatamente o *proxy* fechado que a auditoria v5 mandou **não** usar ([[camada1-revisao-v5]] §1, V6; [[camada1-apendice-formas-v5]] §3).

**Nível técnico:** alto em engenharia e disciplina de processo; **médio** em modelagem estatística efetiva (muito do aparato sofisticado está inerte ou não-validado). **Preparo para a Copa 2026:** o motor é um previsor 1X2 razoável e honesto para estudo, mas **não está pronto** como sistema de previsão sério da Copa — faltam baseline real, diversidade de modelo, cobertura de dados de 2026 e um laço de validação prospectiva. Detalhes e correções abaixo.

---

## 1. Visão geral do projeto

**Objetivo.** Sistema **local e gratuito** que prevê partidas (foco Copa 2026) entregando **P(vitória/empate/derrota), gols esperados (λ), mercados derivados e um score de confiança** — explicitamente **probabilidades, não certezas**, e **não** ferramenta de aposta (fontes: [[CLAUDE]], [[MODELO_FINAL]], `scm_analytics/README.md`). Restrições inegociáveis: custo R$ 0, roda offline (nada lê a internet no cálculo; usa snapshot em disco), registro pré-jogo imutável, não inventar dados ([[CLAUDE]] "Restrições não negociáveis").

**Como funciona (fluxo principal).** Pipeline linear, com contratos via tabelas SQLite ([[Codigo (estrutura)]], `scm/`):

```
ingest → elo_engine → features_pit → predictor → backtest_harness → report
            (Elo+σ_R)   (forma, σ_dr)  (GD/T_m→Poisson + Elo-direto→ensemble)
```

1. `ingest.py` carrega o CSV do martj42 (resultados 1872–2026) para `matches`/`teams`, idempotente por `natural_key`.
2. `elo_engine.py` reconstrói o Elo cronologicamente e grava o **rating pré-jogo** de cada partida (`match_ratings`) — base do point-in-time.
3. `features_pit.py` monta features só com jogos anteriores à data (forma recente ajustada a adversário, `dr_adj`, `σ_dr`).
4. `predictor.py` converte `dr` em saldo `GD=f(dr)` e total `T_m=g(dr)`, gera a **matriz Poisson** (V/E/D, over, BTTS, placares) e a **leitura "Elo-direto" propagada** (com banda 16/84), e as combina num **ensemble**.
5. `backtest_harness.py` mede Brier/LogLoss/RPS com IC bootstrap e implementa o **portão**.
6. `report.py` produz reliability/ECE e "cobertura" de banda.

A "porta da frente" é `predict_match.py` (prevê um confronto a partir do Elo atual) e `web.py` (interface Flask local). Ferramentas de fator C2.5 (`altitude`, `heat`, `estilo`, `calibrate*`) avaliam candidatos atrás do portão.

**Módulos e relação.** Há boa separação: o `predictor` é puro (funções `lambdas`/`poisson_reads`/`elo_direct_read`/`predict` sem I/O), e a persistência fica nos `run()`. `altitude`/`heat`/`estilo` reusam `predict` + `gate`. `predict_match`/`web` reusam o `predict`. Acoplamento via SQLite mantém os estágios desacoplados (ver §2).

**Estado real (reconciliação das fontes).** A documentação tem versões sobrepostas: [[contexto-handoff]] (2026-06-15) diz "não há código de implementação / nada foi backtestado", mas isso ficou **desatualizado** — o código existe, foi backtestado e o baseline está validado contra o uniforme ([[Backtest baseline (resultados)]]). O modelo vigente é `baseline-v0.2.1-altitude` (`predictor.MODEL_VERSION`). É importante notar a confusão de contagem de testes na própria doc: `scm_analytics/README.md` diz "73 testes" em um lugar e "86" em outro; `CLAUDE.md` cita "73" e "86"; o real é **86 [verificado]**.

---

## 2. Arquitetura

**Organização de pastas.** Dupla natureza bem resolvida: um **vault Obsidian** (planejamento/`01`, modelos/`02`, dados/`03`, desenvolvimento/`04`, referências/`05`, análises/`06`) e o **pacote Python** (`scm_analytics/scm`). A separação documentação ↔ código é limpa e a rastreabilidade nota→fórmula→módulo é excelente (cada módulo cita a nota do contrato no docstring). Isso é um ponto forte real.

**Separação de responsabilidades / coesão.** Boa. Cada módulo tem uma responsabilidade única e um contrato de I/O por tabela ([[Esquema SQLite]]). O núcleo matemático (`predictor`) é testável sem banco. `db.py` centraliza schema e conexão.

**Acoplamento.** Baixo no geral, com **duas arestas a observar**:
- *Ciclo de import contornado em runtime.* `predictor.run()` importa `altitude.gd_alt` **dentro da função** ("import tardio (evita ciclo predictor<->altitude)", `predictor.py` ~l.157). O ciclo existe porque `altitude.py` importa de `predictor` **e** de `backtest_harness`, que por sua vez importa de `predictor`. Funciona, mas sinaliza que a lógica de **portão** (avaliação) e a de **predição** (produção) estão entrelaçadas. O ideal seria um módulo de "termos de λ" separado do harness.
- *Schema implementado é um subconjunto do desenhado.* O design ([[Esquema SQLite]], [[camada2-planejamento-v1]] §2.3) prevê `venues`, `context`, `statsbomb`, `odds_hist`; `db.py` cria só `teams/matches/match_ratings/match_features/predictions/meta`. Logo **E4/E5/E6/xG/odds não têm onde entrar** sem evoluir o schema — limitação estrutural para a evolução pretendida (§9).

**Escalabilidade.** O ponto fraco é `features_pit`: para cada jogo roda duas subconsultas correlacionadas de forma (`OR` em duas colunas), e o schema só tem índices de coluna única (`idx_matches_home`, `idx_matches_away`). **[verificado]**: nos 49.423 jogos o passo **não terminou dentro do limite** até eu adicionar índices compostos `(home_team_id,date)` e `(away_team_id,date)` — que aceleram muito **sem mudar resultados**. Recomendo adicioná-los a `db.SCHEMA`. Para a Copa (poucos jogos novos por rodada) o custo é irrelevante; para re-backtests completos, não.

**Manutenibilidade.** Alta: módulos pequenos (80–250 linhas), docstrings densos, nomes claros, testes por módulo. Custos: ausência de `conftest.py` (cada teste reconstrói fixtures — confirmado, 15/16 testes abrem `:memory:` próprio), conexões SQLite sem context manager, `print()` em vez de `logging` (já reconhecido em [[Resposta ao audit tecnico]] como P03/P06/P07, baixo impacto).

**Melhorias arquiteturais sugeridas.** (1) extrair os termos de λ (altitude/calor/estilo) para um módulo `factors.py` consumido pelo `predictor`, deixando os "gates" só no harness — quebra o ciclo; (2) evoluir `db.SCHEMA` para o schema-alvo (venues/context) + índices compostos; (3) `conftest.py` com fixtures compartilhadas; (4) uma camada fina de configuração para os coeficientes (hoje espalhados em dataclasses por módulo: `PredictParams`, `EloParams`, `FeatureParams`, mais constantes-módulo como `THETA_ALT`, `SIGMA_R_REF`).

---

## 3. Modelos matemáticos

Avaliação por bloco. As **fórmulas estão aritmeticamente corretas** (reproduzi as tabelas do contrato e as execuções), mas há problemas de **modelagem** e, sobretudo, de **degenerescência prática** (aparato que existe mas não varia).

### 3.1 Elo (`elo_engine.py`) — sólido, mas `σ_R` é degenerado
`we(dr)=1/(1+10^(−dr/400))`, `dr=R_A−R_B+mando`, `K` por competição, `G` por margem (anti-saturação). Tudo conforme [[Elo]]/contrato §3.1 e **[verificado]** (`we(100)≈0,640`). O `K` por palavra-chave é frágil mas a ordem está certa ("qualif" antes de "world cup", evitando que eliminatórias virem K=60).

**Problema central (Alta).** `sigma_r(n) = floor + (prov−floor)·e^(−n/τ)` com `floor=40, prov=200, τ=20`. **`σ_R` é função só do nº de jogos** — não mede volatilidade real de resultados. Para qualquer seleção com ~80+ jogos, `σ_R → 40` (o piso). Como as 48 seleções da Copa são todas estabelecidas, **todas terão `σ_R ≈ 40`**. **[verificado]** no `predict_match`: Brasil(σ40)×Argentina(σ40), México(σ40)×Alemanha(σ40), Espanha(σ40)×Cabo Verde(σ40) → `σ_dr = 80` nos três. Consequência: a propagação, a banda e a maturidade da confiança **não diferenciam** confrontos de elite. Um time consistente e um errático com o mesmo nº de jogos recebem a mesma incerteza. É a maior fragilidade de modelagem do sistema — o aparato de incerteza é teórico, não operante onde importa.

### 3.2 Poisson (`predictor.poisson_reads`) — correto, mas independente
`M[i][j]=Pois(i;λ_A)·Pois(j;λ_B)`, 0..10; V/E/D/over/BTTS/top-5 da matriz. **[verificado]** coerente. Duas observações:
- *Independência.* Assume gols independentes; ignora a correlação negativa real (poucos jogos 0×0/1×1 a mais). Isso **enviesa BTTS/under** — exatamente o que a Dixon-Coles corrigiria (reconhecido, no backlog).
- *"Resíduo na borda".* A doc ([[Poisson]]) diz "resíduo na borda", mas o código **trunca** em 10 sem redistribuir a massa. **[verificado]**: V+E+D = 0,99999114 (massa truncada ~9e-6). Numericamente irrelevante (renormaliza depois), mas é doc≠código.

### 3.3 Curva de empate C1 (`predictor.draw_prob`) — proxy proibido (Alta)
O contrato especifica `P_E(dr)` como **tabela empírica do martj42 por faixa de |dr|**, truncada por amostra ([[camada1-apendice-formas-v5]] §3). O código implementa `draw_prob = draw_base·e^(−|dr|/draw_scale)` (`draw_base=0,27`, `draw_scale=510`) — um **proxy fechado**. A auditoria v5 é categórica: *"Esse proxy NÃO é a C1 (…) **Não implementar o proxy no lugar da curva empírica**"* ([[camada1-revisao-v5]] §1, V6). **[verificado]**: `draw_prob(0)=0,27`, `draw_prob(300)=0,1499`. Como P(E) e, por decomposição (`pv=we−pe/2`, `pd=1−pv−pe`), P(V)/P(D) da leitura Elo-direto dependem disso, **toda previsão** carrega a curva proxy. O cap de coerência mascara o efeito nos extremos, mas o miolo do empate é um chute paramétrico, não a curva empírica prometida. (Coincide com o P08 da auditoria anterior, ainda no backlog.)

### 3.4 Saldo/Total `f(dr)`, `g(dr)` e o piso de λ (`predictor.lambdas`)
`GD=θ·dr/100` (θ=0,45), `T_m=(T_base+κ·|dr|/100)·estilo·heat` (T_base=2,6, κ=0,10). Formas lineares (placeholders do apêndice). **[verificado]** reproduzem a tabela do contrato.
- *Quebra no tail (Média-Baixa).* A forma linear faz `λ_B=(T_m−GD)/2` **ficar negativo** a partir de `dr≈650–740`. **[verificado]**: em dr=900, `λ_B` iria a −0,275; o piso (D-22) o trava em 0,15 **conservando T_m** (λ_A+λ_B=3,5 exato). O conserva-total funciona, mas a forma linear é **fisicamente inválida** no tail e o piso está fazendo trabalho de modelagem. Para confrontos desiguais da Copa (ex.: dr≈500–600) o modelo opera perto da borda de validade. A forma **saturante** (`tanh`), já especificada no apêndice, resolveria — segue não-adotada.

### 3.5 Incerteza e propagação (`features_pit` + `predictor.elo_direct_read`)
A propagação determinística por estratos de igual probabilidade é elegante e **reprodutível** (sem RNG). **[verificado]**: encolhe o favorito (Jensen) e mantém P∈[0,1] e soma 1 em todo dr∈[−900,900]. **Mas** é alimentada por σ degenerado (3.1) e por um `σ_ajuste` **incompleto**: o contrato (§3.12) define 5 termos (desfalque-dúvida, meio-tier, desvio de forma, fuso, descanso); o código implementa **só** `c·desvio_forma` (`features_pit`, `sigma_ajuste_c=80`). Além disso, **`banda_mando` nunca é somada** a `σ_dr` (nem em `features_pit`, nem em `predict_match`) — ou seja, a incerteza extra do anfitrião (E2, uma manchete da v5) **não é propagada**.

### 3.6 Ensemble (`predictor.predict`) — diversidade fictícia no backtest
Pesos sem-odds `0,56 Poisson / 0,44 Elo`. No histórico **não há perna de mercado**. Como Poisson e Elo-direto **derivam do mesmo Elo**, o ensemble backtestado são **duas leituras correlacionadas da mesma fonte** — a própria doc admite que "a diversidade real vem do mercado" ([[Ensemble]], contrato §3.8). Os pesos **com odds** (0,45/0,35/0,20) nunca foram validados (não há odds históricas — [[camada2-planejamento-v1]] §2.1). Logo a combinação de modelos, central no design, é hoje **cosmética** na validação.

### 3.7 Altitude (`altitude.py`) — maior alavanca, menos validada para 2026 (Média; Alta p/ Copa)
`GD_alt=θ_alt·(pen_B−pen_A)/1000`, `pen=max(0,alt_sede−alt_casa)`, θ_alt=0,5 (McSharry, CONMEBOL). **[verificado]** sinal e magnitude corretos; o portão real dá **+0,0491 IC[+0,0280,+0,0697] em 554 jogos** (reproduz [[Backtest baseline (resultados)]]/D-18 exatamente). Ressalvas:
- *Magnitude enorme e frágil.* **[verificado]** México×Alemanha em Cidade do México: `GD_alt=+1,12`, invertendo o favoritismo (México 48% vs Alemanha 28%) apesar de Elo menor. Um único termo desloca λ ~0,56 de cada lado. θ=0,5 é **extrapolado da CONMEBOL** para a CONCACAF (P11, aberto).
- *Mitigante.* **[verificado]**: dos 554 jogos do portão, **38% são em sedes do México** (Cidade do México 193 + Puebla/Toluca) e 62% CONMEBOL — ou seja, não é puramente CONMEBOL; há evidência de sede mexicana. Mas θ é único, não separado por confederação.
- *Cobertura de dados para 2026 (grave).* `CITY_ALT`/`TEAM_HOME_ALT` são dicionários **hardcoded** minúsculos (4 seleções adaptadas). **[verificado]**: das 16 sedes de 2026, **só "Mexico City" está em `CITY_ALT`**. **Guadalajara (1.566 m)** — que o próprio contrato cita como material (`GD_alt≈−0,78`) — e Monterrey **não estão**. Logo a altitude **não dispara** em jogos de Guadalajara em 2026, e qualquer variação de grafia da cidade no martj42 a desliga silenciosamente. Há também risco de **dupla contagem com o mando** em jogos do México em casa (B2, declarado) — `+1,12` de altitude **e** `+40` de mando se somam.

### 3.8 Calor e Estilo — corretamente rejeitados pelo portão
`heat.py` (E3) e `estilo.py` foram **construídos e rejeitados** pelo portão. **[verificado]** reproduz exatamente: estilo n=445, BTTS 50,5%→47,0% (real 46,7%), ΔBrier −0,0008 IC[−0,0083,+0,0069] cruza zero → não adotar (D-23). Isto é **um ponto forte**: a disciplina funcionou e descartou features plausíveis sem evidência por jogo. (Nota: o portão do estilo usa um único cutoff treino/teste, não PIT por jogo como o `features_pit` — aceitável para um candidato rejeitado, mas registre a diferença de rigor.)

### 3.9 Confiança (`predict_match.confidence`) — desenho bom, insumo inerte
`conf = 100·reliab(p_max)·maturidade(σ_R)`, com `reliab` isotônica do backtest (`calibrate_confidence`, PAV correto) e `maturidade=1−min(0,5, σ_R/200)`. Desenho sólido e calibrado nos dados. Porém, como `σ_R≈40` para todos (3.1), `maturidade≈0,8` quase sempre → a confiança vira **essencialmente uma função de p_max**. Útil, mas o componente "maturidade do rating" é quase constante na prática.

### Modelos mais robustos (o que seria superior, e por quê)
Para um sistema de previsão sério de seleções, na ordem de custo-benefício:
1. **Dixon-Coles** (correção de τ para placares baixos) — corrige o viés de BTTS/under da independência Poisson **e** dá um gerador de λ direcional; já está no roadmap, deveria subir de prioridade.
2. **Modelo bivariado/`bivariate Poisson` ou Weibull-count** — captura correlação de gols sem o hack do piso.
3. **Regressão de força ataque/defesa (Maher/Karlis-Ntzoufras)** como **prior não-Elo** — daria diversidade **real** ao ensemble (hoje fictícia, 3.6).
4. **σ_R baseado em dados** (erro-padrão do ajuste de Elo, ou um esquema tipo **Glicko/TrueSkill** cujo RD/σ varia com regularidade e recência) — resolveria a degenerescência de 3.1 e tornaria banda/confiança informativas.
5. **Calibração isotônica/Platt do 1X2** por faixa (especialmente para corrigir a superconfiança em 0,8–0,9, §5) — barato e mede-se direto.

O projeto **rejeita ML/bayes hierárquico por auditabilidade** (D-02), o que é uma decisão legítima; nenhuma das sugestões acima exige ML opaco — todas são paramétricas e auditáveis.

---

## 4. Fontes de dados

**Inventário** ([[Fontes gratuitas]], [[camada2-planejamento-v1]] §2.1). Fonte primária: **martj42/international_results** (resultados 1872–2026). Complementares declaradas: fixturedownload (calendário), StatsBomb (xG/bola parada, histórico parcial), Open-Meteo (clima/altitude), Wikidata (elevação/técnico), eloratings.net (benchmark), Kalshi/Polymarket (mercado prospectivo).

**O que está realmente em uso.** **[verificado]**: só o **martj42** é ingerido pelo código (`ingest.py`) — 49.423 jogos, 336 "seleções". `climatology.json` (840 cidades, Open-Meteo) existe para o módulo de calor (rejeitado). **Nenhuma** das demais fontes está integrada: não há fixturedownload, StatsBomb, Wikidata nem odds no pipeline. A altitude usa **tabelas hardcoded** no código, não Open-Meteo (3.7).

**Qualidade / confiabilidade / cobertura.**
- *martj42* é uma base reconhecida e ampla, mas é **resultado bruto** (sem xG, sem escalações, sem minuto de gol). **[verificado]**: inclui entidades **extintas/não-FIFA** ("Yugoslavia", "Biafra", "Barawa") entre as 336 — ruído para benchmark e busca de nomes (o `predict_match` chega a sugerir "Biafra"/"Bahrain" para "Brasil", embora "Brazil" venha primeiro via `difflib`).
- *Cobertura temporal* vai a 1872. O Elo é reconstruído desde então a partir de 1500; jogos do século XIX/início do XX entram na métrica "todos os jogos" e **inflam** a vantagem sobre o uniforme (goleadas fáceis). Por isso o recorte honesto é o de **torneios** (n=2.241).
- *Atualização* é por snapshot manual (D-03) — coerente com "roda local", mas exige re-rodar o pipeline antes de cada rodada da Copa; não há automação.
- *Benchmark de Elo* contra eloratings.net é **manual e nunca automatizado**. **[verificado]**: o top do Elo próprio tem artefatos — Argentina 2210, Espanha 2189, **Colômbia 2068 acima do Brasil 2061**, valores absolutos ~70 pts acima do eloratings real (~2140 p/ Argentina). O invariante "±25 nas top-30" do plano não é medido em código.

**Informações faltantes que mais melhorariam a precisão** (em ordem):
1. **Escalações/desfalques estruturados** — hoje só via JSON manual (Camada 3, não implementada). É o maior fator de curto prazo num jogo.
2. **xG histórico (StatsBomb)** — prior de estilo muito menos ruidoso que gols brutos; também viabiliza o piso de bola parada (E4).
3. **Odds/mercado de fechamento** — sem elas o ensemble não tem diversidade real **e** não há comparador de mercado no aceite.
4. **Elo público reconstruído** — comparador mínimo de validação (§7), hoje ausente.
5. **Elevação por sede via Open-Meteo + altitude-de-casa das 48** — substituiria os dicionários hardcoded e cobriria Guadalajara/Monterrey.
6. **Sede/horário por jogo** (para calor/fuso) e **minuto do gol** (`goalscorers.csv`, para "tempo do gol").

---

## 5. Qualidade do código

Boa no geral; nível de um projeto bem cuidado. Pontos por critério:

- **Organização/legibilidade:** alta. Módulos curtos, docstrings que citam o contrato, nomes consistentes, PT-BR coerente. `from __future__ import annotations` e type hints parciais.
- **Modularização:** boa (núcleo puro × I/O; contratos por tabela).
- **Boas práticas / repetição:** SQL parametrizado (sem injeção); seeds fixas. **Repetições:** P(V/E/D) é computado duas vezes (`poisson_reads` e de novo em `markets`); a leitura Elo-direto é reimplementada em `calibrate._elo_read` separada de `predictor.elo_direct_read` (risco de divergirem). Sem `conftest.py` → fixtures duplicadas em 15 testes.
- **Complexidade:** baixa, exceto `features_pit.team_form` (consulta correlacionada cara, §2 escalabilidade).
- **Tratamento de erros:** adequado nas bordas (arquivos ausentes, time não encontrado com sugestão por `difflib` — corrige o P12). Conexões SQLite **sem context manager** (P03, aberto); sem `logging` (usa `print`, P07).
- **Tipagem:** parcial; dataclasses `frozen=True` para parâmetros (bom). Sem checagem estática (mypy) no projeto.
- **Performance:** boa no bootstrap (vetorizado numpy, D-15); **ruim** em `features_pit` sem índices compostos (§2). Propagação por 200 estratos × 49k jogos roda em tempo aceitável **[verificado]**.
- **Segurança:** superfície mínima (local, sem rede no cálculo). `web.py` só escuta em 127.0.0.1, SQL parametrizado, sem template injection óbvia. `ingest --download` e `heat --build-climatology` usam `requests` (rede) — isolados e opcionais, rodam na máquina do usuário.
- **Testabilidade:** alta — 86 testes, sem rede, determinísticos. **[verificado] 86/86 passam.** Porém os testes cobrem sobretudo **invariantes** (anti look-ahead, coerência [0,1], lógica do portão) e **reprodução das próprias fórmulas** (o teste "reproduz IRN×NZL" usa as mesmas contas → algo circular). **Nenhum teste detecta** a divergência proxy-vs-curva-empírica (3.3) nem a ausência de `banda_mando` (3.5), porque ambos são "comportamento implementado", não bug local.

---

## 6. Regras de negócio

Verifiquei se o que está codificado representa o domínio (futebol de seleções / Copa):

- **Mando = 0 em sede neutra; anfitrião com banda.** Conceito correto e bem fundamentado (jogos-fantasma COVID, [[Mando de campo]]). **Mas:** (a) `H_host2026=+40` **nunca passou pelo portão** (P04, aberto — não há conjunto de calibração de Copa em co-anfitrião); (b) a **banda de mando não é propagada** em σ_dr (3.5); (c) no `predict_match`, o mando é argumento manual (`--mando`), o que é razoável, mas sem `banda_mando` a incerteza do anfitrião some.
- **Desfalques direcionais** (ataque corta λ próprio; defesa/goleiro via dr) — regra **correta e diferenciada** no contrato ([[Desfalques direcionais]]), mas **não implementada no código** (é Camada 3, JSON manual). Hoje o sistema **não** considera lesões/suspensões — limitação grande para previsão real de jogo.
- **K-factor por competição** — heurística por palavra-chave plausível; risco de torneios novos/renomeados caírem no default 40 (ex.: "UEFA Nations League" ok; "CONCACAF Nations League" também contém "nations league"→30, o que pode não ser desejado para um jogo de eliminatória continental). Aceitável, mas frágil.
- **Mata-mata / prorrogação / pênaltis** — o contrato trata avanço como `P(V)+P(E)·(0,5+ε)`, mas **o código não tem lógica de mata-mata** (só 1X2 de tempo normal). Para a fase eliminatória da Copa isso é uma lacuna funcional.
- **"Favorito primeiro" (time_a = favorito)** — convenção do repo; o código não impõe (aceita qualquer ordem), apenas a saída assume dr>0 favorece A. Sem erro, mas pode confundir.
- **Registro imutável** — a regra ([[Registro de previsoes]]) é correta e essencial; ver §7 sobre a execução (registro é **manual**, não gerado pelo código).

---

## 7. Problemas encontrados

Severidade: **Crítica** (compromete a validade do que o sistema afirma) · **Alta** · **Média** · **Baixa**. Inclui problemas técnicos, matemáticos e conceituais.

| # | Problema | Gravidade | Onde | Impacto | Como corrigir |
|---|---|---|---|---|---|
| 1 | Validação só compara com o **uniforme**; não há comparação contra **Elo público / mercado**, exigida como critério de aceite | **Crítica** | `backtest_harness.py` (só `UNIFORM`; `compare()` é versão×versão); [[camada2-planejamento-v1]] §5.1; [[Backtest baseline (resultados)]] "Não comparado vs Elo-público" | Bater o uniforme não prova competitividade; o invariante de aceite "≈ Elo público" está **não cumprido**. Risco de falsa sensação de validação | Implementar baseline Elo (usar `we_home` de `match_ratings` já existente!) e, onde houver odds, o mercado; reportar ΔBrier pareado com IC vs Elo, não só vs uniforme |
| 2 | **`σ_R` degenerado**: função só de nº de jogos → ~40 para toda seleção estabelecida; `σ_dr` quase constante (=80) entre elites | **Alta** | `elo_engine.sigma_r`; [verificado] em `predict_match` | Banda, propagação e maturidade da confiança **não diferenciam** confrontos da Copa; a "incerteza" central é inerte | Estimar σ a partir de dados (erro do ajuste de Elo) ou migrar p/ Glicko/TrueSkill (RD varia com regularidade/recência) |
| 3 | **Curva de empate empírica (C1) não implementada**; roda o *proxy* fechado que a auditoria v5 proibiu | **Alta** | `predictor.draw_prob`; contra [[camada1-revisao-v5]] §1 V6 e [[camada1-apendice-formas-v5]] §3; = P08 anterior | P(E)/P(V)/P(D) da leitura Elo-direto saem de um chute paramétrico, não da curva empírica do contrato | Construir `P_E(dr)` por faixa de \|dr\| do martj42 (point-in-time) e usá-la com o cap; ou re-rotular oficialmente o contrato para assumir o proxy |
| 4 | **Mercados over/BTTS quase sem discriminação** + viés de gols não corrigido | **Média** | `predictor.markets`; [verificado] over sd=0,031; BTTS Brier≈0,25 (≈sem skill); `calibrate_total` mantém T_base=2,6 | Mercados da UI são "calibrados na média" mas pouco informativos; over +7pp / BTTS +3,8pp em torneios recentes (n=445) **não** corrigidos | Dixon-Coles (correlação) + estilo/ataque-defesa que passem no portão; investigar não-estacionariedade de gols por era (T_base global não cobre) |
| 5 | **Altitude: cobertura de dados incompleta para 2026** (só Cidade do México; sem Guadalajara/Monterrey) e θ hardcoded/extrapolado | **Média** (Alta p/ Copa) | `altitude.CITY_ALT/TEAM_HOME_ALT`; [verificado] | Em 2026 a altitude **não dispara** em Guadalajara (efeito material declarado); onde dispara, é a maior alavanca e a menos validada p/ CONCACAF; risco de dupla contagem com mando | Carregar elevação via Open-Meteo Elevation; cobrir as 16 sedes e as 48 altitudes-de-casa; testar θ separado p/ CONCACAF; calibrar junto com mando (B2) |
| 6 | **`σ_ajuste` parcial e `banda_mando` ausente** em σ_dr | **Média** | `features_pit` (só `c·desvio_forma`); `predict_match` (sem banda_mando) | A incerteza propagada ignora desfalques/fuso/descanso e a banda do anfitrião — contradiz o contrato §3.12/E2 | Implementar os termos faltantes quando os dados existirem; somar `banda_mando²` quando mando≠0 |
| 7 | **Teste de cobertura de banda é trivial** (freq agregada na banda média), não mede cobertura nominal 68% | **Média** | `report.band_coverage` (`obs_in_mean_band`) | O invariante "banda com cobertura nominal / σ_dr calibrado isoladamente" ([[camada2-planejamento-v1]] §5.4–5.5) **não é testado de fato** | Medir fração de jogos cujo realizado cai na banda por faixa de p_v; teste de calibração de σ_dr por estrato |
| 8 | **Superconfiança em favoritos fortes** (faixa 0,8–0,9) | **Média** | [verificado] reliability: prev 0,85 → obs 0,74 (n=86) | Favoritos da Copa vivem nessa faixa; probabilidades altas demais | Recalibração isotônica/Platt do 1X2 por faixa; ou forma saturante no tail |
| 9 | **Forma linear de GD inválida no tail** (λ_B<0 antes do piso) | **Média-Baixa** | `predictor.lambdas`/`gd_of`; [verificado] dr≳650 | Em confrontos muito desiguais o piso "salva" uma forma fisicamente errada; saída sensível ao piso, não ao modelo | Adotar `f_sat=GD_max·tanh(dr/dr_escala)` (já especificada no apêndice), decidida no backtest |
| 10 | **Registro de previsões é manual; sem validação prospectiva fechada** | **Média** | `registro-previsoes.csv` (linhas `v*-manual`); col. "Resultado" vazia em [[06 - Analises]] | As 9 previsões registradas foram feitas à mão com inputs ≠ do código (ex.: Elo do Irã 1640 manual); nenhuma tem resultado preenchido → **zero** validação prospectiva real | Gerar o registro pelo `predict_match` (carimba versão/hash) e preencher resultados pós-jogo; medir Brier prospectivo |
| 11 | **Schema implementado é subconjunto do desenhado** (sem venues/context/statsbomb/odds) | **Média** | `db.SCHEMA` vs [[Esquema SQLite]] | Bloqueia E4/E5/E6/xG/odds — a evolução planejada não "encaixa" sem migração | Evoluir o schema para o alvo + índices compostos antes da Camada 3+ |
| 12 | **Ensemble sem diversidade real no backtest** (Poisson+Elo do mesmo Elo; sem mercado) | **Média** | `predictor.predict`; [[Ensemble]] admite | A "combinação de modelos" validada é cosmética; pesos com-odds (0,45/0,35/0,20) nunca testados | Adicionar membro de prior não-Elo (ataque/defesa/xG) e/ou mercado; revalidar pesos |
| 13 | **Sem lógica de mata-mata/prorrogação/pênaltis** | **Média** | ausente no código (contrato §3.2 prevê) | Fase eliminatória da Copa não é modelada (só 1X2 de tempo normal) | Implementar avanço `P(V)+P(E)·(0,5+ε·sinal(dr))` |
| 14 | **Benchmark de Elo não automatizado; ratings com artefatos** | **Baixa-Média** | `elo_engine.main` (só imprime); [verificado] Colômbia>Brasil, valores inflados | Não há checagem de sanidade reprodutível; ratings absolutos divergem do eloratings | Script de comparação vs snapshot eloratings; considerar regularização/recência |
| 15 | **Qualidade: sem `conftest.py`, conexões sem context manager, `print` vs `logging`, código P(V/E/D) duplicado** | **Baixa** | `tests/*`, `db.connect`, vários `main`, `predictor.markets` | Manutenção/robustez; risco de fixtures e leituras divergirem | Faxina já reconhecida (P03/P06/P07); centralizar a leitura Elo-direto |
| 16 | **Dependências não pinadas** (apesar de TECH_STACK dizer "versões pinadas") | **Baixa** | `requirements.txt` (usa `>=`) | Reprodutibilidade frágil entre máquinas/tempo | Pinar versões exatas (`==`) ou usar lock |
| 17 | **Doc inconsistente** (73 vs 86 testes; [[contexto-handoff]] diz "sem código/sem backtest", já falso; comentário `# .../codigo`) | **Baixa** | `scm_analytics/README.md`, `CLAUDE.md`, `ingest.py` | Confusão para novos leitores/agentes | Reconciliar contagens e marcar handoff como histórico |
| 18 | **`natural_key` sem cidade**; jogos repetidos no mesmo dia/torneio podem colidir | **Baixa** | `ingest.load_results` | Risco teórico de perder um jogo (raro) | Incluir cidade/ordem no `natural_key` se necessário |

---

## 8. Melhorias (priorizadas por impacto)

**Prioridade 1 — corrigem a validade ou destravam a evolução:**
1. **Comparar contra Elo público (e mercado quando houver)** no harness. Custo baixo (o `we_home` pré-jogo já está em `match_ratings`); impacto altíssimo: é o que separa "tem algum sinal" de "é competitivo". (Problema #1)
2. **σ baseado em dados** (erro do ajuste de Elo ou Glicko/TrueSkill). Destrava banda/confiança/propagação — hoje inertes. (Problema #2)
3. **Implementar a curva de empate empírica C1** (ou re-rotular o contrato). Tira o miolo do empate de um proxy proibido. (Problema #3)
4. **Cobrir dados de altitude das 16 sedes + 48 seleções via Open-Meteo** e calibrar mando×altitude juntos. Sem isso, a maior alavanca do modelo está cega para metade das sedes altas de 2026. (Problema #5)

**Prioridade 2 — precisão e robustez do modelo:**
5. **Dixon-Coles** (correlação de gols) — corrige BTTS/under e dá λ direcional. (Problemas #4, #12)
6. **Forma saturante de GD/T_m** no tail, decidida no backtest. (Problema #9)
7. **Recalibração isotônica do 1X2** (superconfiança 0,8–0,9). (Problema #8)
8. **Membro de prior não-Elo no ensemble** (ataque/defesa ou xG) — diversidade real. (Problema #12)
9. **Teste de cobertura de banda e de σ_dr** de verdade. (Problema #7)

**Prioridade 3 — infraestrutura e dados:**
10. **Evoluir o schema** (venues/context/statsbomb/odds) + **índices compostos**. (Problemas #11, performance)
11. **Camada 3**: desfalques/escalações via JSON → δ_ata e σ. (Problema em §6)
12. **Lógica de mata-mata** (avanço com ε). (Problema #13)
13. **Registro prospectivo gerado pelo código** + preenchimento de resultados → primeiro Brier prospectivo real. (Problema #10)

**Prioridade 4 — qualidade/manutenção:** `conftest.py`, context managers, `logging`, pinar dependências, automatizar o benchmark de Elo, reconciliar a documentação. (Problemas #14–#18)

> **Sobre estatística:** a melhoria de maior retorno **não** é adicionar fatores (a v5 já tem fatores demais para a amostra — o próprio projeto reconhece). É **fortalecer o baseline e a validação**: comparador real, σ informativo, curva de empate honesta, Dixon-Coles. "Mais variáveis" sem isso só aumenta graus de liberdade contra amostras pequenas (o risco nº 1 declarado em [[camada1-planejamento-v5]] §16).

---

## 9. Funcionalidades futuras (com justificativa)

Pensando em previsão/análise da Copa 2026:

1. **Simulação de Monte Carlo do torneio** (probabilidade de avançar do grupo, chegar à final, ser campeão). É o **maior valor para o usuário** e usa o motor que já existe (amostrar resultados → simular o bracket). Já citado no backlog como Camada 5; deveria ser a próxima grande entrega de produto. *Justificativa:* transforma previsões de jogo em insight de torneio, que é o que interessa numa Copa.
2. **Comparador de mercado ao vivo** (Kalshi/Polymarket por captura manual com timestamp) na interface — mostra onde o modelo concorda/diverge do consenso. *Justificativa:* o próprio projeto define o mercado como benchmark; expor a divergência é honesto e informativo.
3. **Cenários de classificação determinísticos** ("quem precisa de quê na última rodada") + flag de jogo-morto. *Justificativa:* captura motivação/rotação sem fingir prever o imprevisível (F8 de [[camada1-lacunas]]).
4. **Explicador de previsão** ("por que este número"): decompor o dr em Elo/forma/altitude/mando e mostrar a sensibilidade. *Justificativa:* auditabilidade é valor central do projeto; expô-la ao usuário a concretiza.
5. **Backtest específico de 2018/2022** com comparação a supercomputadores públicos (Opta) como sanidade externa. *Justificativa:* dá um teto de comparação realista (não o uniforme).
6. **Dixon-Coles + mercados de placar exato calibrados** e **"tempo do gol"** (quando ingerir `goalscorers.csv`). *Justificativa:* completa a oferta de mercados com base correlacionada.
7. **Atualização agendada do snapshot** (script + agendador) antes de cada rodada. *Justificativa:* operacionaliza o uso na Copa sem virar serviço online.

---

## 10. Roadmap (ordem de prioridade)

**Fase 0 — Higiene de validação (antes de confiar em qualquer número):**
- Implementar **comparador Elo/mercado** no harness (#1).
- Implementar **testes reais de cobertura de banda e σ_dr** (#7).
- *Resultado:* saber se o modelo realmente bate algo além do trivial. **Sem isto, o resto é decoração** (eco do próprio [[camada2-planejamento-v1]]).

**Fase 1 — Corrigir o núcleo estatístico:**
- **σ informativo** (#2) → torna banda/confiança úteis.
- **Curva de empate C1** real (#3).
- **Cobertura de altitude para 2026** + mando×altitude (#5).
- **Forma saturante** e **recalibração isotônica** (#9, #8).

**Fase 2 — Mais precisão de modelo:**
- **Dixon-Coles** + membro de prior não-Elo no ensemble (#4, #12).
- **Camada 3** (desfalques/escalações) — maior fator de jogo a jogo (#6, §6).
- **Lógica de mata-mata** (#13).

**Fase 3 — Produto/valor:**
- **Monte Carlo do torneio** (campeão/avanço) — maior valor ao usuário.
- **Comparador de mercado** + **explicador** na interface.
- **Registro prospectivo automatizado** e medição de Brier real na Copa (#10).

**Fase 4 — Infra/manutenção (contínuo):**
- Evoluir schema + índices (#11), faxina de código (#15), pinagem (#16), doc (#17), benchmark de Elo automatizado (#14).

**Pode esperar:** afinação fina de pesos do ensemble (só com ≥30 jogos), xG ao vivo (sem fonte), árbitro individual (lacuna declarada) — todos corretamente despriorizados pelo projeto.

---

## 11. Conclusão

**Pontos fortes (com justificativa técnica).**
- **Disciplina de processo rara:** contrato congelado, ADRs, múltiplas rodadas de auditoria, fatores ancorados em literatura. A rastreabilidade nota→fórmula→código é exemplar.
- **Portão estatístico que realmente barra:** o IC-bootstrap-pareado-que-não-cruza-zero é implementado corretamente (`backtest_harness.gate`) e **[verificado]** reproduz a rejeição de calor/estilo/calibração e a adoção de altitude. Rejeitar features plausíveis por falta de evidência por jogo é honestidade que quase nenhum projeto pratica.
- **Point-in-time levado a sério:** rating pré-jogo persistido, features só com passado, teste anti look-ahead dedicado. **[verificado]** o pipeline reproduz os números documentados (Brier todos 0,5375; torneios 0,5598; altitude +0,0491).
- **Engenharia limpa, local, reprodutível, R$ 0**, com 86 testes verdes e coerência [0,1] por construção.

**Pontos fracos (com justificativa técnica).**
- **A validação responde à pergunta errada** (bate o uniforme, não o Elo/mercado) — o critério de aceite mais importante do próprio projeto não está implementado (#1).
- **O aparato de incerteza está inerte** onde importa: σ_R degenerado torna banda/confiança quase constantes entre elites (#2).
- **Divergências contrato↔código** em peças centrais: curva de empate é o proxy proibido (#3); σ_ajuste e banda_mando incompletos (#6); schema é subconjunto (#11).
- **Lacunas de domínio para a Copa:** sem desfalques, sem mata-mata, altitude cega para Guadalajara/Monterrey, mercados de baixa discriminação (#4, #5, #13, §6).
- **Zero validação prospectiva fechada:** o registro é manual e sem resultados (#10).

**O que mais chamou a atenção.** O **contraste entre a qualidade do planejamento e a inércia prática de partes do modelo**. O projeto documenta com rigor invejável uma "propagação de incerteza" e uma "curva de empate empírica" que, no código, viraram respectivamente um σ quase-constante e um proxy fechado que a própria auditoria interna proibiu. A sofisticação está mais no papel do que na execução — e, paradoxalmente, o que o código faz bem (baseline Elo→Poisson honesto e calibrado) é mais simples e mais sólido do que o discurso sugere. O segundo destaque positivo é o portão: é genuinamente bom e já evitou três falsos avanços.

**Nível técnico.** Engenharia e processo: **alto**. Modelagem estatística efetivamente entregue: **médio** (muito aparato não-operante ou não-validado; baseline correto mas com baseline de comparação trivial). É claramente trabalho de alguém competente e cuidadoso, com forte cultura de honestidade metodológica — limitado pela distância entre contrato e implementação e por um critério de validação fraco.

**Preparo para análises da Copa 2026.** Como **ferramenta de estudo** que produz probabilidades 1X2 razoáveis e bem calibradas na média, com confiança honesta: **utilizável, com ressalvas**. Como **sistema de previsão sério da Copa**: **ainda não pronto**. Faltam, em ordem: (1) provar que bate um Elo/mercado, não só o uniforme; (2) σ que varie e banda que signifique algo; (3) cobrir desfalques e a fase de mata-mata; (4) corrigir a altitude para as sedes reais de 2026; (5) fechar o laço de validação prospectiva. A **arquitetura suporta** essa evolução (estágios desacoplados, contrato versionado, portão), mas os **modelos atuais não a sustentam sem os itens da Fase 0–1** do roadmap. A filosofia "congela o contrato, mede com portão, nunca afirma certezas" é a base certa — o que falta é fazer o código honrar o que o contrato promete e medir contra um adversário à altura.

---

### Anexo — verificações empíricas executadas (2026-06-18)

| Verificação | Resultado | Confere a doc? |
|---|---|---|
| `pytest -q` | **86 passed** | sim (86) |
| Ingestão martj42 | 49.423 jogos, 336 seleções | sim (49.423) |
| Backtest todos os jogos | Brier 0,5375; ganho +0,1292 IC[+0,1257,+0,1327] | sim (0,538; +0,129) |
| Backtest torneios (n=2.241) | Brier 0,5598; ECE 0,0248; ganho +0,1069 IC[+0,0913,+0,1227] | ~ (doc v0.1: 0,562/0,023; diferença = drift v0.2.1) |
| Portão altitude (n=554) | +0,0491 IC[+0,0280,+0,0697] → manter | sim (exato, D-18) |
| Portão estilo (n=445) | BTTS 50,5→47,0 (real 46,7); ΔBrier −0,0008 IC[−0,0083,+0,0069] → rejeitar | sim (exato, D-23) |
| `calibrate_total` (n=445) | mantém T_base=2,60; over +7,0pp / BTTS +3,8pp não corrigidos | candidato não-adotado |
| Coerência P∈[0,1], soma 1 | OK em dr∈[−900,900]; mín. componente 0,02 | sim |
| Piso conserva T_m (D-22) | λ_A+λ_B=T_m exato em dr=900/1500/2500 | sim |
| σ_dr em `predict_match` | =80 idêntico p/ BRA×ARG, MEX×ALE, ESP×CPV | achado (σ_R degenerado) |
| Curva de empate | `draw_prob` = proxy fechado (0,27 em dr=0) | diverge do contrato (C1 empírica) |
| Cobertura de sedes 2026 | só "Mexico City" em `CITY_ALT` (faltam Guadalajara/Monterrey) | achado |

---
*Auditoria externa independente — 2026-06-18. Baseada em leitura integral do vault e do código `scm_analytics/` e em execução empírica do pipeline sobre os 49.423 jogos do martj42. Sem implementação de funcionalidades. Conclusões citam arquivo/módulo; números marcados [verificado] foram reproduzidos em código. Relacionado: [[Resposta ao audit tecnico]] · [[Backtest baseline (resultados)]] · [[camada1-planejamento-v5]] · [[camada2-planejamento-v1]] · [[MODELO_FINAL]] · [[Codigo (estrutura)]].*

---

## Follow-up (2026-06-18) — correções aplicadas (Fase 0–1)

Implementadas e validadas as correções de alto impacto do núcleo (modelo **`baseline-v0.3-altitude`**, **92 testes** verdes, rebuild completo point-in-time). Ver [[Decisoes tecnicas]] D-26..D-30 e [[Backtest baseline (resultados)]].

| # | Problema | Estado | Evidência |
|---|---|---|---|
| 1 | Validação só vs uniforme | ✅ **corrigido** | `evaluate_vs_elo`: modelo **bate o Elo público** com IC>0 (all +0,0028 [+0,0023,+0,0033]; major +0,0037 [+0,0009,+0,0066]) |
| 2 | σ_R degenerado / σ_dr constante | ✅ **corrigido** | `vol_mult` + σ_ajuste real: σ_dr da porta da frente varia (BRA×ARG 63, MEX×ALE 49, KSA×NZL 75 — era 80 fixo); backtest σ_dr min 58→36 |
| 3 | Curva de empate = proxy proibido | ✅ **corrigido** | `DRAW_CURVE` empírica do martj42; proxy só como fallback; Brier melhora levemente |
| 5 | Altitude cega p/ Guadalajara | ✅ **corrigido** | Guadalajara/Zapopan + normalização de acentos; portão re-rodado +0,0490 [+0,0283,+0,0690] (n=566) |
| 7 | Teste de cobertura trivial | ✅ **corrigido** | `band_coverage_binned`: 8/10 faixas dentro; **flagra** a superconfiança em [0,8–0,9] (obs 0,74 fora de [0,84–0,92]) |
| 8 | Superconfiança em 0,8–0,9 | 🟡 **medido** (não corrigido) | agora quantificado pelo teste #7; recalibração isotônica fica p/ Fase 1 |
| 11 | Schema sem índices | ✅ **parcial** | índices compostos adicionados (perf); tabelas venues/context seguem fora |
| — | Propagação lenta | ✅ **bônus** | quantis da Normal cacheados: ~8× mais rápido, **mesma matemática** |

**Não incluído nesta rodada** (Fase 2+ do roadmap, conforme combinado): Dixon-Coles (#4/#12), mando do anfitrião no portão (P04), mata-mata (#13), Camada 3 de desfalques, registro prospectivo automatizado (#10), faxina (#15). A arquitetura e o portão suportam essas evoluções; os ganhos de validade/precisão mais críticos já estão aplicados.

### Atualização 2026-06-18 (b) — mata-mata implementado
Problema **#13 (sem lógica de mata-mata)** ✅ **corrigido**: `predictor.knockout_advance` (`avanço = P(V)+P(E)·(0,5+ε·sinal(dr))`, ε=0,03), exposto na CLI (`--mata-mata`) e na web. Releitura do 1X2 (sem bump de versão, como os mercados). **96 testes** verdes. Calibração empírica de ε (via `shootouts.csv`) fica como follow-up. Ver [[Decisoes tecnicas]] D-31.

### Atualização 2026-06-18 (c) — Simulação do torneio (Camada 5)
Entregue a **Funcionalidade Futura #1** da §9 (Monte Carlo do torneio → chance de título): `scm/simulate.py` + `dados/copa2026.json` (sorteio a preencher) + página `/simulacao`. Reusa o `knockout_advance` (#13). Σ P(campeão)=1 e Σ P(passar)=32 nos testes. **100 testes** verdes. Ver [[Decisoes tecnicas]] D-32.

**Sorteio preenchido (2026-06-18).** `copa2026.json` recebeu o **sorteio oficial dos 12 grupos** (busca web + cruzamento 100% com os 20 jogos já disputados no martj42). Simulação real (20k torneios, `baseline-v0.3-altitude`): **Argentina 18,6% · Espanha 15,0% · França 10,9% · Inglaterra 6,8% · Colômbia 5,3% · Brasil 4,9%** de título; México 3,6% (com mando de anfitrião). Insight, não previsão validada.

### Atualização 2026-06-18 (d) — chaveamento oficial + ε do mata-mata
Simulação refinada com o **chaveamento oficial da FIFA 2026** (R32 73–88 → final 104; 3os por elegibilidade do Anexo C, validado nas 495 combinações) no lugar do sorteio aleatório — caminhos reais (ex.: França semi ~34%). E `calibrate_ko.py` mede o **ε empírico** dos pênaltis (`shootouts.csv` + dr pré-jogo) — rodar na máquina do usuário. **102 testes**. D-33.
