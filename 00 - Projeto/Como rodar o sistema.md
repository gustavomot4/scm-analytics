---
tags: [projeto, guia, uso]
status: atual
tipo: guia
data: 2026-06-17
aliases: ["Como rodar", "Guia de uso", "Manual"]
---
# Como rodar o sistema (do zero ao resultado)

Guia completo e prático. Tudo roda **local e offline** (a única coisa que usa a internet é baixar a base, 1×). Código em `scm_analytics/`. Detalhe dos módulos: [[Codigo (estrutura)]].

## 0. Pré-requisitos (instalar 1×)
- **Python 3.11+** — Windows: `winget install Python.Python.3.12`. **Feche e reabra o terminal** depois (o PATH só atualiza em janela nova). Confirme com `python --version` (ou `py --version`).
- **Git** (opcional, para versionar) — já configurado se você clonou de `gustavomot4/scm-analytics`.

## 1. Ambiente
Na pasta `scm_analytics`:
```
cd scm_analytics
python -m venv .venv
.venv\Scripts\Activate.ps1          # Windows PowerShell  (Linux/Mac: source .venv/bin/activate)
pip install -r requirements.txt     # numpy, pandas, matplotlib, requests, flask, pytest
```
> Se o PowerShell bloquear o Activate: `Set-ExecutionPolicy -Scope Process RemoteSigned` (vale só nessa janela), ou use `.venv\Scripts\python` no lugar de `python`.

## 2. Construir a base (pipeline)
Cada comando é **idempotente** (pode repetir):
```
python -m scm.ingest --download     # baixa o histórico do martj42 (~49k jogos) -> dados/results.csv  [requer rede, 1x]
python -m scm.ingest                # normaliza -> dados/scm.sqlite
python -m scm.elo_engine --top 30   # reconstrói o Elo cronológico + mostra o top-30
python -m scm.features_pit          # features point-in-time (forma, dr_adj, σ_dr)
python -m scm.predictor             # gera as previsões (modelo baseline-v0.2-altitude)
```
Pronto — a base e as previsões estão no `dados/scm.sqlite`.

## 3. Validar (opcional, mostra que o modelo tem skill)
```
python -m scm.backtest_harness --major   # Brier vs uniforme com IC (jogos de torneio)
python -m scm.report --major             # calibração (reliability) + cobertura de banda
python -m scm.calibrate_confidence       # ancora a confiança na confiabilidade medida (grava em meta)
python -m scm.report --btts --major      # diagnóstico do 'ambos marcam' (previsto vs real)
python -m scm.estilo                      # PORTÃO do estilo (tendência de gols) na Brier de BTTS
```
Esperado: Brier ~0,56 **< uniforme 0,667 com IC que não cruza zero**, bem calibrado. O `calibrate_confidence` imprime a curva de acerto por faixa e mostra que **confiança alta = mais acerto**.

## 4. Prever um jogo
**No terminal:**
```
python -m scm.predict_match "Brazil" "Argentina"               # sede neutra
python -m scm.predict_match "Mexico" "Germany" --city "Mexico City"   # aplica altitude (E1)
python -m scm.predict_match "United States" "England" --mando 40      # vantagem de anfitrião 2026
```
Nomes em inglês (padrão martj42); se errar, o programa sugere ("Brasil" → "Brazil").

A saída traz P(V/E/D)+banda, **over/under 0.5–4.5**, ambos marcam, **não sofrer gol**, **quem marca primeiro**, dupla chance, handicap, placares prováveis e a **confiança** (0–100). Tudo sai do mesmo Poisson — ver [[MODELO_FINAL]] §4.

**Na interface gráfica (navegador):**
```
python -m scm.web                   # abre http://127.0.0.1:5000
```
Digite as duas seleções (autocompleta), escolha a sede e clique em Prever. Ctrl+C para sair.

## 5. Atualizar com jogos recentes
O sistema usa um **snapshot** (não se atualiza sozinho — ver [[Decisoes tecnicas]] D-03). Para pegar jogos novos, re-rode 3 comandos (idempotente, só adiciona o que é novo):
```
python -m scm.ingest --download ; python -m scm.ingest ; python -m scm.elo_engine ; python -m scm.features_pit ; python -m scm.predictor
```
Depois, `predict_match`/`web` já usam o Elo atualizado. (Para automatizar, agende no Agendador de Tarefas do Windows.)

## 6. Testes
```
python -m pytest -q                 # 83 testes
```
> Quirk de sandbox: se uma edição `.py` não refletir, `rm -rf scm/__pycache__ tests/__pycache__`.

## Resumo dos comandos
| Objetivo | Comando |
|---|---|
| Instalar deps | `pip install -r requirements.txt` |
| Construir base | `ingest --download` → `ingest` → `elo_engine` → `features_pit` → `predictor` |
| Validar | `backtest_harness --major` · `report --major` · `calibrate_confidence` |
| Prever (terminal) | `predict_match "TimeA" "TimeB" [--city ... | --mando N]` |
| Prever (interface) | `web` → http://127.0.0.1:5000 |
| Atualizar | `ingest --download` → `ingest` → `elo_engine` |
| Testar | `pytest -q` |

## Opcional — re-testar fatores (C2.5)
- Coeficientes: `python -m scm.calibrate --cutoff 2018-01-01` (mantido v0.1 — D-17).
- Altitude: `python -m scm.altitude` (**adotada** — D-18).
- Calor: `python -m scm.heat --build-climatology` (lento) → `python -m scm.heat` (**rejeitado** — D-19).
- **Estilo (tendência de gols):** `python -m scm.estilo` roda o portão (Brier de BTTS); `python -m scm.estilo --list` lista as seleções mais ofensivas/defensivas. Preview num jogo: `predict_match "A" "B" --estilo`. Candidato — D-23.
- **BTTS enviesado?** `python -m scm.report --btts --major` compara o 'ambos marcam' previsto com o real.
- Confiança: `python -m scm.calibrate_confidence` ancora a confiança no backtest (**adotado** — D-20).

## Problemas comuns
- **"Python não encontrado"** → não instalado ou terminal não reaberto após o `winget install`.
- **`ModuleNotFoundError`** (numpy/flask/requests) → faltou `pip install -r requirements.txt`.
- **"snapshot não encontrado"** / **"SQLite não existe"** → rode o passo 2 na ordem.
- **`gh`/`python` não reconhecido logo após instalar** → reabra o terminal.

Ver também: [[MODELO_FINAL]] (o que o sistema calcula) · [[Backtest baseline (resultados)]] (validação) · [[CLAUDE]] (contexto).
