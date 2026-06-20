---
kanban-plugin: board
tags: [dev, backlog, kanban]
status: vivo
tipo: backlog
data: 2026-06-15
---

## ✅ Concluído (planejamento)

- [x] **Contrato v5.0 congelado e auditado** — [[camada1-planejamento-v5]] + [[camada1-revisao-v5]]
- [x] **Design do backtest (C2)** — [[camada2-planejamento-v1]]
- [x] **Plano do baseline** — [[camada2-baseline-plano-v1]]
- [x] **Vault Obsidian organizado** — [[Indice]]
- [x] **[M1] Ingestão martj42 → SQLite** — módulo `scm/ingest.py`; **5/5 testes verdes** (contagens, sem nulos, idempotência, neutro); E2E ok. *fixturedownload adiado p/ o card de fuso/descanso.* Ver [[Codigo (estrutura)]]
- [x] **[M2] Motor Elo histórico** — módulo `scm/elo_engine.py`; **9 testes verdes** (`we(100)=0.64`, mando, zero-sum, **point-in-time**, idempotência); grava `match_ratings` (rating pré-jogo) + `ratings_current` (+σ_R/provisório). *Benchmark eloratings ±25 roda com dados reais na sua máquina.*
- [x] **[M3] Features point-in-time** — módulo `scm/features_pit.py`; **6 testes verdes** incl. **anti look-ahead** (jogo futuro não altera feature passada); grava `match_features` (`dr_adj`, `σ_dr`, forma recência+adversário).
- [x] **[M4] Preditor congelado** — módulo `scm/predictor.py`; **9 testes verdes** (reproduz a execução manual IRN×NZL no Poisson; P∈[0,1] e soma 1; **propagação encolhe favorito**; piso de λ); grava `predictions` (P(V/E/D), banda, λ, over/BTTS). Propagação **determinística** (reprodutível).
- [x] **[M5] Harness de backtest** — módulo `scm/backtest_harness.py`; **7 testes verdes** (Brier/RPS/LogLoss; **portão aceita termo informativo e rejeita termo nulo**; bootstrap determinístico por seed); `evaluate()` testa Brier vs uniforme com IC.
- [x] **[M6] Relatório (calibração)** — módulo `scm/report.py`; **6 testes** (reliability bins, ECE, cobertura de banda); reliability diagram opcional (matplotlib). **🎉 Baseline 6/6 completo — 42 testes; pipeline E2E rodando.**

## 🔜 Sprint 2 — Backtest com dados reais ([[camada2-planejamento-v1]])

- [x] **✅ Backtest real — baseline VALIDADO** (49.423 jogos; torneios n=2241: **Brier 0,562 < uniforme 0,667, IC [+0,089,+0,120]**, ECE 0,023, banda dentro). Ver [[Backtest baseline (resultados)]]. **Próximo: C2.5 (lane abaixo).**

## ✅ C2.5 — CONSOLIDADO (fatores de bom custo-benefício avaliados pelo portão)

> **Modelo atual: `baseline-v0.2-altitude`.** Altitude ✅ adotada; calor e calibração ✗ (portão). Os itens abaixo ficam como **futuro opcional** (retorno decrescente / atrito de dados).

- [x] **Calibrar coeficientes (`scm/calibrate.py`)** — ganho no teste **+0,0013** (IC marginal) → **não adotado**; placeholders v5 confirmados quase ótimos (D-17). v0.1 mantido.

- [ ] **[P1]** Calibrar [[Mando de campo|mando (E2)]] separado de altitude — *dep:* baseline · *aceite:* ΔBrier com IC>0 **ou remover**; θ_alt e mando identificáveis (B2)
- [x] **[[Ajustes ambientais|Altitude (E1)]] ADOTADA (v0.2)** — portão **+0,0491** IC[+0,028,+0,070] em 554 jogos → ativa no pipeline (D-18).
- [x] **[[Ajustes ambientais|Calor (E3)]] NÃO adotada** — portão over/under +0,0007 IC[−0,0008,+0,0022] cruza zero (n=15.378); proxy de climatologia grosseiro (D-19).
- [x] **Portão do estilo RODADO → rejeitado** (D-23): corrige a média do BTTS (50,5→47 vs real 46,7) mas sem skill por jogo (IC cruza 0). Viés é global.
- [ ] **[P1]** Rodar **`calibrate_total`** (T_base na Brier de BTTS/over) e adotar se passar (D-25) — corrige o BTTS ~4pp alto com 1 parâmetro
- [ ] **[P2] (futuro opcional)** Piso de [[Ajustes ambientais|bola parada (E4)]] — *dep:* StatsBomb (download; só 2018/2022/Euro) · *aceite:* fecha o gap BTTS; IC>0
- [ ] **[P2]** Fuso (E5) + descanso (E6) em `σ_ajuste` — *dep:* baseline · *aceite:* melhora **cobertura da banda**, não o ponto
- [ ] **[P2]** [[xG preditivo|xG]] prior + Dixon-Coles + reconciliar as duas P(E) — *dep:* StatsBomb · *aceite:* recomputa V/E/D/over/BTTS coerentes
- [ ] **[P2]** Afinação dos pesos do [[Ensemble]] — *dep:* ≥30 jogos · *aceite:* grid minimiza Brier, congelado por fase

## 📋 Backlog — Camadas 3–6

- [ ] **[P2]** Detector de desfalques (JSON → σ) — Camada 3
- [ ] **[P2]** Insights: Monte Carlo do torneio + cenários de classificação — Camada 5
- [x] **Interface local (Camada 6) — ENTREGUE:** `scm/web.py` (Flask, UI de produto) + `predict_match`. Ver [[Como rodar o sistema]].
- [x] **Resposta ao audit técnico — ENTREGUE:** P01 (piso conserva T_m, D-22), estilo implementado+gated (D-23), curva de confiança versionada + difflib (D-24), diagnóstico de BTTS (`report --btts`). Ver [[Resposta ao audit tecnico]]. **83 testes.**
- [x] **Mercados (Poisson) + confiança evoluída — ENTREGUE:** `predictor.markets` (over/under 0.5–4.5, totais, clean sheet, dupla chance, handicap, **quem marca 1º**) + confiança `reliab(p_max)·maturidade` calibrável (`calibrate_confidence`); na CLI e na interface. **73 testes.** [[Decisoes tecnicas|D-20]]/[[Decisoes tecnicas|D-21]].

## ✅ Camada 5 (insights) — Monte Carlo do torneio ENTREGUE (2026-06-18)
- [x] **Simulação da Copa (`scm/simulate.py`)** — P(campeão/final/semi/passar) por seleção; reusa o mata-mata (D-31); CLI + página `/simulacao`. Preencher o sorteio em `dados/copa2026.json`. Ver [[Decisoes tecnicas]] D-32. *(Cenários de classificação determinísticos seguem como futuro.)*

## ✅ Consistência produção↔backtest — ENTREGUE (2026-06-19, audit completo)
> Correções da Fase 0 de [[Auditoria tecnica completa (2026-06-19)]] — **sem termos novos** (não passam pelo portão), só alinham a porta da frente ao modelo validado. Verificado por harness numpy+sqlite (26/26); **rodar `pytest` na máquina do usuário**.
- [x] **N1 — forma no `predict_match`** (D-34): `dr = elo_A − elo_B + (forma_A − forma_B) + mando`; teste novo `test_dr_includes_recent_form`.
- [x] **N3 — confiança usa σ_R escalado** (D-35): `(sr_a + sr_b)/2` em vez do σ bruto.
- [x] **N4 — `--estilo` rotulado EXPERIMENTAL** (D-36).

## 📋 Backlog — achados abertos do audit (2026-06-19), por prioridade
- [ ] **[P0] N2** — aplicar **altitude no Monte Carlo** (`simulate`): exige o mapa **jogo→sede 2026** (não inventar). Hoje a chance de título ignora CDMX/Guadalajara.
- [ ] **[P1] P-A** — **Dixon-Coles** + membro de **prior não-Elo** no ensemble (diversidade real; corrige BTTS/under).
- [ ] **[P1] P-B** — **σ estrutural** (Glicko/TrueSkill ou erro do ajuste de Elo) — σ_R hoje satura ~40.
- [ ] **[P1] P-C** — **recalibração isotônica do 1X2** (superconfiança medida em [0,8–0,9]).
- [ ] **[P1] P-D** — **forma saturante** de GD (`tanh`) — evita λ_B<0 no tail.
- [ ] **[P1] P-E** — **mando do anfitrião** (+40) pelo portão (P04).
- [ ] **[P2] P-F** — **Camada 3** (desfalques/escalações) — maior fator jogo-a-jogo.
- [ ] **[P2] P-G** — **registro prospectivo gerado por código** + resultados → primeiro Brier real.
- [ ] **[P2] P-H** — evoluir **schema-alvo** (venues/context/odds/statsbomb).
- [ ] **[P2] N5** — versionar `copa2026.json` (config do torneio) p/ reprodutibilidade do `simulate`.
- [ ] **[P3]** Faxina (P-I): centralizar a leitura Elo-direto (3 cópias), `conftest.py`, context managers, `logging`; pinar deps (P-J); `natural_key` com cidade (P-L); benchmark de Elo automatizado (P-M).

## ✅ Round 2 — melhorias do audit ENTREGUES (2026-06-19b)
> Portão rodado no `dados/scm.sqlite` local (Brier 0,5366 reproduzido). Ver [[Auditoria tecnica completa (2026-06-19)]] follow-up (b) e [[Decisoes tecnicas]] D-37..D-43.
- [x] **N2 — altitude no Monte Carlo** (D-37): `simulate` + `copa2026.json altitude_venues`. México avança 98,5→99,9%, título 3,1→4,0%.
- [x] **P-G — registro prospectivo** (D-38): `scm/registrar.py` (register/settle/report, imutável). **Usar a cada jogo da Copa.**
- [x] **P-F — Camada 3 desfalques** (D-41): `scm/desfalques.py` + hook em `predict_match` (dado via JSON do usuário).
- [x] **P-A — Dixon-Coles**: TESTADO e **REJEITADO** pelo portão (D-39, ρ=−0,06 piora BTTS). Candidato OFF `dixon_coles.py`.
- [x] **P-C — recalibração 1X2**: TESTADA e **REJEITADA** (D-40, T*=1,0). Candidato OFF `calibrate_1x2.py`.
- [x] **Higiene**: `predictor.ved_from_elo` (núcleo único, idêntico em grade), `conftest.py`, `requirements` com teto (D-43).
- [x] **P-B — σ Glicko: portão de banda RODADO → NÃO adotado** (D-42): RD varia 51–64 (resolve a degenerescência), mas a banda já sobre-cobre (~92% vs 68%) e o Glicko a alarga (0,134→0,184). Candidato OFF com `run_pit`+`gate_band` prontos. *Achado: o certo é ENCOLHER σ_dr (banda larga demais) — novo card.*
- [x] **P-H (parcial) — esqueleto de odds/mercado** (D-44): `odds_hist` + `scm/odds.py` (de-vig) + `predict_match(odds=...)` mistura mercado no peso 0,20. Falta a captura periódica (manual) e backtest com série de mercado.
- [ ] **[P1] Encolher/ calibrar σ_dr** (novo, do portão de banda): a banda sobre-cobre (~92% vs 68%) → escalar σ_dr para baixo e re-gatear a cobertura.
- [x] **Chaveamento mais provável** (D-45): `simulate.most_likely_bracket` + `--bracket`. Bracket determinístico com % por confronto (complementa o Monte Carlo). 2026: México no caminho único; Monte Carlo dá Argentina/Espanha/França.
- [x] **Odds visíveis no CLI** (D-44): `predict_match --odds CASA EMPATE FORA` mostra mercado + 1X2 misturado.
- [ ] **[P1] P-E** mando do anfitrião no portão · **[P2]** captura periódica de odds + comparador de mercado na UI · **[P2]** xG (StatsBomb) como prior.
- [x] **Página web `/bracket` ENTREGUE** (D-46): `web.py` (`/bracket` + `/api/bracket`) + `templates/bracket.html` — chaveamento dos **16 avos** à final + tabela de % do Monte Carlo lado a lado. Recarregável, local.
- [x] **Sidebar de navegação + tema unificado** (D-48): sidebar (Prever/Simular/Chaveamento) nas 3 telas; bracket no tema claro do app.
- [x] **BUG corrigido — fator casa no mata-mata** (D-48, achado do usuário): altitude vazava p/ o KO no bracket e inflava o México (campeão). Agora KO neutro → campeão Argentina (alinha com o Monte Carlo).
- [x] **Bracket redesenhado** (D-49): abas Chaveamento/Probabilidades (MC fora da lateral), cards largos sem sobreposição.
- [x] **Odds na UI** (D-49): campos de odds na previsão + linha "Mercado (sem vig)"; `/api/predict` aceita odds.
- [x] **Altitude θ por confederação revisada** (D-49): θ=0,5 sustenta nas duas (CONMEBOL +0,066; CONCACAF +0,023, IC>0) → mantém θ=0,5. A força do México em casa é real; o exagero era só o KO (D-48). `altitude --by-confed`.
- [ ] **[P3]** Altitude no grupo: monitorar com mais dados de 2026; considerar θ por confederação só se a amostra recente pedir.

## ✅ Round 3 — operacional + dados + UX (2026-06-19, D-50..D-52)
- [x] **Registro prospectivo operacional** (D-51): `register-batch` (rodada via JSON) + `settle-from-db` (preenche pelo snapshot) + `register` auto-carrega desfalques/odds. Fluxo: registrar antes → `ingest --download` + settle depois → `report`.
- [x] **Explicador de previsão** (D-52): UI mostra a decomposição do `dr` (Elo/forma/mando/desfalque) + saldo (altitude/desfalque-ataque).
- [x] **Confronto direto no desempate** + **sede por jogo** no simulate (D-52).
- [x] **xG esqueleto** (D-50): `team_xg` + `scm/xg.py` (candidato OFF; precisa do StatsBomb + portão).
- [ ] **[P1] Próximos (dados, valor real):** preencher `desfalques.json` e capturar odds a cada rodada; gatear o xG quando houver a série StatsBomb.
- [ ] **[P3]** Sede real por jogo da altitude: preencher `alt_venues` por confronto com o calendário oficial.
- [x] **σ_dr encolher: TESTADO → não adotado** (D-47): cobertura de banda é não-estacionária (sobre-cobre antigo, sub-cobre recente); nenhuma escala única resolve. Mantém σ_dr.
- [x] **Mando (P-E) estimado** (D-47): H empírico ≈110–120 Elo; motor usa 100 (ok). +40 do anfitrião 2026 segue juízo declarado.
- [ ] **[P2]** Calibração de σ_dr **por época/estrato** (não-estacionária) — só se houver ganho de cobertura com IC.
- [ ] **[P2]** Comparador de mercado na UI (input de odds no index.html; `predict_match --odds` já mostra no CLI) · captura periódica de odds.
