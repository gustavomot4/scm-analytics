---
tags: [projeto, contexto, onboarding]
status: atual
tipo: contexto
data: 2026-06-15
aliases: ["Contexto do projeto", "Onboarding"]
---

# CLAUDE.md — contexto do projeto (leia isto primeiro)

## Objetivo (3 linhas)
Sistema **local e gratuito** que prevê partidas da Copa 2026 entregando **probabilidades V/E/D, gols esperados e confiança** — nunca certezas.
Motor matemático auditável (Elo → Poisson → ensemble), validado por **backtest histórico** antes de qualquer uso.
**Não é ferramenta de aposta**; Brier ~0.60 não é vantagem.

## Estado atual
**Planejamento (congelado):** contrato matemático **v5.0** ([[camada1-planejamento-v5]]), auditado ([[camada1-revisao-v5]]) e autocontido ([[camada1-apendice-formas-v5]]); design do backtest ([[camada2-planejamento-v1]]); plano de build ([[camada2-baseline-plano-v1]]); 9 execuções manuais ([[06 - Analises]]); registro imutável ([[Registro de previsoes]]).
**Código:** baseline 6/6 + ferramentas C2.5 (`calibrate`/`altitude`/`heat`) + **`predict_match`** (prever um jogo) + **`web`** (interface gráfica). **86 testes**, pipeline E2E. Modelo `baseline-v0.2.1-altitude`. Ver [[Codigo (estrutura)]] e [[Como rodar o sistema]].
**✅ Baseline VALIDADO** (torneios n=2241 Brier 0,562 bate uniforme com IC; ECE 0,023). Modelo atual: **`baseline-v0.2-altitude`**. **Portão C2.5 (decididos):** altitude (E1) **✅ adotada** (+0,049, D-18) · calor (E3) **✗** (D-19) · calibração de coeficientes **✗** (D-17). Candidatos restantes **opcionais**: bola parada (E4, StatsBomb) e descanso (E6, σ). Ver [[Backtest baseline (resultados)]].

## Decisões tomadas (resumo — detalhe em [[Decisoes tecnicas]])
- Contrato congelado v5.0; mudar fórmula = nova versão.
- **Sem ML/bayes hierárquico** (auditabilidade/overfit). **Custo R$ 0, roda local.**
- **Portão de backtest:** nada entra em λ/dr sem IC que não cruza zero.
- **Baseline primeiro** (Elo+mando+σ_R→Poisson), depois fatores ambientais atrás do portão.
- Stack: Python + NumPy/pandas + SQLite + pytest ([[TECH_STACK]]).

## Restrições não negociáveis
1. **Zero custo** — sem APIs/bases/hospedagem pagas.
2. **Roda local** — nada lê a internet no cálculo (snapshot em disco).
3. **Probabilidades, nunca certezas** — inclusive sobre o próprio modelo.
4. **Registro pré-jogo imutável** — nunca reescrever linha gravada ([[Registro de previsoes]]).
5. **Não inventar dados/fontes** — lacunas declaradas ficam declaradas.

## Mapa das notas-chave
- Visão: [[Indice]] · este [[CLAUDE]] · [[MODELO_FINAL]] · [[TECH_STACK]] · [[BACKLOG]] · [[Plugins recomendados]]
- Contrato: [[camada1-planejamento-v5]] · [[camada1-apendice-formas-v5]] · [[camada1-revisao-v5]]
- Modelos: [[Elo]] · [[Poisson]] · [[Incerteza e propagacao]] · [[Ensemble]] · [[Mando de campo]] · [[Ajustes ambientais]] · [[Confianca]]
- Execução: [[camada2-planejamento-v1]] · [[camada2-baseline-plano-v1]] · [[Decisoes tecnicas]]
- Dados: [[Fontes gratuitas]] · [[Esquema SQLite]] · [[Registro de previsoes]]

## Como rodar e testar
Código em `scm_analytics/` (ver [[Codigo (estrutura)]]). Pipeline `ingest → elo_engine → features_pit → predictor` funcionando:
```
cd scm_analytics
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m scm.ingest --download     # baixa snapshot martj42 (1x, na sua máquina)
python -m scm.ingest                # -> dados/scm.sqlite (offline)
python -m scm.elo_engine            # reconstrói o Elo
python -m scm.features_pit          # features point-in-time
python -m scm.predictor             # previsões -> tabela predictions
python -m pytest -q                 # 73 testes
```
**Prever um jogo específico** (porta da frente — usa o Elo atual):
```
python -m scm.predict_match "Brazil" "Argentina"               # sede neutra
python -m scm.predict_match "Mexico" "Germany" --city "Mexico City"   # altitude
python -m scm.predict_match "United States" "England" --mando 40      # anfitrião 2026
```
**Interface gráfica** (local, no navegador):
```
pip install -r requirements.txt   # inclui flask
python -m scm.web                 # abre http://127.0.0.1:5000
```
Nomes em inglês (padrão martj42); se errar, ele sugere. Detalhe: [[Codigo (estrutura)]].

## ▶ Estado: CONSOLIDADO
**C2.5 fechado** nos fatores de bom custo-benefício. Modelo atual e recomendado: **`baseline-v0.2-altitude`** (validado + altitude). **Sem tarefa ativa.** Futuro **opcional** (retorno decrescente): bola parada (E4, StatsBomb), descanso (E6, σ), xG/Dixon-Coles, afinação de pesos. Para **previsões de 2026**: rodar o pipeline e **registrar antes do kickoff** ([[Registro de previsoes]], imutável).

## 🔄 Retomada rápida (para um novo chat / após perda de contexto)
Se você é um agente novo pegando o projeto, faça nesta ordem:
1. Leia: este `CLAUDE.md` → [[Indice]] → [[BACKLOG]] (estado dos cards) → [[Codigo (estrutura)]] (status dos módulos).
2. **Estado em 1 linha:** **CONSOLIDADO** em `baseline-v0.2-altitude` — baseline validado (torneios Brier 0,562 bate uniforme com IC) + altitude adotada; calor/calibração barrados pelo portão; **73 testes**; tags `v1.0`/`v1.1` no GitHub.
3. **Valide o ambiente:** `cd scm_analytics && pip install -r requirements.txt && python -m pytest -q` → esperar **62 passed**. Se uma edição `.py` não refletir, `rm -rf scm/__pycache__ tests/__pycache__` (quirk do sandbox).
4. **Próxima tarefa:** seção acima (**C2.5**).
5. **Regras de trabalho:** atualizar a documentação a cada etapa; escrever código de sistema pelo executor (bash) e rodar pytest; nada pago; probabilidades, nunca certezas. Detalhe em [[Decisoes tecnicas]].

## Git / GitHub
O versionamento roda **na máquina do usuário** — o sandbox não mantém `.git` na pasta montada (o FS do mount corrompe o config do git; ver [[Decisoes tecnicas]] D-14). `.gitignore` (raiz) já cobre cache, `.venv`, `*.sqlite`, snapshots e o workspace volátil do Obsidian.

**Setup inicial (1x, no PC, dentro da pasta do vault):**
```
git init -b main
git add -A
git commit -m "Projeto Copa 2026: vault + baseline Camada 2"
```
Criar o repo no GitHub e publicar **pelo terminal** com a GitHub CLI (`gh`):
```
gh auth login                                               # 1x, autentica via navegador
gh repo create <repo> --private --source=. --remote=origin --push
```
Sem `gh`: crie um repo **vazio** em github.com/new e rode `git remote add origin <URL>` + `git push -u origin main`.

**Sincronizar a cada etapa de código:**
```
git add -A && git commit -m "<mensagem>" && git push
```
O agente mantém o projeto **commit-ready** e fornece a **mensagem de commit** ao fim de cada etapa; o `push` é executado pelo usuário (auth própria, persistente).

## ▶ Atualização 2026-06-18 — v0.3 (correções do audit externo)
Modelo recomendado agora: **`baseline-v0.3-altitude`** (92 testes). Aplicadas as correções de alto impacto de [[Auditoria tecnica externa (2026-06-18)]] (Fase 0–1): curva de empate **empírica C1** (substitui o proxy proibido), **baseline Elo público** no portão (o modelo **bate o Elo** com IC>0: major +0,0037 [+0,0009,+0,0066]), **σ informativo** (σ_dr varia por confronto), cobertura de **altitude p/ Guadalajara**, **cobertura de banda por faixa** e índices. Detalhe em [[Decisoes tecnicas]] D-26..D-30 e [[Backtest baseline (resultados)]]. **Rebuild:** rode `features_pit` + `predictor` (a base muda).

## ▶ Atualização 2026-06-19 — consistência produção↔backtest (audit completo)
Aplicadas as correções de **consistência** de [[Auditoria tecnica completa (2026-06-19)]] (Fase 0), que **não** adicionam termos novos a λ/dr (logo não passam pelo portão) — apenas fazem a "porta da frente" entregar o **mesmo modelo já validado**:
- **D-34:** `predict_match` agora aplica a **forma recente** ao `dr` (`elo_A − elo_B + (forma_A − forma_B) + mando`), igual ao `features_pit.dr_adj` do backtest. Antes a forma era descartada na produção.
- **D-35:** a **confiança** usa o `σ_R` **escalado** por consistência (`vol_mult`), não o bruto.
- **D-36:** `--estilo` rotulado `[EXPERIMENTAL]` (rejeitado pelo portão, D-23).

**Estado canônico (reconciliação P-K):** modelo **`baseline-v0.3-altitude`** (`predictor.MODEL_VERSION`); **18 arquivos de teste** em `tests/` (+1 caso novo `test_dr_includes_recent_form`). As menções antigas a `v0.2`/`v0.2.1` e a contagens "73/86/92" nesta nota e no `README` são **históricas** — vale o que está em `predictor.MODEL_VERSION`. **Aberto** (Fase 1+ do audit): Dixon-Coles/diversidade real do ensemble, σ estrutural (Glicko/TrueSkill), altitude no Monte Carlo (`simulate`, N2), mando do anfitrião no portão, Camada 3 (desfalques), validação prospectiva fechada. **Não rodei `pytest`** nesta sessão (sandbox sem pytest/rede) — validei a lógica com um harness numpy+sqlite; **rode `python -m pytest -q` na sua máquina** após o pull.

## ▶ Atualização 2026-06-19 (b) — melhorias do audit (Fases 1–3)
Implementadas mais correções de [[Auditoria tecnica completa (2026-06-19)]], **com portão real rodado no `dados/scm.sqlite` local** (reproduzi Brier 0,5366 / +0,0028 vs Elo antes de mexer):
- **D-37 — Altitude no Monte Carlo** (`simulate.py` + `copa2026.json` `altitude_venues`). México: avanço 98,5%→99,9%, título 3,1%→4,0%.
- **D-38 — Registro prospectivo** (`scm/registrar.py`, register/settle/report, imutável) → mede Brier real da Copa. **Use agora**, jogo a jogo.
- **D-41 — Camada 3 desfalques** (`scm/desfalques.py` + hook em `predict_match`); JSON que você preenche.
- **D-42 — σ Glicko** (`scm/sigma_glicko.py`, candidato OFF): RD varia 51–64 nas elites (σ_r era ~40 fixo). Adotar exige rebuild + portão de banda.
- **D-39/D-40 — Dixon-Coles e recalibração 1X2: TESTADOS e REJEITADOS pelo portão** (DC ρ=−0,06 piora BTTS; recal T=1,0). Ficam como candidatos OFF (`dixon_coles.py`, `calibrate_1x2.py`).
- **D-43 — Higiene:** núcleo único `predictor.ved_from_elo` (idêntico em grade), `tests/conftest.py`, `requirements` com teto de major.

**Lição (importante):** com os dados atuais, **ajustes paramétricos no núcleo não vencem o portão** (DC/recal rejeitados) — o motor está no teto. Ganho real agora vem de **dados novos** (desfalques/odds/xG via D-41 e schema-alvo) ou de **σ informativo** (D-42, validar). Módulos novos: `tests/` agora cobre registrar/desfalques/dixon_coles/calibrate_1x2/sigma_glicko. **Rode `pytest` na sua máquina após o pull.**

## ▶ Atualização 2026-06-19 (c) — web /bracket + experimentos gateados
- **Web `/bracket`** (D-46): `web.py` (`/bracket` + `/api/bracket`) + `templates/bracket.html` — chaveamento **dos 16 avos à final** (dois lados convergindo, % por confronto) **lado a lado** com a tabela do Monte Carlo. `python -m scm.web` → `/bracket`. Bracket data: `simulate.most_likely_bracket` (D-45).
- **odds visíveis** (D-44): `predict_match --odds CASA EMPATE FORA` mostra mercado + 1X2 misturado (20%).
- **σ_dr encolher** (D-47): testado no portão de banda → **não adotado** (cobertura não-estacionária: sobre-cobre antigo, sub-cobre recente). Mantém σ_dr.
- **Mando (P-E)** (D-47): H empírico ≈110–120 Elo; motor usa 100 (ok). +40 do anfitrião 2026 = juízo declarado.
- **Padrão confirmado:** Dixon-Coles, recalibração, σ-Glicko e σ_dr-scaling **todos barrados pelo portão**. O núcleo Elo→Poisson está no **teto** com os dados atuais — ganho real vem de **dados** (desfalques/odds/xG) e de **uso** (registro prospectivo a cada rodada). Registro prospectivo é operacional: registre antes do jogo, preencha depois.

## ▶ Atualização 2026-06-19 (d) — operacional + dados + UX (D-50..D-52)
- **Registro a cada rodada** (D-51): `python -m scm.registrar register-batch rodada.json` → após os jogos, `python -m scm.ingest --download` + `python -m scm.registrar settle-from-db` + `report`. `register` auto-carrega `dados/desfalques.json` e odds do `odds_hist`.
- **Explicador** (D-52): a tela de previsão decompõe o `dr` (Elo/forma/mando/desfalque) + saldo (altitude/desfalque-ataque).
- **Simulate** (D-52): desempate de grupo por **confronto direto** (regra FIFA) antes do sorteio; `alt_venues` aceita sede por jogo (`"A|B": cidade`).
- **xG** (D-50): `team_xg` + `scm/xg.py` — esqueleto OFF (precisa do StatsBomb + portão).
- **Fechamento honesto:** o núcleo está no teto (DC/recal/σ-Glicko/σ_dr todos barrados pelo portão). O valor agora é **operacional** (registrar a Copa) e **dados** (desfalques/odds/xG). Pare de adicionar fórmula; meça.

## ▶ Atualização 2026-06-20 — v0.4 (perna AD ligada; portão aplicado)
Modelo recomendado agora: **`baseline-v0.4-ad`**. Implementação do plano da [[Auditoria + plano de melhorias (modelo, 2026-06-20)]] (Fases 0–3). Detalhe em [[Evolucao v0.4 - perna AD + sigma no torneio (2026-06-20)]].
- **Perna ataque/defesa não-Elo LIGADA** (`w_ad=0.30`) — fonte de gols independente do `dr`. Portão **+0,0039 IC[+0,0028,+0,0051]** (torneios). O modelo agora **bate o teto não-paramétrico do `dr`** (torneios vs lookup **+0,0062 IC>0**; era empate). Brier torneios **0,5590→0,5554**, todos **0,5365→0,5336**. [verificado]
- **Porta da frente alinhada:** `predict_match` passou a usar a perna AD (consistência produção↔backtest).
- **σ propagado no Monte Carlo** (`simulate`): a sim deixa de tratar o Elo como exato (efeito modesto — σ_R degenerado).
- **Rejeitados pelo portão (ficam OFF):** `T_base` (ótimo=2,60), forma `tanh` (pior no tail −0,0042), recalibração 1X2 (T=1,0; isotônica −0,0021), σ-Glicko (banda já sobre-cobre). Ressalva: ECE subiu 0,026→0,033.
- **Higiene:** novo `tests/test_skill_regression.py` (trava o skill do backtest, audit P12); `config.W_AD`.
- **Rebuild:** `rm -rf scm/__pycache__ && python -m scm.predictor` (a base muda). Rode `pytest` na sua máquina.

## ▶ Atualização 2026-06-20 (b) — afinação + rigs de dados
- **`w_ad` afinado 0,30 → 0,50** (grid+portão): Brier major **0,5554→0,5542**, bate o teto do dr **+0,0073 IC>0**. Parei em 0,50 (acima de ~0,7 o ECE degrada). Recalibração 1X2 re-testada e **segue rejeitada** (T*=1,0). [verificado]
- **Rigs montados (dado é seu):** `odds.py bench` (Brier modelo vs mercado) + template `dados/odds_copa.csv`; caminho xG→AD verificado (`scm.attack_defense --xg-prior`); `dados/desfalques.json` (template, efeito direcional verificado). Detalhe: [[Evolucao v0.4 - perna AD + sigma no torneio (2026-06-20)]] (adendo b).

## ▶ Atualização 2026-06-20 (d) — pipeline de xG turnkey (prior de elenco, OFF até o portão)
A maior alavanca permitida (comparação vs Opta/EA): **xG como prior da perna AD**. Encanamento pronto, **OFF por padrão** (`config.USE_XG_PRIOR=False`) — nada muda no v0.4 até passar o portão.
- **`scm.xg build <clone do statsbomb/open-data>`** → `team_xg` (+ CSV). Ou `scm.xg ingest <csv>` (manual).
- **`scm.attack_defense --gate-xg`** (`gate_xg_increment`): mede se o xG ACRESCENTA sobre a perna AD (ΔBrier pareado, IC).
- **Se IC>0:** `config.USE_XG_PRIOR=True` + `rm -rf scm/__pycache__` + rebuild + bump (`baseline-v0.5-xg`). Senão, deixa OFF.
- Guia: [[Como usar xG (prior de elenco) — turnkey (2026-06-20)]]. Limite: StatsBomb cobre WC18/22+Euro, não as 48.

## ▶ Atualização 2026-06-21 — xG rodado no dado REAL: portão marginal, NÃO adotado
Construtor `scm.xg build` validado no StatsBomb real (73 seleções, 37/48 da Copa; `dados/xg.csv`). Portão `gate_xg_increment`: major **+0,00022 IC[+0,00001,+0,00044]** (passa por um fio), todos **+0,00002 IC cruza 0** (nulo). **Mantido `USE_XG_PRIOR=False`** (ruído; ~6× menor que o que D-17 já rejeitou). Motivo: a perna AD já extrai gols (xG ~redundante) e a **simulação usa só `lambdas(dr)` [Elo]**, então xG não toca o favoritismo. Para mexer no título, o sinal de elenco teria de entrar no `dr`/λ da simulação (mudança maior, com portão). Detalhe: [[Como usar xG (prior de elenco) — turnkey (2026-06-20)]] (RESULTADO REAL).

## ▶ Atualização 2026-06-21 (b) — sinal de gols (perna AD) no λ da SIMULAÇÃO (ADOTADO)
A simulação do título usava só `lambdas(dr)` (Elo puro). Agora amostra de `λ=(1−α)·λ_Elo+α·λ_AD` (α=`config.SIM_AD_BLEND=0.5`), com a λ da perna AD (gols). **Portão: major +0,00712 IC[+0,0047,+0,0096]; all +0,00497 IC[+0,0043,+0,0056]** — passa com folga (maior ganho do trabalho). Efeito no título: Brasil/Portugal/Alemanha ↑ (rumo ao consenso), México (anfitrião) ↓, **Spain ↓ 15→10** (gols não sustentam o favoritismo de elenco do EA/Opta), Colômbia segue alta (Copa América a defende), Argentina segue 1º. Muda só a SIM; o modelo de 1 jogo (v0.4-ad) é o mesmo. Detalhe: [[Comparacao com mercado, Opta e EA (2026-06-20)]] (experimento 06-21).

## ▶ Atualização 2026-06-21 (c) — docs consolidadas + mercado-na-sim (inviável)
- **Docs sincronizadas p/ `baseline-v0.4-ad`:** [[Como rodar o sistema]] (versão + comandos novos), [[Codigo (estrutura)]], `scm_analytics/README` (137 testes / 26 arquivos), [[Indice]] (seção Auditoria & evolução). `.gitignore`: `open-data/` (clone de ~18 GB do StatsBomb) ignorado; `xg.csv` opcional p/ versionar.
- **Experimento mercado-no-λ-da-sim: ESTRUTURALMENTE INVIÁVEL** — o mercado só precifica jogos agendados; a sim precisa de λ p/ a árvore hipotética (cobertura ~1,1%). Sem portão a rodar. Mercado fica na previsão de 1 jogo (0,20) + uso operacional. Detalhe: [[Comparacao com mercado, Opta e EA (2026-06-20)]] (experimento b).

## ▶ Atualização 2026-06-21 (d) — UX: launcher 1-clique + pop-up de atualização persistente
- **Launcher** `scm_analytics/Abrir SCM (Copa 2026).bat` (duplo-clique): 1ª vez cria venv + instala deps + constrói a base; depois sobe `scm.web --open` e abre o navegador. Sem terminal.
- **Pop-up flutuante persistente** (`templates/_update_widget.html` reescrito): botão **"Atualizar tudo"** + barra de %, etapa e **logs ao vivo**; faz poll de `/api/update/status` em TODA tela (estado server-side) → **não some ao navegar**; minimizar/mostrar com memória (localStorage), canto inferior direito (não atrapalha).
- **Backend** (`web.py`): `_UPDATE` agora tem `pct`+`logs`+`started`; `/api/update/status` devolve `elapsed`; `scm.web --open` abre o navegador. Verificado: web.py compila; as 4 telas renderizam com o pop-up (Jinja). Flask não roda no sandbox da auditoria → teste o servidor na sua máquina.

## ▶ Atualização 2026-06-21 (e) — "Atualizar" INCREMENTAL (12 min → segundos)
O botão **"Atualizar tudo"** ficou incremental: `features_pit`/`predictor` agora processam **só os jogos NOVOS** (os antigos são invariantes — point-in-time), em vez de reprocessar os 49k. **Verificado** (synthetic): resultado **idêntico** ao rebuild completo (features e previsões batem 100%), processando só os novos. Numa atualização diária (poucos jogos) cai de ~12 min p/ **segundos**. `elo_engine` segue full (rápido, ~s) por robustez. Flags: `features_pit.run(incremental=True)`, `predictor.run(incremental=True)` (CLI segue full por padrão = seguro). **Pressuposto: append-only** (jogos novos = os mais recentes; vale na Copa). Após **correção** de jogo antigo no snapshot OU mudança de **código** de feature, rode rebuild completo: `python -m scm.features_pit && python -m scm.predictor`.

## ▶ Atualização 2026-06-21 (f) — UX web lote 1 (auditoria [[Auditoria UX-web (2026-06-21)]])
Aplicado: P1 texto do chaveamento (simulacao dizia "sorteio aleatório" — corrigido p/ oficial FIFA); P2 `predict_match` aceita nomes em PT (apelidos→EN); P4 a11y (labels nas odds, sims `type=number`, abas `role=tab`, aria na barra); P5 Guadalajara no venue + botão trocar lados + scroll ao resultado + link de registro c/ handoff p/ o Prospectivo. 32/32 compila; 4 telas renderizam. Pendente: P3 (cache/progresso do bracket), P6 (base template + CSS único), P7 (polish).

## ▶ Atualização 2026-06-21 (g) — UX web lote 2 (P3 perf + P6 front)
P3: `/api/bracket` e `/api/simulate` agora **cacheiam** (por sims+impressão-digital dos dados) e rodam a 1ª vez em **job de fundo com % real** (`web._run_sim_job` + `simulate.run(progress=)`); front faz poll com **barra de progresso**; default 5000→**2000**. P6: **sidebar única** (`templates/_sidebar.html`) e **CSS morto removido** nas 4 telas. 32/32 compila; 4 telas renderizam. Não testado no Flask ao vivo (sandbox sem flask) → testar no navegador. Detalhe: [[Auditoria UX-web (2026-06-21)]] (lote 2).

## ▶ Atualização 2026-06-21 (h) — UX web lote 3 (P7 polish)
Favicon (SVG data-URI) nas 4 telas; **dark mode** aditivo (`prefers-color-scheme`, não afeta o claro) nas 4 + popup; pop-up responsivo no mobile. Separador decimal (vírgula) **deferido de propósito** (colide com larguras CSS via toFixed e refs §3.8; baixo valor). Auditoria UX P1–P7 concluída. Detalhe: [[Auditoria UX-web (2026-06-21)]] (lote 3).

## ▶ Atualização 2026-06-21 (i) — operar e medir a Copa (placar real)
Novo: `python -m scm.report --copa` = Brier do modelo na Copa 2026 (previsões PIT) vs uniforme (IC) e vs mercado, repetível a cada rodada (`report.cup_scorecard`). **Medição real (36 jogos): Brier 0,587 vs uniforme 0,667, mas IC [-0,067,+0,219] CRUZA ZERO** — 1 torneio é ruidoso; não prova skill ainda (o backtest de 2.253 dizia que sim). Mercado à frente (0,566 vs 0,640, n=12). Runbook da rodada em [[Operação da Copa 2026]]. settle-from-db: 0 novos, 11 em aberto (aguardando placares no snapshot).
