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

## 🔜 Sprint 1 — Baseline ([[camada2-baseline-plano-v1]])

- [ ] **[P0] ◀ PRÓXIMO** Harness de backtest + métricas + portão — *módulo:* `backtest_harness` · *dep:* predictor ✓ · *aceite:* Brier < uniforme com IC; **portão rejeita termo nulo**
- [ ] **[P1]** Relatório + reliability diagrams — *módulo:* `report` · *dep:* harness · *aceite:* bins ≥20/faixa; cobertura de banda calculável

## 📋 Backlog — C2.5 (cada termo atrás do [[camada2-planejamento-v1|portão]])

- [ ] **[P1]** Calibrar [[Mando de campo|mando (E2)]] separado de altitude — *dep:* baseline · *aceite:* ΔBrier com IC>0 **ou remover**; θ_alt e mando identificáveis (B2)
- [ ] **[P1]** [[Ajustes ambientais|Altitude (E1) + calor (E3)]] juntos — *dep:* baseline · *aceite:* IC que não cruza zero; calibrados em conjunto
- [ ] **[P1]** Piso de [[Ajustes ambientais|bola parada (E4)]] — *dep:* StatsBomb · *aceite:* fecha o gap BTTS observado; IC>0
- [ ] **[P2]** Fuso (E5) + descanso (E6) em `σ_ajuste` — *dep:* baseline · *aceite:* melhora **cobertura da banda**, não o ponto
- [ ] **[P2]** [[xG preditivo|xG]] prior + Dixon-Coles + reconciliar as duas P(E) — *dep:* StatsBomb · *aceite:* recomputa V/E/D/over/BTTS coerentes
- [ ] **[P2]** Afinação dos pesos do [[Ensemble]] — *dep:* ≥30 jogos · *aceite:* grid minimiza Brier, congelado por fase

## 📋 Backlog — Camadas 3–6

- [ ] **[P2]** Detector de desfalques (JSON → σ) — Camada 3
- [ ] **[P2]** Insights: Monte Carlo do torneio + cenários de classificação — Camada 5
- [ ] **[P2]** Interface local — Camada 6
