---
tags: [dev, decisoes, adr]
status: vivo
tipo: decisoes
data: 2026-06-15
---

# Decisões técnicas (ADRs)
Registro curto de *por que* cada escolha. Vivo — append quando algo for decidido.

| # | Decisão | Por quê |
|---|---|---|
| D-01 | **Contrato congelado na v5.0** ([[camada1-planejamento-v5]]) | base estável p/ o backtest; mudar fórmula = nova versão |
| D-02 | **Sem ML/boosting/bayes hierárquico** | matam auditabilidade ou garantem overfit na amostra minúscula |
| D-03 | **Custo R$ 0, roda local** | restrição de projeto; nada lê internet no cálculo (snapshot) |
| D-04 | **Probabilidades, nunca certezas** | inclusive sobre o próprio modelo (não-validado até o backtest) |
| D-05 | **Portão de backtest** ([[camada2-planejamento-v1]] §6) | nenhum termo entra "porque a literatura diz"; só com IC que não cruza zero |
| D-06 | **Baseline primeiro** ([[camada2-baseline-plano-v1]]) | medir o motor antes de adicionar graus de liberdade |
| D-07 | **Registro pré-jogo imutável** ([[Registro de previsoes]]) | sem isso, métrica de validação é autoengano |
| D-08 | **Mercado é benchmark, peso ≤0.20** | pode ecoar o Elo público; não é onisciente |
| D-09 | **Vault Obsidian in-place** | repositório vira o vault (decisão 2026-06-15) |
| D-10 | **Código em `scm_analytics/` (pacote `scm`)** | Python limpo runnable (`python -m scm.ingest`); notas e código na mesma raiz ([[Codigo (estrutura)]]). *Pasta renomeada de `codigo/` em 2026-06-16.* |
| D-11 | **Ingest idempotente por `natural_key`** (date\|home\|away\|tournament) | rodar a ingestão N vezes não duplica (`INSERT OR IGNORE`) |
| D-12 | **Pular jogos sem placar na ingestão** | fixtures futuras não entram em `matches` → sem nulos em chaves |
| D-13 | **Testes sem rede (fixtures); download só na máquina do usuário** | testes determinísticos; snapshot offline preserva "nada lê a internet no cálculo" |
| D-14 | **Versionamento git no PC do usuário; push por sessão** | o sandbox **não mantém `.git`** na pasta montada (o FS do mount corrompe o config) e não há conector de GitHub no registro. O `.git` é criado pela máquina do usuário; com **token fornecido na sessão**, o agente commita e dá push — mas a credencial **não persiste entre chats** (revogar o token após a sessão). Sem token, o usuário roda `git push`. |
| D-15 | **Bootstrap vetorizado (numpy)** | teste de escala (3000 jogos sintéticos) mostrou `harness`/`report` a ~17s/14s com bootstrap em Python puro → vetorizado p/ **~0.4s** (~40x). Sanidade: em dados **aleatórios** o modelo **não bate** o uniforme (Brier 0.68 > 0.667) — sem skill inventado. |
| D-18 | **Altitude (E1) ADOTADA → v0.2** | portão: ganho de Brier **+0,0491**, IC95 [+0,028, +0,070] nos **554 jogos de altitude** (θ=0,5 McSharry, sem p-hacking). Mesmo com o Elo, sobra sinal. `gd_alt` ativo no predictor; =0 fora de altitude. |
| D-17 | **Calibração C2.5 NÃO adotada (mantém v0.1)** | grid treino/teste deu ganho **+0,0013** no teste (IC [+0,0001,+0,0025]) — significativo por um fio, **irrelevante na prática**. Placeholders da v5 confirmados quase ótimos. Não se troca versão por isso. |
| D-16 | **Índice git em `/tmp` no sandbox** | o FS do mount corrompe o `.git/index` (chegou a apagar 2 arquivos de teste num commit — recuperados). Mitigação: as operações git do **agente** usam `GIT_INDEX_FILE=/tmp/...`; o `.git` do **usuário** (FS real) não tem o problema. |