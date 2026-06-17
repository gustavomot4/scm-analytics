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
│   ├── predictor.py    # GD/T_m -> Poisson + Elo-direto propagado -> P(V/E/D)+banda
│   ├── backtest_harness.py # Brier/RPS/LogLoss + IC bootstrap + portão por termo
│   ├── report.py       # calibração (reliability/ECE) + cobertura de banda
│   └── calibrate.py    # [C2.5] grid treino/teste dos coeficientes + portão de adoção
├── tests/
│   ├── test_ingest.py        # 5 testes (M1)
│   ├── test_elo_engine.py    # 9 testes (M2)
│   ├── test_features_pit.py  # 6 testes (M3)
│   ├── test_predictor.py     # 9 testes (M4)
│   ├── test_backtest_harness.py # 7 testes (M5)
│   ├── test_report.py        # 6 testes (M6)
│   └── test_calibrate.py     # 3 testes (C2.5)
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

> **🎉 Baseline 6/6 completo (42 testes, pipeline E2E).** Próximo marco: rodar o backtest com **dados reais** (martj42), o aceite de fato. Ver [[BACKLOG]].

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
