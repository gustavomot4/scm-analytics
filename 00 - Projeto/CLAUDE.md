---
tags: [projeto, contexto, onboarding]
status: atual
tipo: contexto
data: 2026-06-15
aliases: ["Contexto do projeto", "Onboarding"]
---

# CLAUDE.md — contexto do projeto (leia isto primeiro)

## Objetivo (3 linhas)
Sistema **local e gratuito** que prevê partidas da Copa 2026 entregando **probabilidades V/E/D, gols esperados e confiança** — nunca certezas.
Motor matemático auditável (Elo → Poisson → ensemble), validado por **backtest histórico** antes de qualquer uso.
**Não é ferramenta de aposta**; Brier ~0.60 não é vantagem.

## Estado atual
**Planejamento (congelado):** contrato matemático **v5.0** ([[camada1-planejamento-v5]]), auditado ([[camada1-revisao-v5]]) e autocontido ([[camada1-apendice-formas-v5]]); design do backtest ([[camada2-planejamento-v1]]); plano de build ([[camada2-baseline-plano-v1]]); 9 execuções manuais ([[06 - Analises]]); registro imutável ([[Registro de previsoes]]).
**Código (Camada 2, em andamento):** módulos `ingest`, `elo_engine`, `features_pit`, `predictor` e **`backtest_harness`** (Brier/RPS/LogLoss + IC bootstrap + **portão por termo**) implementados e testados (**36/36**) — ver [[Codigo (estrutura)]]. Próximo: `report` (último do baseline).
**Falta:** `report` (reliability diagrams + cobertura de banda). O backtest **roda** com dados reais na máquina do usuário (martj42 via `--download`); até lá, as métricas são exercitadas em testes. Parâmetros `[a calibrar]`.

## Decisões tomadas (resumo — detalhe em [[Decisoes tecnicas]])
- Contrato congelado v5.0; mudar fórmula = nova versão.
- **Sem ML/bayes hierárquico** (auditabilidade/overfit). **Custo R$ 0, roda local.**
- **Portão de backtest:** nada entra em λ/dr sem IC que não cruza zero.
- **Baseline primeiro** (Elo+mando+σ_R→Poisson), depois fatores ambientais atrás do portão.
- Stack: Python + NumPy/pandas + SQLite + pytest ([[TECH_STACK]]).

## Restrições não negociáveis
1. **Zero custo** — sem APIs/bases/hospedagem pagas.
2. **Roda local** — nada lê a internet no cálculo (snapshot em disco).
3. **Probabilidades, nunca certezas** — inclusive sobre o próprio modelo.
4. **Registro pré-jogo imutável** — nunca reescrever linha gravada ([[Registro de previsoes]]).
5. **Não inventar dados/fontes** — lacunas declaradas ficam declaradas.

## Mapa das notas-chave
- Visão: [[Indice]] · este [[CLAUDE]] · [[MODELO_FINAL]] · [[TECH_STACK]] · [[BACKLOG]] · [[Plugins recomendados]]
- Contrato: [[camada1-planejamento-v5]] · [[camada1-apendice-formas-v5]] · [[camada1-revisao-v5]]
- Modelos: [[Elo]] · [[Poisson]] · [[Incerteza e propagacao]] · [[Ensemble]] · [[Mando de campo]] · [[Ajustes ambientais]] · [[Confianca]]
- Execução: [[camada2-planejamento-v1]] · [[camada2-baseline-plano-v1]] · [[Decisoes tecnicas]]
- Dados: [[Fontes gratuitas]] · [[Esquema SQLite]] · [[Registro de previsoes]]

## Como rodar e testar
Código em `scm_analytics/` (ver [[Codigo (estrutura)]]). Pipeline `ingest → elo_engine → features_pit → predictor` funcionando:
```
cd scm_analytics
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m scm.ingest --download     # baixa snapshot martj42 (1x, na sua máquina)
python -m scm.ingest                # -> dados/scm.sqlite (offline)
python -m scm.elo_engine            # reconstrói o Elo
python -m scm.features_pit          # features point-in-time
python -m scm.predictor             # previsões -> tabela predictions
python -m pytest -q                 # 29 testes
```
Detalhe e status dos módulos: [[Codigo (estrutura)]].

## ▶ Próxima tarefa a executar
**[P1] Relatório (`report`)** — **último módulo do baseline**. Reliability diagrams + cobertura de banda a partir das saídas do `backtest_harness` (matplotlib). Card em [[BACKLOG