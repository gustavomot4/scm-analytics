# scm_analytics/ — sistema (Camada 2)

Código Python do baseline. Documentação completa no vault Obsidian (raiz): ver
`00 - Projeto/CLAUDE.md`, `00 - Projeto/MODELO_FINAL.md` e
`04 - Desenvolvimento/camada2-baseline-plano-v1.md`.

## Estrutura
```
scm_analytics/
├── scm/                # pacote
│   ├── db.py           # schema SQLite + helpers
│   ├── ingest.py       # martj42 -> SQLite (idempotente)            [M1]
│   ├── elo_engine.py   # Elo histórico + σ_R + rating pré-jogo       [M2]
│   ├── features_pit.py # features point-in-time (anti look-ahead)    [M3]
│   └── predictor.py    # Poisson + Elo-direto -> P(V/E/D)+banda      [M4]
├── tests/              # pytest (sem rede; fixtures) — 29 testes
├── dados/              # snapshots + scm.sqlite  (gerados; .gitignore)
└── requirements.txt
```

## Setup (R$ 0, local)
```bash
cd scm_analytics
python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Pipeline
```bash
python -m scm.ingest --download    # baixa o snapshot do martj42 (1x, requer rede)
python -m scm.ingest               # -> dados/scm.sqlite (offline)
python -m scm.elo_engine --top 30  # Elo + top-30 (benchmark eloratings)
python -m scm.features_pit         # features point-in-time
python -m scm.predictor            # previsões -> tabela predictions
```

## Testes
```bash
python -m pytest -q
```
> Se uma edição em `.py` não refletir, limpe o bytecode: `rm -rf scm/__pycache__ tests/__pycache__`.

## Próximo módulo
`backtest_harness` — walk-forward, Brier/RPS/LogLoss, bootstrap pareado, portão por termo. Ver `../04 - Desenvolvimento/BACKLOG.md`.
