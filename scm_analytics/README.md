# scm_analytics/ — sistema (motor + interface)

Código Python do sistema de previsão. Documentação completa no vault Obsidian (raiz):
**`00 - Projeto/Como rodar o sistema.md`** (guia de uso), `CLAUDE.md`, `MODELO_FINAL.md`.

## Estrutura
```
scm_analytics/
├── scm/
│   ├── db.py             # schema SQLite + helpers
│   ├── ingest.py         # martj42 -> SQLite (idempotente)            [M1]
│   ├── elo_engine.py     # Elo histórico + sigma_R + rating pré-jogo   [M2]
│   ├── features_pit.py   # features point-in-time (anti look-ahead)    [M3]
│   ├── predictor.py      # Poisson + Elo-direto -> P(V/E/D)+banda+markets [M4] (v0.2: altitude)
│   ├── backtest_harness.py  # Brier/RPS/LogLoss + IC + portão          [M5]
│   ├── report.py         # calibração (reliability/ECE) + cobertura    [M6]
│   ├── calibrate.py      # [C2.5] calibração treino/teste (não adotada)
│   ├── altitude.py       # [C2.5/E1] termo GD_alt (ADOTADO)
│   ├── heat.py           # [C2.5/E3] termo de calor (rejeitado)
│   ├── calibrate_confidence.py # confiança ancorada no backtest
│   ├── predict_match.py  # prever um confronto (porta da frente)
│   ├── web.py            # interface web local (Flask)
│   └── templates/index.html   # UI (design de produto)
├── tests/                # pytest (sem rede; fixtures) — 73 testes
├── dados/                # snapshots + scm.sqlite (gerados; .gitignore)
└── requirements.txt
```

## Uso rápido
```bash
cd scm_analytics
python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m scm.ingest --download && python -m scm.ingest && python -m scm.elo_engine && python -m scm.features_pit && python -m scm.predictor
python -m scm.predict_match "Brazil" "Argentina"     # prever no terminal
python -m scm.web                                    # interface -> http://127.0.0.1:5000
python -m pytest -q                                  # 73 testes
```
Guia completo e passo a passo: `../00 - Projeto/Como rodar o sistema.md`.
