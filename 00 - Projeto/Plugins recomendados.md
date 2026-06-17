---
tags: [projeto, obsidian, plugins]
status: atual
tipo: referencia
data: 2026-06-15
aliases: ["Plugins"]
---

# Plugins recomendados (Obsidian)

Todos gratuitos. Justificativa **ligada a este projeto**, não genérica.

| Plugin | Para quê aqui | Prioridade |
|---|---|---|
| **Kanban** | renderiza o [[BACKLOG]] como quadro arrastável (P0/P1/P2 por raia) | essencial |
| **Dataview** | consultas vivas sobre o frontmatter que já padronizamos (`status`, `tipo`, `tags`) — ex.: listar modelos da V1, ou análises aguardando resultado | essencial |
| **Templater** | template para nova [[06 - Analises\|análise de jogo]] (`AAAA-MM-DD-COD-x-COD`) e para notas de modelo — padroniza frontmatter | alta |
| **Obsidian Git** | versiona o vault automaticamente; casa com o Git local da [[TECH_STACK]] e protege o [[Registro de previsoes\|registro imutável]] | alta |
| **Obsidian Charts** | plota reliability diagram / Brier ao longo do tempo direto da nota, quando o backtest rodar | média (pós-baseline) |
| **Callout/Admonition** | destacar o aviso recorrente "probabilidades, nunca certezas" e blocos `[a calibrar]` | baixa |

## Exemplos de Dataview (já funcionam com o frontmatter atual)

Análises ainda sem resultado:
````
```dataview
TABLE data, status FROM "06 - Analises" WHERE status = "aguardando-resultado" SORT data
```
````

Modelos que entram na V1:
````
```dataview
LIST FROM "02 - Modelos" WHERE contains(status, "V1")
```
````

Itens de planejamento históricos vs atuais:
````
```dataview
TABLE status, tipo FROM "01 - Planejamento" SORT status
```
````

## Relacionado
[[Indice]] · [[BACKLOG]] · [[TECH_STACK]]
