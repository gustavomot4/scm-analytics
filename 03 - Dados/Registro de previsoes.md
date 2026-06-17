---
tags: [dados, registro, imutavel]
status: atual
tipo: dados
data: 2026-06-15
---

# Registro de previsões (CSV imutável)
Arquivo: `registro-previsoes.csv` (nesta mesma pasta). **Append-only, separador `;`.**

## Regra inegociável
Registrar **antes do kickoff** e **nunca editar** linha já gravada — sem isso, qualquer métrica de validação é autoengano. Migração de esquema (→ tabela `predictions`, ver [[Esquema SQLite]]) é da Camada 2; linhas antigas **não** são reescritas, ficam marcadas por `versao_modelo`.

## Colunas
`match_id ; timestamp_utc ; fase ; time_a ; time_b ; elo_a_aj ; elo_b_aj ; dr ; lambda_a ; lambda_b ; p_v ; p_e ; p_d ; p_over25 ; p_btts ; top5_placares ; confianca ; desfalques ; odds_1x2 ; versao_modelo`

> over/BTTS/placares são **Poisson-condicionais** ([[Poisson]], achado A1).

## Relacionado
[[Esquema SQLite]] · [[06 - Analises]] (execuções) · contrato [[camada1-planejamento-v5]] §15
