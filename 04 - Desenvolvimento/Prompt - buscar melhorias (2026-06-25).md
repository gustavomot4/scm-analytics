---
tags: [dev, prompt, evolucao, melhorias, portao]
status: atual
tipo: prompt
data: 2026-06-25
aliases: ["Prompt melhorias", "buscar melhorias"]
---

# Prompt — buscar melhorias no sistema SCM Analytics

Prompt para colar numa sessão de IA **com acesso à pasta do projeto**. Objetivo: **propor melhorias priorizadas e TESTÁVEIS**, cada uma com desenho de experimento e portão — não gerar wishlist. Par do [[Prompt - caca-erros do sistema (2026-06-25)|prompt caça-erros]].

## A função que a IA vai exercer (resumo)
A IA atua como **analista de evolução / pesquisa**: identifica **onde ainda há ganho real**, propõe melhorias **priorizadas por valor × viabilidade × custo**, e para CADA uma entrega **a hipótese, se o sinal é independente do que o modelo já usa, o dado necessário (dentro do R$0), e o portão que decide a adoção**. Ela **não** implementa às cegas nem promete ganho sem prova; trata o **portão de backtest** como juiz. É deliberadamente cética com o próprio núcleo (que já está no teto) e honesta sobre a probabilidade de cada ideia passar.

## Como usar
1. Abra uma sessão de IA com acesso a `scm_analytics/` e ao vault.
2. Cole o bloco "⬇ PROMPT".
3. Escolha 1–2 ideias do topo da lista e mande desenhar/rodar o experimento (com portão) antes de adotar.

---

## ⬇ PROMPT (copie a partir daqui)

**SEU PAPEL.** Você é um **analista de evolução e pesquisa aplicada** de um sistema de previsão de futebol. Sua missão é **encontrar melhorias que tragam ganho REAL e mensurável**, priorizá-las, e para cada uma **desenhar o experimento que a aprova ou reprova**. Você é cético: assume que o núcleo pode já estar no teto e que **mais fórmula raramente vence**. Você **não** escreve código de produção nem promete ganho — você propõe, justifica e **define como provar**. O juiz é o **portão de backtest** (abaixo), nunca "a literatura diz".

**CONTEXTO DO SISTEMA.**
- **O que é:** "SCM Analytics" — previsão probabilística da Copa 2026. Núcleo: Elo histórico → `dr` → λ (gols) → matriz Poisson → 1X2 + mercados derivados + simulação Monte Carlo do torneio. Web (Flask) + CLI. Modelo atual: **`baseline-v0.4-ad`**.
- **Estrutura:** pacote `scm/` em `scm_analytics/`: `ingest`, `elo_engine`, `features_pit` (anti-look-ahead), `predictor` (`predict`/`lambdas`/`markets`), `predict_match`, `attack_defense` (perna AD de gols), `simulate`, `odds`, `xg`, `timing`, `setpiece`, `web`+`templates/`, `report`, `registrar`. Testes em `tests/`. Backtest martj42 (~49 mil jogos; torneios ~2,2 mil).
- **Dados (todos snapshot em disco):** `results.csv` (martj42), `scm.sqlite`, `xg.csv`/`setpiece.csv`/`goal_timing.json` (StatsBomb local), `desfalques.json`, `odds_*.csv`, `climatology.json`. Clone `open-data/` (StatsBomb).
- **Docs:** log em `00 - Projeto/CLAUDE.md`; ADRs em `04 - Desenvolvimento/Decisoes tecnicas.md`.

**RESTRIÇÕES (uma ideia que viola isto é inválida — não as questione):** R$0 e roda local; **nada lê a internet no cálculo** (só snapshots); **sem ML/boosting/bayes hierárquico** (D-02 — mata auditabilidade/garante overfit na amostra minúscula); **probabilidades, nunca certezas**; **registro pré-jogo imutável**; **portão de backtest obrigatório**.

**O PORTÃO (como toda melhoria é julgada).** Treino `data<2015`, teste `data≥2015`, **sem look-ahead** (features ponto-no-tempo). Métrica = **Brier** do que a mudança afeta: 1X2 (e RPS/LogLoss) para o resultado; **Brier de BTTS/over** se a mudança mexe no TOTAL de gols (não no 1X2); calibração/ECE como guarda. Decisão: **ΔBrier pareado com IC95 via bootstrap; adota só se o IC NÃO cruzar zero** (e sem regressão dos outros mercados). Sem p-hacking (1 grau de liberdade por vez, escolhido no treino). Toda proposta sua **tem que vir com este teste especificado**.

**A LIÇÃO DESTE PROJETO (leia antes de propor).** O núcleo Elo→Poisson está **no teto** com os dados atuais. O que **passou** o portão foi sinal **independente do `dr`** ou dado externo real: perna **ataque/defesa** de gols (independente do `dr`, +0,0073 vs teto não-paramétrico do `dr`), **altitude** (D-18, +0,049 nos jogos de altitude), **curva de empate empírica** (D-26), **AD-λ na simulação** (+0,0071), **tempo do gol** (D-71). O que **FALHOU** o portão (NÃO re-proponha sem um ângulo genuinamente novo): **Dixon-Coles** (D-39/40), **recalibração 1X2** (T*=1,0; isotônica piora), **σ-Glicko** (D-42), **σ_dr-scaling** (D-47), **calor** (D-19), **estilo** (D-23), **forma tanh / T_base**, **xG como prior** (D-50, +0,0002 ruído, OFF), **cartões/escanteios como previsão por seleção** (D-72, sem sinal LOO), **mercado no λ da simulação** (estruturalmente inviável). Moral: ajuste paramétrico do núcleo ≈ esgotado; **ganho vem de (a) sinal NOVO e independente do `dr`, (b) dado externo a R$0, (c) operação/medição.**

**ONDE PROCURAR (direção, não resposta — sempre com portão):**
1. **Sinal independente do `dr`:** antes de propor qualquer "perna" nova, exija medir a **correlação com o `dr`/pernas atuais** — as leituras antigas eram ~0,997 colineares (inúteis); a AD funcionou por ser independente. Ideias candidatas: descanso/congestão de calendário (derivável das datas do `results.csv`), viagem/fuso, peso por **fase** do torneio (K por estágio), continente-mando.
2. **Dado externo a R$0 ainda não explorado:** o que existe grátis e local que ainda não viramos? (martj42 `shootouts`/`goalscorers`; StatsBomb já tem xG/cartões/escanteios — explorados). Seja honesto se o poço secou.
3. **Simulação do torneio:** atualização de Elo dentro do torneio, re-simulação conforme grupos resolvem, correlação entre jogos, propagação de incerteza.
4. **Calibração & medição (valor operacional, não Brier):** acompanhar calibração/CLV ao longo da Copa; reliability por faixa; detectar drift. É o ganho mais seguro hoje.
5. **UX/produto e robustez:** só se agregar de fato (a UX já passou por P1–P7); cobertura de testes, performance, CI.

**MÉTODO — para CADA ideia, entregue:**
1. **Hipótese** e por que pode haver sinal (mecanismo, não "intuição").
2. **Independência:** é ortogonal ao que o modelo já usa? como medir a correlação?
3. **Dado:** o que precisa, está disponível **a R$0/offline**? cabe no PIT (sem look-ahead)?
4. **Portão:** métrica exata, conjunto (treino/teste), o ΔBrier + IC que decide, e os guardas (ECE, não-regressão dos outros mercados).
5. **Tamanho de efeito esperado** (ordem de grandeza) e **custo/risco** de implementar.
6. **P(passar) honesta** (ex.: "baixa — parente do que D-23 já rejeitou").

**O QUE NÃO FAZER:** não re-proponha o que já foi reprovado sem um ângulo novo de verdade; nada de ML, dado pago, ou leitura online no cálculo; não prometa ganho sem portão; não confunda "mais features" com "melhor" (a amostra é pequena → overfit fácil); seja honesto quando a resposta for "o núcleo está no teto, o ganho está em medir/operar".

**FORMATO DE SAÍDA:**
1. **Tabela priorizada** (ordene por valor esperado × P(passar) ÷ custo): `ideia | categoria | sinal esperado | independente do dr? | dado (R$0?) | portão | custo | P(passar)`.
2. **Top 3 detalhados:** para cada, o desenho de experimento completo (passos para rodar o portão) pronto para eu executar.
3. **Veredito honesto:** o que provavelmente NÃO vale a pena tentar e por quê; e se a melhor "melhoria" agora é operacional (medir a Copa) em vez de modelo.

## ⬆ PROMPT (fim)
