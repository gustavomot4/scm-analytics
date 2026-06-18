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
| D-19 | **Calor (E3) NÃO adotada** | portão over/under **+0,0007**, IC [−0,0008, +0,0022] **cruza zero** (n=15.378 quentes; κ ótimo no treino = 0,01, o menor). Causas prováveis: climatologia mensal é **proxy grosseiro** (não o WBGT do dia/horário) e o efeito é sutil/absorvido pelo estilo. Não entra como termo de λ. |
| D-20 | **Confiança = reliab(p_max)·maturidade** | A forma antiga `g_rating=1−min(0.6,σ_dr/σ_ref)` travava a confiança em ~68 — o `σ_ajuste` do jogo hipotético pisava o `σ_dr`. Nova confiança ancora na **confiabilidade medida**: curva isotônica de acerto do 'top pick' por faixa de p_max (`calibrate_confidence`, grava `meta`), × maturidade do rating (σ_R). Massacre maduro→~76 (alta), parelho→~30, provisório derruba. **Não infla nada** — a curva vem do backtest. Rótulos ≥60/40/<40. |
| D-21 | **Mercados são releituras, não novos modelos** | over/under 0.5–4.5, totais por time, clean sheet, dupla chance, handicap e **quem marca 1º** saem da MESMA matriz Poisson (`predictor.markets`); 'quem marca 1º' por Poisson concorrente `λ_i/(λ_A+λ_B)·(1−e^-(λ_A+λ_B))`. Zero graus de liberdade novos → **não passam por portão** (são exatos dado λ). 'Tempo do gol' fica fora até ingerir o minuto (`goalscorers.csv`). |
| D-22 | **Piso de λ conserva T_m (P01)** | Quando o azarão vai ao piso `λ_min`, o favorito é descontado p/ manter `λ_A+λ_B=T_m` (antes a soma furava o total → over/BTTS inflado em massacres). Bug do audit técnico. Bump p/ `baseline-v0.2.1`. |
| D-23 | **Estilo (tendência de gols) é candidato, portão na Brier de BTTS** | Feature dormente do contrato (sempre 1.0, P10 do audit). Implementada (`estilo.py`, shrinkage+cap, PIT). Como move o TOTAL e não o 1X2, o portão mede a **Brier de BTTS** (mesma lição do calor). Só entra no pipeline default se passar. É a alavanca natural do BTTS. **→ RODADO E REJEITADO** (n=445): corrige o viés médio (BTTS 50,5%→47,0% vs real 46,7%) mas ΔBrier-BTTS −0,0008 IC[−0,0083,+0,0069] **cruza zero** (sem skill por jogo; ~200 DOF por time). O viés é GLOBAL → vai p/ T_base (D-25). |
| D-24 | **Curva de confiança carimba a versão do modelo (P09)** | `calibrate_confidence` grava `{model, curve}` em `meta`; `predict_match` sinaliza `reliab_stale` se a versão não bater. Sugestões de nome agora por `difflib` (P12). |
| D-25 | **T_base calibrado na Brier de BTTS/over (não 1X2)** | O audit+dúvida do usuário expuseram BTTS ~4pp alto. O grid antigo media 1X2 (cego a T_base). `calibrate_total.py` escolhe T_base no treino minimizando viés de BTTS/over, valida no teste com **guarda de não-regressão do 1X2** (IC). 1 grau de liberdade, auditável. Candidato — rodar e adotar se passar. |
| D-18 | **Altitude (E1) ADOTADA → v0.2** | portão: ganho de Brier **+0,0491**, IC95 [+0,028, +0,070] nos **554 jogos de altitude** (θ=0,5 McSharry, sem p-hacking). Mesmo com o Elo, sobra sinal. `gd_alt` ativo no predictor; =0 fora de altitude. |
| D-17 | **Calibração C2.5 NÃO adotada (mantém v0.1)** | grid treino/teste deu ganho **+0,0013** no teste (IC [+0,0001,+0,0025]) — significativo por um fio, **irrelevante na prática**. Placeholders da v5 confirmados quase ótimos. Não se troca versão por isso. |
| D-16 | **Índice git em `/tmp` no sandbox** | o FS do mount corrompe o `.git/index` (chegou a apagar 2 arquivos de teste num commit — recuperados). Mitigação: as operações git do **agente** usam `GIT_INDEX_FILE=/tmp/...`; o `.git` do **usuário** (FS real) não tem o problema. |