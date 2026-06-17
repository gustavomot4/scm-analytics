---
tags: [camada2, baseline, plano]
status: atual
tipo: plano
data: 2026-06-15
aliases: ["Plano do baseline"]
---

# Camada 2 — Plano de implementação do BASELINE congelado
**Projeto:** Sistema de previsão de partidas — Copa do Mundo 2026
**Baseline:** Elo (+ `H_hist` + mando + σ_R) → `GD=f(dr)`, `T_m=g(dr)·estilo` → Poisson → leitura Elo-direto propagada → métricas
**Consome:** [[camada1-planejamento-v5]] (v5.0) · [[camada1-apendice-formas-v5]] · [[camada2-planejamento-v1]]
**Data:** 2026-06-15 · **Status:** **PLANO de implementação (ainda sem código de sistema)** · **Custo-alvo:** R$ 0 · **Versão:** v1

> **Isto é o plano, não a corrida.** Descreve **como** construir o baseline (módulos, fluxo, ordem, testes, aceite) para quando você der o "ok" de escrever código de sistema. O pseudocódigo abaixo é **ILUSTRATIVO**; a lógica do laço/portão foi **validada num exemplo-brinquedo** (§6, rodado em código). O baseline é o **passo 1** da ordem de calibração ([[camada2-planejamento-v1]] §3.3): mede o motor **antes** de qualquer fator ambiental. Princípio: nada de ML; tudo auditável, local, reprodutível, R$ 0.

---

## 0. Escopo do baseline (o que ENTRA e o que NÃO entra)

**ENTRA (mínimo que se sustenta sozinho):**
- Elo histórico reconstruído com `H_hist` (todo jogo não-neutro), `K`/`G` do contrato, inicialização 1500, provisório < 30 jogos.
- `σ_R` por seleção; `σ_ajuste` de forma; `σ_dr` por RSS.
- Mando: `H_host2026` para anfitrião / 0 neutro — **mas sujeito ao portão** (não é dado de graça; §5).
- Forma (janela 10, ajustada a adversário) → `R'`.
- `GD=f(dr)`, `T_m=g(dr)·estilo` com **formas e placeholders do apêndice** (θ=0.45; T_base=2.6, κ=0.10; ou saturante).
- Poisson 0..10 → V/E/D, over 2.5, BTTS, top-k (**Poisson-condicionais**, nota A1).
- Leitura **Elo-direto propagada inteira** (curva de empate restrita C1 + cap por amostra) + banda 16/84.
- Confiança (`g_rating`) e o **harness de backtest** (métricas, bootstrap, calibração).

**NÃO entra (vem depois, cada um atrás do portão — C2.5+):** altitude (E1), calor (E3), piso de bola parada (E4), banda de mando como termo livre, fuso/descanso em σ (E5/E6), xG/Dixon-Coles, afinação dos pesos do ensemble, mercado de previsão. **Razão:** o baseline tem de provar que o **motor** bate o trivial **antes** de adicionar graus de liberdade.

---

## 1. Stack e princípios (R$ 0, local, auditável)
- **Python 3.x** + **`sqlite3` (stdlib)** + **numpy/pandas** (livres) + **matplotlib** (reliability diagrams).
- **Nenhuma dependência paga; nada lê a internet no cálculo** — ingestão grava um **snapshot** em disco; o backtest roda offline sobre o SQLite.
- **Reprodutível:** seed fixa no bootstrap; `hash_inputs` por predição; versão de dados carimbada.
- **Auditável:** sem ML/boosting/bayes hierárquico (decisão de projeto). Cada saída rastreável a fórmula + dado.

---

## 2. Arquitetura de módulos (6 unidades pequenas e testáveis)

| # | Módulo | Responsabilidade | Entrada → Saída |
|---|---|---|---|
| M1 | `ingest` | martj42 + fixturedownload → SQLite normalizado (schema C2 §2.3) | CSV/JSON → tabelas `matches/teams/venues` |
| M2 | `elo_engine` | reconstrução cronológica do Elo (H_hist, K, G), σ_R, provisório<30 | `matches` → `ratings_pit` |
| M3 | `features_pit` | montar features **só com jogos < t** (Elo, forma, desvio, σ_dr) | `ratings_pit`+`matches` → `features_pit` |
| M4 | `predictor` | pipeline **congelado**: dr→GD/T_m→Poisson→leitura Elo-direto propagada→V/E/D+banda+confiança | `features_pit` → `predictions` |
| M5 | `backtest_harness` | walk-forward, Brier/RPS/LogLoss, bootstrap pareado, **portão por termo**, calibração/cobertura | `predictions`+resultados → métricas |
| M6 | `report` | tabelas por `versao_modelo`, reliability diagrams, cobertura da banda | métricas → relatório/arquivos |

Acoplamento baixo: cada módulo tem contrato de I/O via tabelas SQLite — testável isolado.

---

## 3. Fluxo e o laço walk-forward (ILUSTRATIVO — validado §6)

```
ingest → SQLite → elo_engine(cronológico) → features_pit(< t) → predictor(congelado) → harness → report
```
```python
# ILUSTRATIVO (não é o sistema). O ponto crítico: prever ANTES de atualizar.
elo = {t: 1500.0 for t in teams}
for m in matches_ordenados_por_data:          # cronológico = point-in-time
    feat = features_pit(m, usando_apenas=jogos_antes_de(m.date))   # anti look-ahead
    dr   = feat.elo_a - feat.elo_b + mando(m)
    GD   = f(dr) + 0                           # baseline: sem GD_alt (altitude OFF)
    T_m  = g(dr) * estilo_a * estilo_b         # baseline: sem (1-κ_heat·calor)
    lamA, lamB = (T_m+GD)/2, (T_m-GD)/2
    pred = poisson_e_leitura_elo_direto(lamA, lamB, dr, feat.sigma_dr)   # V/E/D + banda
    registrar(pred)                            # imutável
    elo = atualiza_elo(elo, m.resultado, dr)   # SÓ DEPOIS de prever
```
O teste anti look-ahead (M3) é o **mais importante do build**: um vazamento de futuro inflama o Brier silenciosamente e invalida tudo.

---

## 4. Ordem de build incremental (menor incremento testável primeiro)

| Marco | Entrega | Teste de "feito" |
|---|---|---|
| **M1** | ingestão + schema | contagens batem; sem nulos em chaves; flag neutro presente; idempotente |
| **M2** | motor Elo | sanidade `dr=100→W_e≈0.64`, `dr=300→0.85`; **benchmark vs eloratings.net ±25 nas top-30** (snapshot manual) |
| **M3** | features point-in-time | **teste anti look-ahead dedicado**: nenhuma feature de `m` usa jogo com data ≥ `t(m)` |
| **M4** | preditor congelado | `P(V),P(E),P(D)∈[0,1]` e somam 1 em todo `dr`; reproduz uma execução manual do repo (ex.: URU×KSA/IRN×NZL) dentro de tolerância |
| **M5** | harness | Brier < uniforme num holdout com IC; bootstrap pareado; **portão rejeita termo nulo** (validado no toy, §6) |
| **M6** | relatório | reliability bins (≥20/faixa); cobertura da banda calculável |

Cada marco é um PR pequeno, com teste, antes do próximo.

---

## 5. Testes e critério de aceite do baseline

**Por módulo:** unidade (M2 sanidade Elo; M4 coerência [0,1]; M3 anti look-ahead) + integração (laço completo num torneio).

**Aceite do baseline** (subconjunto dos invariantes de [[camada2-planejamento-v1]] §5 aplicáveis sem fatores ambientais):
1. **Brier < uniforme (0.667)** com IC bootstrap que **não cruza** o baseline; e **≤ Elo público** (não significativamente pior).
2. **P(V), P(D) ∈ [0,1]** em todo |dr| observado.
3. **Confiança não-crescente com σ_dr** (`g_rating` monótono).
4. **Cobertura da banda nominal — na leitura Elo-direto** (A2), não no ensemble.
5. **σ_dr calibrado isoladamente** (B4): variância empírica dos erros por faixa bate com σ_R/σ_ajuste.

**Mando passa pelo MESMO portão.** O `H_host2026` (e qualquer banda de mando) **não é assumido** — entra como termo candidato e só fica se ΔBrier pareado tiver IC que não cruza zero. No exemplo-brinquedo (§6) o portão **rejeitou** um mando fabricado, como deve. Em dados reais com anfitrião, espera-se que sobreviva — mas é o backtest que decide, não o decreto.

---

## 6. Validação da lógica do harness (exemplo-brinquedo, rodado em código)

Para não apoiar o plano em pseudocódigo não testado, rodei um **toy** (60 jogos sintéticos, 8 times) exercitando o laço:
- **Walk-forward point-in-time:** prever com Elo corrente, atualizar depois.
- **Brier = 0.637 < uniforme 0.667** (o Elo bate o trivial mesmo no ruído sintético).
- **Invariante P(x) ≥ 0** mantido (min 0.157).
- **Portão por termo:** ΔBrier(sem − com mando), bootstrap pareado B=10⁴ → **IC95 cruza zero** → **não adicionar** mando (correto: o dataset não tem mando real). O portão **não** adiciona ruído.

*É exemplo-brinquedo, não dado real — valida a **lógica**, não o modelo. Os números reais saem do backtest histórico quando o código existir.*

---

## 7. Riscos específicos do build (declarar)
- **Vazamento de futuro (point-in-time):** o bug mais perigoso e silencioso — mitigado pelo teste anti look-ahead dedicado (M3) e por construir features só de `jogos < t`.
- **martj42 atrasa por PR / eloratings.net é SPA:** ambos resolvidos por **snapshot local** (eloratings só para sanidade, 1× pré-build).
- **Amostra pequena / tail ruidoso:** ICs largos em |dr| alto; minnows mal calibrados → relatar incerteza, não esconder.
- **Reprodutibilidade:** seed do bootstrap e hash de inputs obrigatórios; sem eles, métricas não são auditáveis.
- **Tentação de afrouxar o portão** ao ver Brier alto: proibido — o portão e o controle de comparações múltiplas ([[camada2-planejamento-v1]] §6) são inegociáveis.

---

## 8. Definição de pronto e handoff
**Pronto =** os 5 critérios de aceite (§5) cumpridos no conjunto de teste intocado, relatório gerado por `versao_modelo`, e **coeficientes do baseline congelados** (θ, κ, T_base, σ_R/σ_ajuste/σ_ref, tabela `P_E(dr)`) gravados para a Camada 4. **Só então** abre-se a **C2.5** (altitude+calor juntos → piso → σ de fuso/descanso → xG/DC), cada termo atrás do portão.

---
*Plano de implementação do baseline da Camada 2 — v1, **sem código de sistema** (pseudocódigo só ilustra; lógica validada em exemplo-brinquedo). Escrever os módulos é o próximo passo, sob pedido explícito. Consome v5.0 + apêndice + design da C2. Stack R$ 0/local/auditável. Probabilidades, nunca certezas — e o baseline tem de bater o trivial antes de ganhar qualquer engrenagem nova.*
