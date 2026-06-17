---
tags: [dados, fontes, gratis]
status: atual
tipo: dados
data: 2026-06-15
---

# Fontes gratuitas (R$ 0)
Tudo público/gratuito, snapshot local; **nada lê a internet no momento do cálculo**.

| Fonte | Dado | Papel | Limite honesto |
|---|---|---|---|
| **martj42/international_results** | resultados 1872–2026 (torneio, neutro) | base do [[Elo]] + V/E/D realizado | atualização por PR (lag) |
| **fixturedownload** | calendário | descanso/fuso ([[Incerteza e propagacao]]) | só jogos |
| **StatsBomb Open Data** | xG + tipo de jogada | [[xG preditivo]] + piso de [[Ajustes ambientais|bola parada]] | **só 2018/2022/Euro/WWC**; não-comercial; histórico |
| **Open-Meteo (Archive+Elevation)** | clima histórico + altitude | calor/altitude ([[Ajustes ambientais]]) | uso não-comercial |
| **Wikidata** | elevação de estádio + data do técnico | altitude "de casa"; regime → σ_R | semiestruturado |
| **eloratings.net** | Elo benchmark | sanidade (±25 top-30) | SPA, sem API → snapshot manual |
| **Kalshi / Polymarket** | preço de mercado (prospectivo) | benchmark do [[Ensemble]] | **sem histórico**; captura manual |

**Lacunas declaradas (não inventar):** odds históricas gratuitas de seleção; árbitro individual; xG ao vivo das 48; lesões estruturadas. **APIs pagas = fora de escopo.**

## Relacionado
[[Esquema SQLite]] · [[Referencias]] · [[camada2-planejamento-v1]] §2 · [[TECH_STACK]]
