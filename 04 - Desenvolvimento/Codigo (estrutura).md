---
tags: [dev, codigo, camada2]
status: vivo
tipo: referencia
data: 2026-06-15
aliases: ["Código", "Estrutura do código"]
---

# Código (estrutura)

O sistema vive em **`scm_analytics/`** na raiz do vault. Python limpo, R$ 0, local. Espelha o [[camada2-baseline-plano-v1|plano do baseline]].

## Árvore
```
scm_analytics/
├── scm/                # pacote
│   ├── __init__.py
│   ├── db.py           # schema SQLite + helpers ([[Esquema SQLite]])
│   ├── ingest.py       # martj42 -> SQLite (idempotente)
│   ├── elo_engine.py   # Elo histórico + σ_R + rating pré-jogo (point-in-time)
│   ├── features_pit.py # features point-in-time (forma, dr_adj, σ_dr) — anti look-ahead
│   ├── predictor.py    # GD/T_m -> Poisson + Elo-direto -> P(V/E/D)+banda + markets()
│   ├── backtest_harness.py # Brier/RPS/LogLoss + IC bootstrap + portão por termo
│   ├── report.py       # calibração (reliability/ECE) + cobertura de banda
│   ├── calibrate.py    # [C2.5] grid treino/teste dos coeficientes + portão de adoção
│   ├── altitude.py     # [C2.5/E1] termo GD_alt (McSharry) + portão por subconjunto
│   ├── heat.py         # [C2.5/E3] WBGT (Open-Meteo) + termo de calor + portão over/under
│   ├── calibrate_confidence.py # confiança ancorada na confiabilidade do backtest
│   ├── estilo.py        # tendência de gols (rejeitado pelo portão, D-23)
│   ├── calibrate_total.py # calibra T_base na Brier de BTTS/over (D-25)
│   ├── predict_match.py # prevê um confronto (Elo atual + mando/altitude)
│   ├── web.py          # INTERFACE WEB local (Flask: página + API /api/predict)
│   └── templates/index.html  # UI (design de produto; sem cara de IA)
├── tests/
│   ├── test_ingest.py        # 5 testes (M1)
│   ├── test_elo_engine.py    # 9 testes (M2)
│   ├── test_features_pit.py  # 6 testes (M3)
│   ├── test_predictor.py     # 9 testes (M4)
│   ├── test_backtest_harness.py # 7 testes (M5)
│   ├── test_report.py        # 6 testes (M6)
│   ├── test_calibrate.py     # 3 testes (C2.5)
│   ├── test_altitude.py      # 3 testes (E1)
│   ├── test_heat.py          # 4 testes (E3)
│   ├── test_predict_match.py # 7 testes (porta da frente + confiança)
│   ├── test_markets.py        # 5 testes (mercados do Poisson)
│   ├── test_calibrate_confidence.py # 4 testes (curva isotônica + versão)
│   ├── test_estilo.py         # 5 testes (estilo + shrinkage + PIT)
│   ├── test_btts_report.py    # 1 teste (viés do BTTS)
│   ├── test_calibrate_total.py # 3 testes (T_base na Brier de BTTS)
│   └── test_web.py           # 4 testes (interface)
├── dados/              # snapshots + scm.sqlite (gerados; .gitignore)
├── requirements.txt
└── README.md
```

## Status dos módulos ([[camada2-baseline-plano-v1]])
| Módulo | Estado | Aceite |
|---|---|---|
| `ingest` | ✅ **pronto** (5/5 + E2E) | contagens · sem nulos · idempotente · neutro |
| `elo_engine` | ✅ **pronto** (9 testes + E2E) | `we(100)=0.64` · mando · zero-sum · point-in-time · idempotente |
| `features_pit` | ✅ **pronto** (6 testes + E2E) | **anti look-ahead** · forma adversário/recência · `dr_adj` · `σ_dr` |
| `predictor` | ✅ **pronto** (9 testes + E2E) | reproduz Poisson manual · P∈[0,1] · propagação determinística · piso de λ |
| `backtest_harness` | ✅ **pronto** (7 testes) | Brier/RPS/LogLoss · IC bootstrap (seed) · portão aceita/rejeita |
| `report` | ✅ **pronto** (6 testes) | reliability bins · ECE · cobertura de banda |
| `calibrate` | C2.5 (3 testes) | grid treino/teste — não adotada (D-17) |
| `altitude` | C2.5/E1 (3 testes) | termo GD_alt — **ADOTADO** (D-18) |
| `heat` | C2.5/E3 (4 testes) | termo de calor — rejeitado (D-19) |
| `predict_match` | porta da frente (4 testes) | prever um confronto (Elo atual) |
| `web` | interface (4 testes) | app Flask local + UI de produto + mercados |
| `calibrate_confidence` | confiança (4 testes) | curva isotônica do backtest → `meta` versionada (D-20/D-24) |
| `estilo` | rejeitado (5 testes) | tendência de gols → portão BTTS cruza zero (D-23) |
| `calibrate_total` | candidato (3 testes) | T_base na Brier de BTTS/over + guarda 1X2 (D-25) |

> **Sistema completo e validado — 86 testes (modelo `baseline-v0.2.1-altitude`).** Baseline + altitude (E1) + `predict_match` + interface web + **mercados** (over/under 0.5–4.5, quem marca 1º, etc.) + **confiança calibrável**. Backtest real: torneios Brier 0,562 batem o uniforme com IC. Guia: [[Como rodar o sistema]].

## Como rodar
```bash
cd scm_analytics
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m scm.ingest --download    # snapshot martj42 (1x, requer rede)
python -m scm.ingest               # -> dados/scm.sqlite (offline)
python -m scm.elo_engine --top 30  # reconstrói o Elo + top-30 (benchmark eloratings)
python -m pytest -q                # testes
```
> **Nota (sandbox):** se uma edição em `.py` não refletir nos testes, limpe o bytecode — `rm -rf scm/__pycache__ tests/__pycache__` (ou rode com `PYTHONDONTWRITEBYTECODE=1`).

## Decisões ligadas
[[Decisoes tecnicas|D-10 a D-13]]: pacote `scm`, idempotência por `natural_key`, pular jogos sem placar, testes sem rede.

## Relacionado
[[CLAUDE]] · [[BACKLOG]] · [[MODELO_FINAL]] · [[Esquema SQLite]] · [[camada2-baseline-plano-v1]]

## Atualização 2026-06-18 — correções do audit externo (v0.3)
Modelo **`baseline-v0.3-altitude`** · **92 testes** (era 86; +6 dos novos recursos). Mudanças (ver [[Decisoes tecnicas]] D-26..D-30, [[Auditoria tecnica externa (2026-06-18)]]):
- `predictor.py` — **curva de empate empírica C1** (`DRAW_CURVE`, `build_draw_curve`; proxy vira fallback); propagação **vetorizada** (quantis da Normal cacheados).
- `backtest_harness.py` — **baseline Elo público** (`elo_baseline_read`, `evaluate_vs_elo`): modelo bate o Elo com IC>0.
- `features_pit.py` / `predict_match.py` — **σ informativo** (`vol_mult`; σ_ajuste da forma real; banda_mando).
- `altitude.py` — **Guadalajara/Zapopan** + normalização de acentos.
- `report.py` — **cobertura de banda por faixa** (`band_coverage_binned`).
- `db.py` — **índices compostos** (home/away, date).
> **Rebuild necessário:** como σ_R e a curva mudaram, rode `features_pit` + `predictor` de novo (a base é gerada; o `scm.sqlite` antigo é v0.2.1).

### 2026-06-18 (b) — mata-mata
`predictor.knockout_advance` (avanço eliminatório) + CLI `predict_match --mata-mata` + toggle na web (`web.py`/`index.html`). **96 testes** (era 92; +4). Releitura do 1X2 (D-31), sem rebuild.

### 2026-06-18 (c) — Camada 5: simulação do torneio
`scm/simulate.py` (Monte Carlo: P de título por seleção) + `dados/copa2026.json` (sorteio, preencher) + página web `/simulacao` (`templates/simulacao.html`, rota em `web.py`). **100 testes** (era 96; +4). Ver [[Decisoes tecnicas]] D-32.

### 2026-06-18 (d) — chaveamento oficial + ε do mata-mata
`simulate.py` agora usa o **chaveamento oficial da FIFA** (R32→final; 3os por elegibilidade do Anexo C). Novo `scm/calibrate_ko.py` calibra o **ε** dos pênaltis com `shootouts.csv` (rodar `--download` na sua máquina). **102 testes** (era 100; +2, incl. as 495 combinações de 3º). D-33.


## ▶ Atualização 2026-06-21 — `baseline-v0.4-ad` (26 arquivos de teste, 137 casos)
Supersede as notas de v0.2/v0.3 acima (históricas; vale `predictor.MODEL_VERSION`).
- **Perna AD não-Elo LIGADA** (`predictor.PredictParams.w_ad=0,50`, afinada por grid+portão): bate o teto do `dr` (major vs lookup +0,0073 IC>0).
- **Simulação usa λ misturado** Elo+AD (`config.SIM_AD_BLEND=0,50`; `simulate.build_ad_lambdas`) — portão major +0,0071/all +0,0050; e **σ propagado** no Monte Carlo.
- **Módulos/recursos novos:** `odds.bench_vs_market` (`scm.odds bench`), `xg.build_from_statsbomb` (`scm.xg build`), `attack_defense.gate_xg_increment` (`--gate-xg`), `config.USE_XG_PRIOR` (xG OFF — portão marginal), `tests/test_skill_regression.py`.
- Rejeitados pelo portão (OFF): T_base, forma saturante (tanh), recalibração 1X2, σ-Glicko, prior de xG.
Detalhe: [[Auditoria + plano de melhorias (modelo, 2026-06-20)]] · [[Evolucao v0.4 - perna AD + sigma no torneio (2026-06-20)]].
