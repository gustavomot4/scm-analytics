---
tags: [projeto, indice, home]
status: atual
tipo: indice
data: 2026-06-15
aliases: ["Início", "Home", "Mapa do vault"]
---

# 🏠 Índice — Sistema de previsão Copa 2026

Vault de **planejamento e execução** de um sistema local e gratuito de previsão de partidas. **O sistema está construído e validado** (modelo `baseline-v0.2.1-altitude`). Para usar: [[Como rodar o sistema]]. Para o contexto: [[CLAUDE]].

## Portas de entrada
- 🧭 [[CLAUDE]] — contexto completo (objetivo, estado, decisões, próxima tarefa)
- 🎯 [[MODELO_FINAL]] — o que a V1 calcula
- 🛠 [[TECH_STACK]] — stack escolhida
- [[Como rodar o sistema]] — guia de uso completo (instalar → prever → interface)
- [[BACKLOG]] — quadro Kanban (estado consolidado)
- 🔌 [[Plugins recomendados]] — plugins do Obsidian

## Estrutura do vault
```
00 - Projeto/        contexto, modelo final, stack, índice
01 - Planejamento/   contrato v5 + históricos (v1–v4) + auditorias + pesquisa
02 - Modelos/        uma nota por bloco matemático
03 - Dados/          fontes, esquema SQLite, registro imutável
04 - Desenvolvimento/ backlog, decisões, design do backtest, plano do baseline
05 - Referencias/    papers e fontes externas
06 - Analises/       execuções manuais de jogo (9)
scm_analytics/       código do sistema (Python: motor + interface)
```

## Modelos ([[02 - Modelos]])
[[Elo]] · [[Poisson]] · [[Forma recente]] · [[Forca ofensiva-defensiva]] · [[Mando de campo]] · [[Desfalques direcionais]] · [[Incerteza e propagacao]] · [[Ensemble]] · [[Ajustes ambientais]] · [[Confianca]]

## Contrato e execução
[[camada1-planejamento-v5]] (atual) · [[camada1-apendice-formas-v5]] · [[camada1-revisao-v5]] (auditoria) · [[camada1-lacunas]] (pesquisa) · [[camada2-planejamento-v1]] (backtest) · [[camada2-baseline-plano-v1]] (build) · [[Codigo (estrutura)]] (código) · [[Decisoes tecnicas]]

## Previsões registradas ([[06 - Analises]])
| Data | Jogo | Favorito (ensemble) | Conf. | Modelo | Resultado |
|---|---|---|---|---|---|
| 2026-06-12 | [[2026-06-12-CAN-x-BIH\|CAN x BIH]] | Canadá 59.9% | 62 | v0.1 | — |
| 2026-06-15 | [[2026-06-15-BEL-x-EGY\|BEL x EGY]] | Bélgica 62.0% | 67 | v2.0 | — |
| 2026-06-15 | [[2026-06-15-ESP-x-CPV\|ESP x CPV]] | Espanha 89.8% | 82 | v2.0 | — |
| 2026-06-15 | [[2026-06-15-URU-x-KSA\|URU x KSA]] | Uruguai 67.6% (60–74%) | 57 | v2.1→v3.0 | — |
| 2026-06-15 | [[2026-06-15-IRN-x-NZL\|IRN x NZL]] | Irã 54.2% (48–60%) | 53 | **v5.0** | — |
| 2026-06-21 | [[2026-06-21-ESP-x-KSA\|ESP x KSA]] | Espanha 90.0% | 69 | v3.0-prelim | — |
| 2026-06-21 | [[2026-06-21-URU-x-CPV\|URU x CPV]] | Uruguai 67.2% | 48 | v3.0-prelim | — |
| 2026-06-26 | [[2026-06-26-CPV-x-KSA\|CPV x KSA]] | aberto: CPV 37/E 30/KSA 33 | 34 | v3.0-prelim | — |
| 2026-06-26 | [[2026-06-26-ESP-x-URU\|ESP x URU]] | Espanha 72.9% | 55 | v3.0-prelim | — |

*Linhas `*-prelim` são antecipadas e não entram na validação morning-of. Resultados a preencher após os jogos.*
