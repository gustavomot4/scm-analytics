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
│   ├── predictor.py      # Poisson + Elo-direto -> P(V/E/D)+banda+markets [M4] (v0.3: altitude)
│   ├── backtest_harness.py  # Brier/RPS/LogLoss + IC + portão          [M5]
│   ├── report.py         # calibração (reliability/ECE) + cobertura    [M6]
│   ├── calibrate.py      # [C2.5] calibração treino/teste (não adotada)
│   ├── altitude.py       # [C2.5/E1] termo GD_alt (ADOTADO)
│   ├── heat.py           # [C2.5/E3] termo de calor (rejeitado)
│   ├── calibrate_confidence.py # confiança ancorada no backtest
│   ├── predict_match.py  # prever um confronto (porta da frente) — forma (D-34) + desfalques (D-41)
│   ├── registrar.py      # [P-G] registro prospectivo: register/settle/report (Brier real da Copa)
│   ├── desfalques.py     # [P-F] Camada 3: ajuste direcional por lesões/suspensões (JSON)
│   ├── dixon_coles.py    # [P-A] candidato τ — TESTADO e REJEITADO pelo portão (OFF)
│   ├── calibrate_1x2.py  # [P-C] candidato recalibração 1X2 — REJEITADO (OFF)
│   ├── sigma_glicko.py   # [P-B] candidato σ Glicko (RD varia) — portão de banda: não adotado (OFF)
│   ├── odds.py           # [P-H] esqueleto de mercado: odds→prob de-vig + 3ª perna do ensemble (0.20)
│   ├── xg.py             # [D-50] esqueleto xG (StatsBomb): team_xg + fator de estilo (candidato OFF)
│   ├── web.py            # interface web local (Flask)
│   └── templates/index.html   # UI (design de produto)
├── tests/                # pytest (sem rede; fixtures) — 26 arquivos de teste (137 casos)
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
python -m scm.predict_match "Mexico" "South Korea" --odds 2.5 3.3 2.8   # mistura mercado (20%) no 1X2
python -m scm.simulate --bracket                     # chaveamento mais provável (a "história")
python -m scm.simulate                               # Monte Carlo: P de título por seleção (rigoroso)
python -m scm.registrar register "Mexico" "South Korea" --date 2026-06-20 --city "Mexico City"
python -m scm.web                                    # interface -> http://127.0.0.1:5000
python -m pytest -q                                  # roda a suíte de testes
```
Guia completo e passo a passo: `../00 - Projeto/Como rodar o sistema.md`.
