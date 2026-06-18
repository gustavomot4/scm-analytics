---
tags: [projeto, stack, tecnologia]
status: atual
tipo: especificacao
data: 2026-06-15
aliases: ["Tech Stack", "Stack"]
---

# TECH STACK — escolhas (uma por componente)

Tudo **gratuito, local, auditável**. Sem APIs pagas, sem hospedagem, sem servidor. Python é a língua única.

| Componente | Escolha | Por quê (1 linha) |
|---|---|---|
| Linguagem | **Python 3.11+** | ecossistema científico maduro, legível, auditável |
| Cálculos matemáticos | **NumPy** | vetoriza Poisson/Elo/bootstrap; rápido sem peso de framework |
| Estatística pontual | **`math` (stdlib)** + SciPy só se preciso | Poisson/logística fecham em stdlib; evita dependência grande |
| Manipulação de dados | **pandas** | ETL tabular padrão; lê CSV/JSON do snapshot trivialmente |
| Armazenamento local | **SQLite (`sqlite3` stdlib)** | banco em arquivo, zero servidor, SQL auditável ([[Esquema SQLite]]) |
| Coleta de dados | **`requests` p/ baixar snapshot + arquivos locais** | baixa 1×, grava em disco; **nada lê a internet no cálculo** |
| CLI | **`argparse` (stdlib)** | zero dependência extra, totalmente auditável; ergonomia suficiente |
| Testes | **pytest** | padrão de fato; abriga o **teste anti look-ahead** (crítico, [[camada2-baseline-plano-v1]] M3) |
| Visualização | **Matplotlib** | gera reliability diagrams e cobertura de banda, gratuito |
| Interface web | **Flask** | app local mínimo p/ a interface gráfica (`scm.web`); sem servidor externo |
| Ambiente | **venv + `requirements.txt` (versões pinadas)** | reprodutível sem o overhead de Docker |
| Versionamento | **Git (local)** | histórico auditável; casa com o plugin [[Plugins recomendados|Obsidian Git]] |

## Não usar (e por quê)
- **APIs pagas** (Sportmonks, API-Football, iSports…) → viola custo R$ 0.
- **ML/boosting (sklearn/xgboost), PyMC** → overfit/auditabilidade (decisão [[Decisoes tecnicas|D-02]]).
- **ORM pesado / Postgres / Docker** → complexidade desnecessária para um banco em arquivo local.
- **Scrapers de ToS restritivo** (FBref/Transfermarkt) → só consulta manual; snapshot.

## Relacionado
[[MODELO_FINAL]] · [[Fontes gratuitas]] · [[camada2-baseline-plano-v1]] · [[CLAUDE]]
