---
tags: [dev, audit, resposta]
status: atual
tipo: registro
data: 2026-06-18
aliases: ["Resposta ao audit", "Audit tecnico"]
---

# Resposta ao audit técnico

Resposta ponto a ponto ao `SCM_Analytics_Analise_Tecnica.docx` (auditoria do repositório). O audit é, na maior parte, **correto e útil**. Abaixo, o que foi **corrigido**, o que virou **candidato ao portão**, e o que ficou **no backlog** (com justificativa). Modelo após esta rodada: **`baseline-v0.2.1-altitude`, 86 testes**.

## Corrigido nesta rodada

| Achado | O que era | Correção | Decisão |
|---|---|---|---|
| **P01** | `λ_A+λ_B` deixava de ser `T_m` quando o azarão batia no piso `λ_min` → over/BTTS inflado em massacres | Piso passa a **conservar o total** (desconta do favorito) | [[Decisoes tecnicas\|D-22]] |
| **P10** | Estilo (tendência de gols) estava no contrato mas **hardcoded 1.0** (feature dormente) | Implementado `estilo.py` (shrinkage + cap + PIT); é **candidato ao portão** | [[Decisoes tecnicas\|D-23]] |
| **P09** | Curva de confiança em `meta` **sem versão** → ficava obsoleta em silêncio | Grava `{model, curve}`; `predict_match` sinaliza `reliab_stale` | [[Decisoes tecnicas\|D-24]] |
| **P12** | Sugestão de nome por `LIKE '%xxx%'` (3 letras) | Agora por `difflib.get_close_matches` (ex.: "Brasil"→"Brazil") | [[Decisoes tecnicas\|D-24]] |
| **dúvida BTTS** | "ambos marcam sempre alto" — sem forma de medir | `report --btts`: BTTS **previsto vs real** + viés + reliability | (abaixo) |

## Estilo: rodado pelo portão (e rejeitado)

**Estilo (D-23) — RODADO e REJEITADO.** n=445 jogos: corrige o viés médio do BTTS (50,5%→47,0% vs real 46,7%), mas ΔBrier-BTTS −0,0008 IC[−0,0083,+0,0069] **cruza zero** — ~200 parâmetros por time sem skill por jogo. O portão funcionou. **O achado real:** o viés é **global** (~4pp), então o ajuste certo é 1 parâmetro: o nível de gols **T_base**, calibrado na Brier de BTTS/over (`calibrate_total.py`, D-25), não 200 estilos. Rodar `python -m scm.calibrate_total`.

## Backlog (audit correto, fica para depois — com prioridade)

| Achado | Por que não agora | Prioridade |
|---|---|---|
| **P04** H_host2026=+40 não passou pelo portão | precisa de conjunto de calibração (jogos de Copa em sede de co-anfitrião) | **P1** (já no backlog) |
| **P02** `sigma_ajuste_c=80` não calibrado | adicionar ao grid do `calibrate.py`; afeta banda/confiança | P1 |
| **P08** `draw_prob` é proxy sem base formal | calibrar `draw_base`/`draw_scale` no backtest por fase | P2 |
| **P05** `TEAM_HOME_ALT` cobre 4 seleções | expandir p/ as 48 (Wikidata/Open-Meteo Elevation) | P2 |
| **P11** `θ_alt=0.5` extrapolado de CONMEBOL | testar θ separado p/ CONCACAF (sedes do México) | P2 |
| Dixon-Coles | corrige 0×0/1×1 e a leve superestimação de BTTS; exige reconciliar as duas P(E) | P2 (pós-Copa) |
| Monte Carlo do torneio | maior valor p/ o usuário ("chance de ser campeão") — Camada 5 | P1 (futuro) |

## Qualidade de código (P03/P06/P07) — aceito, baixo impacto

Context managers nas conexões, `conftest.py` compartilhado e `logging` no lugar de `print` são melhorias válidas e de baixo risco; ficam para uma rodada de faxina, sem afetar resultados do modelo.

## Sobre a sua dúvida: o BTTS está sempre alto?

**Em parte é correto, em parte havia o que melhorar.** Para um jogo equilibrado, BTTS = `(1−e^−λ)²`; com `T_base=2.6` e estilo desligado, λ≈1.3 e BTTS≈**53%** — e como o estilo estava dormente, **todo** jogo equilibrado caía nesse mesmo ~53%, sem distinguir times ofensivos de defensivos. A taxa real de "ambos marcam" no futebol de seleções costuma ficar **~46–50%**, então pode haver um viés de alguns pontos para cima, com duas causas: (1) **estilo desligado** (agora implementado, D-23) e (2) **Poisson independente** ignora a correlação negativa entre os gols — o Dixon-Coles corrigiria, e está no backlog. O comando `python -m scm.report --btts --major` **mede** o viés exato. **Já medido (n=445 torneios): 50,5% previsto vs 46,7% real (~4pp alto).** O estilo corrige a média mas não passa o portão (D-23); o ajuste certo é global, 1 parâmetro: `python -m scm.calibrate_total` (T_base, D-25). Dixon-Coles fica como refino pós-Copa.

## Relacionado
[[Decisoes tecnicas]] · [[MODELO_FINAL]] · [[Codigo (estrutura)]] · [[Como rodar o sistema]] · [[BACKLOG]]
