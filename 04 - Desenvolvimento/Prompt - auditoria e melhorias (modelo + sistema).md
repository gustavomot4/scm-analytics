# Prompt — Auditoria técnica orientada a MELHORIAS (modelo matemático + sistema)

> Versão refatorada do prompt de auditoria. Mudou o objetivo: não é só descrever o que existe, é **encontrar e priorizar melhorias concretas** — com **ênfase no modelo matemático** — fundamentadas em evidência e com **plano de validação** para cada uma. Cole isto para um agente/IA com acesso ao repositório.

---

## Papel e objetivo

Aja como **três especialistas ao mesmo tempo**: (1) **cientista de dados / estatístico de previsão esportiva**, (2) **arquiteto de software**, (3) **auditor técnico**. Seu objetivo **não** é só auditar nem implementar código: é **diagnosticar o estado atual e propor um plano de melhorias acionável e priorizado** para o **modelo matemático** (foco principal) e para o **sistema**, considerando que este projeto será a base de um **sistema de previsão de partidas de futebol** (Copa do Mundo).

Não implemente nada a menos que seja pedido. Mas cada proposta deve ser **concreta o bastante para implementar**: fórmula/pseudocódigo, onde mexer (arquivo:linha), e **como medir se melhorou**.

## Processo obrigatório (nesta ordem — não pule)

1. **Leia o repositório inteiro**, sem leitura superficial: `README` e toda documentação; arquitetura; **modelos matemáticos e fórmulas**; estrutura de pastas; regras de negócio; fluxo de execução de ponta a ponta; todo o código-fonte; scripts; configurações; dependências; banco de dados (se houver); APIs; fontes de dados; algoritmos de cálculo e sistema de pontuação; testes; e qualquer doc adicional (decisões/ADRs, planejamento, históricos).
2. **Reconstrua o fluxo** ingestão → processamento → modelo → saída/validação, dizendo o que cada módulo recebe e produz.
3. **VERIFIQUE, não confie na documentação.** Reproduza numericamente as fórmulas centrais e o backtest (rode o código ou reconstrua a base a partir do snapshot/fontes). Marque cada número como **[verificado]** (você reproduziu) ou **[inferido]** (só leu). Se não conseguir executar algo, **diga explicitamente** o porquê.
4. **Só depois** produza conclusões.

## Entregável (documento estruturado)

### 0. Sumário executivo (1 página)
Nível técnico geral; 3 maiores forças e 3 maiores fraquezas (com evidência); **top-5 melhorias por impacto × esforço** (a maioria deve ser do modelo); e, em 1 frase, **qual é o teto atual de acurácia e o que o levanta**.

### 1. Visão geral e fluxo
Objetivo do sistema; como funciona; fluxo principal; módulos e como se relacionam. Conciso.

### 2. Arquitetura
Organização de pastas; separação de responsabilidades; acoplamento; coesão; escalabilidade; manutenibilidade. **Pergunta central:** a arquitetura **suporta a evolução** para um preditor de partidas sério (novas fontes, recalibração, re-treino, versionamento de modelo, uso ao vivo)? Aponte melhorias arquiteturais com justificativa.

### 3. MODELO MATEMÁTICO — núcleo da análise (vá fundo aqui)
Trate esta seção como a principal. Para **cada** bloco do modelo:

- **Inventário completo:** liste TODA fórmula, métrica, coeficiente e "número mágico", com **arquivo:linha** e a **fórmula explícita** (não parafraseie — escreva a matemática).
- **Verificação numérica [verificado]:** reproduza as contas centrais; confirme se o **código bate com a documentação/contrato** (aponte divergências).
- **Correção e consistência:** as fórmulas fazem sentido? Há erro matemático, inconsistência ou unidade trocada?
- **Vieses e armadilhas estatísticas — investigue explicitamente:**
  - **Vazamento temporal (look-ahead):** as features usam só dados anteriores ao jogo? O rating/pré-jogo é *point-in-time*?
  - **Vazamento in-sample:** algum componente (curvas, tabelas, coeficientes) foi **ajustado nos mesmos dados** em que é avaliado?
  - **Calibração:** as probabilidades são calibradas (reliability/ECE)? Há super/subconfiança em alguma faixa?
  - **Regras de pontuação próprias:** usa-se **Brier / log-loss / RPS** corretamente? A avaliação tem **intervalo de confiança** (bootstrap pareado)?
  - **Baselines honestos:** o modelo é comparado contra **uniforme**, contra um **baseline forte** (Elo público, mercado, ou um *lookup* não-paramétrico) e, idealmente, contra um **previsor externo**? Ele realmente supera, com IC que não cruza zero?
  - **Incerteza:** a incerteza é modelada, **propagada** para a saída, e é **informativa** (ou degenera/satura, virando constante)?
  - **Diversidade do ensemble:** se há combinação de modelos, as pernas são **independentes** ou são leituras correlacionadas da mesma fonte (diversidade fictícia)? Meça a correlação.
  - **Comportamento no tail / bordas numéricas:** as fórmulas continuam válidas nos extremos (ex.: taxas negativas, *clamps*/pisos que passam a "fazer a modelagem")?
  - **Direção/causalidade das features:** cada ajuste move a probabilidade **no sentido certo**? (teste casos.)
  - **Overfitting:** quantos graus de liberdade vs tamanho de amostra? Risco de sobreajuste com poucos jogos?
- **Consistência produção ↔ validação:** o caminho que o usuário usa (produção) entrega **exatamente o modelo que o backtest valida**? Aponte qualquer "o que se valida ≠ o que se entrega".
- **Coeficientes:** os números são **calibrados** (ajustados e validados) ou **chutados**? Como foram/são validados?

**Modelos superiores (obrigatório, dado o foco no modelo).** Liste alternativas **concretas** mais robustas para previsão esportiva e, para **cada uma**: por que seria superior, **ganho esperado** (e em qual métrica), **custo/esforço**, **risco de overfit**, e **como validar** (desenho de backtest + IC). Considere ao menos: Dixon-Coles / Poisson bivariado; força ataque-defesa (Maher, Karlis–Ntzoufras); ratings dinâmicos (Glicko/TrueSkill/*state-space*, recência/decaimento); Skellam ou Weibull-count para o saldo; recalibração isotônica/Platt por faixa; **integração de odds de mercado** (o benchmark mais difícil); e — se a auditabilidade permitir — hierárquico bayesiano. **Respeite as restrições declaradas do projeto** (ex.: custo zero, roda local, sem ML opaco) e proponha dentro delas; se uma restrição limita demais a acurácia, diga isso explicitamente.

### 4. Fontes de dados
Qualidade, confiabilidade, cobertura, atualização e limitações de cada fonte. **O que realmente está em uso vs só declarado.** Quais dados **faltam** e quanto cada um aumentaria a precisão (ordene por impacto): ex. escalações/desfalques, xG, odds de fechamento, minuto do gol, elevação/clima por sede.

### 5. Qualidade do código
Organização, legibilidade, modularização, boas práticas, repetição, complexidade, tratamento de erros, tipagem, performance, segurança, **testabilidade**. Avalie em especial se os **testes pegam regressões de modelagem** (não só invariantes/coerência) e se há risco de testes **circulares** (que reproduzem a própria fórmula).

### 6. Regras de negócio
As regras codificadas representam o domínio (futebol de seleções / formato da Copa)? Aponte regras incorretas ou aprimoráveis, com o efeito de cada uma.

### 7. Problemas encontrados (tabela)
Colunas: **Problema · Gravidade (Baixa/Média/Alta/Crítica) · Local (arquivo:linha) · Impacto · Como corrigir · Como validar a correção**. Inclua problemas técnicos **e** matemáticos/conceituais. Marque cada um como *verificado* ou *inferido*.

### 8. Plano de melhorias priorizado (modelo + sistema) — destaque o modelo
Tabela: **Melhoria · Categoria (modelo / dados / arquitetura / performance / validação / produto) · Impacto esperado (alto/médio/baixo + métrica afetada, ex.: −X no Brier) · Esforço · Risco (inclui overfit) · Como medir o ganho**. Ordene por **impacto ÷ esforço**. Separe claramente:
- **(a) Correções e consistência** que **não** mudam o modelo validado (não precisam de portão).
- **(b) Mudanças que alteram o modelo** (λ, rating, probabilidades) e **exigem backtest com IC** antes de adotar.
Para as do modelo, descreva o experimento de validação (treino/teste, métrica, IC, critério de adoção).

### 9. Funcionalidades futuras
Sugestões com foco em previsão/análise da Copa, cada uma justificada pelo valor que agrega.

### 10. Roadmap
Fases em ordem de prioridade: o que corrigir primeiro (e por quê), o que pode esperar, o que **destrava** o quê, e o que agrega mais valor. Indique dependências.

### 11. Conclusão
Pontos fortes e fracos (com justificativa técnica); o que mais chamou atenção; nível técnico; **preparo real para análises da Copa**; e — explícito — **o teto atual de acurácia e o caminho mais curto para superá-lo**.

## Regras inegociáveis

- **Sem evidência, sem afirmação.** Cite **arquivo:linha** (ou a nota/doc) em cada conclusão.
- **Verifique numericamente** o que afirmar sobre o modelo; marque **[verificado]/[inferido]**. Se não puder rodar, diga.
- **Lacuna é lacuna:** se algo não existe ou não foi encontrado, declare — **não invente** dados, fontes ou resultados.
- **Nada de elogio sem justificativa técnica.** Seja crítico, técnico e objetivo; aponte erros, limitações e riscos.
- **Toda melhoria proposta vem com (i) impacto esperado e (ii) como validar.** Proibido "adicionar fator/feature" sem plano de medição — lembre que **mais variáveis contra amostra pequena = overfit**.
- **Distinga** o que muda o modelo validado (precisa de backtest/portão) do que é só correção/consistência.
- **Pense na evolução:** a arquitetura e os modelos suportam virar um preditor de partidas ao vivo (recalibração, re-treino, *drift*, versionamento, uso operacional)? Avalie isso.
- **Quantifique sempre que possível** (Brier, log-loss, RPS, ECE, cobertura, correlação entre pernas, n de amostra) em vez de adjetivos.
