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
- [ ] **[P2] (futuro opcional)** Piso de [[Ajustes ambientais|bola parada (E4)]] — *dep:* StatsBomb (download; só 2018/2022/Euro) · *aceite:* fecha o gap BTTS; IC>0
- [ ] **[P2]** Fuso (E5) + descanso (E6) em `σ_ajuste` — *dep:* baseline · *aceite:* melhora **cobertura da banda**, não o ponto
- [ ] **[P2]** [[xG preditivo|xG]] prior + Dixon-Coles + reconciliar as duas P(E) — *dep:* StatsBomb · *aceite:* recomputa V/E/D/over/BTTS coerentes
- [ ] **[P2]** Afinação dos pesos do [[Ensemble]] — *dep:* ≥30 jogos · *aceite:* grid minimiza Brier, congelado por fase

## 📋 Backlog — Camadas 3–6

- [ ] **[P2]** Detector de desfalques (JSON → σ) — Camada 3
- [ ] **[P2]** Insights: Monte Carlo do torneio + cenários de classificação — Camada 5
- [x] **Interface local (Camada 6) — ENTREGUE:** `scm/web.py` (Flask, UI de produto) + `predict_match`. Ver [[Como rodar o sistema]].
