---
tags: [dev, comparacao, modelo, mercado, opta, ea]
status: atual
tipo: analise
data: 2026-06-20
aliases: ["Comparacao com o mercado", "Modelo vs Opta vs EA"]
---

# Comparação do modelo (v0.4) com mercado, Opta e EA Sports — Copa 2026

Comparação da previsão de título do **`baseline-v0.4-ad`** (Monte Carlo, 8.000 sims, com os 32
jogos de grupo já disputados travados) contra o **mercado** (casas, 20/06), o **supercomputador
Opta** (pré-torneio, 25k sims) e o **EA Sports FC 26** (pré-torneio). Probabilidade, nunca certeza.

## 1. Os números (P de ser campeão)

| Seleção | **Modelo v0.4** | Opta (pré) | Mercado (impl. bruta†) | EA FC 26 |
|---|---:|---:|---:|---|
| Argentina | **18,2% (1º)** | 10,4% (4º) | 11,1% (4º, +800) | finalista‑tipo |
| Spain | 15,1% (2º) | **16,1% (1º)** | 15,4% (2º, +550) | **CAMPEÃO** |
| France | 11,0% (3º) | 13,0% (2º) | **21,3% (1º, +370)** | — |
| England | 8,4% (4º) | 11,2% (3º) | 14,3% (3º, +600) | — |
| **Colombia** | **6,5% (5º)** | fora do top‑8 | baixa | — |
| Brazil | 5,1% (6º) | 6,6% (6º) | 8,3% (6º, +1100) | — |
| Portugal | **2,5% (11º)** | 7,0% (5º) | 9,1% (5º, +1000) | — |
| Mexico (anfitrião) | **3,3% (8º)** | 1,0% (20º) | baixa | — |

† Mercado: probabilidade implícita **sem remover o overround** (o book de título de 48 seleções
soma ~150%); vale a **ordem** e a magnitude relativa, não o nível absoluto. FanDuel, 20/06.

## 2. "EA, não FIFA" — o que é e o histórico (honesto)

O previsor com o famoso retrospecto **não é a FIFA** (a entidade não prevê campeão; e o **ranking
FIFA** nº1 **não** venceu as últimas Copas — Bélgica/Brasil eram nº1 antes de 2018/2022 e não
ganharam). É o **EA Sports FC** (ex‑"FIFA", o videogame), que simula a Copa com elencos licenciados:
- **Acertou 4 campeões seguidos:** Espanha 2010, Alemanha 2014, França 2018, **Argentina 2022** — e
  os **dois finalistas** nessas 4 edições. Errou a Euro 2024 (cravou Inglaterra; Espanha venceu).
- **Ressalva estatística:** é uma **previsão pontual** (o campeão modal), não probabilidade calibrada.
  Os 4 campeões eram todos **favoritos do topo** — qualquer bom modelo os tinha entre os 1ºs; acertar
  o modal 4×, com ~15‑20% no topo, é impressionante mas **amostra pequena** (mistura skill + o
  favorito de fato vencer). O forte do EA é o **dado de elenco/jogador** (ratings, química).

**Para 2026 o EA crava a Espanha** — ou seja, **discorda do seu modelo** (que crava Argentina).
Opta e mercado também põem Espanha/França à frente da Argentina. Seu modelo é o **único** com
Argentina como favorita clara.

## 3. Onde o modelo concorda e onde diverge

**Concorda (bom sinal):** o topo — Argentina, Espanha, França, Inglaterra, Brasil — é o mesmo de
todos. O modelo está na vizinhança certa.

**Diverge — e cada divergência aponta a MESMA lacuna (qualidade de elenco):**
1. **Argentina 1º (só o modelo).** O modelo é **Elo+forma puro**; a Argentina tem o **maior Elo**
   (2210, campeã, eliminatórias CONMEBOL fortes). Opta/EA pesam **qualidade de elenco/idade/xG** e
   preferem a Espanha (talento jovem). O mercado já reagiu à **notícia** (Espanha tropeçou com Cabo
   Verde → caiu; França bateu Senegal → subiu) — algo que o modelo não "vê". Não é claramente um
   **erro** (Argentina é um 1º defensável), mas ser o **único dissidente** é uma bandeira amarela.
2. **Colombia 5º (6,5%) — o OUTLIER.** Ninguém mais tem a Colômbia no top‑5; o mercado põe o Brasil
   **muito** à frente. É o **Elo inflado** pelas eliminatórias CONMEBOL **sem correção de elenco**.
   É a evidência mais concreta de erro do modelo.
3. **Portugal 11º (2,5%) — subestimado.** Opta/mercado: 5º (~7‑9%). O modelo não enxerga o elenco
   (Ronaldo & cia.) e ainda dá só 76,5% de avanço (grupo K). Mesma cegueira de elenco, ao contrário.
4. **México 8º (3,3%) — anfitrião superestimado.** Opta: 20º (1%). O modelo dá **+40 de mando ao
   anfitrião** + **altitude (CDMX)** na fase de grupos. Casa com o achado do bench (modelo
   superestimou o **Canadá**, 72% vs mercado 53%): **o modelo super‑rateia mandante/anfitrião.**

## 4. O que dá para melhorar (priorizado pela evidência da comparação)

1. **Sinal de QUALIDADE DE ELENCO — a peça que falta (e o que o EA tem).** É a causa‑raiz de 3 das
   4 divergências (Colômbia ↑, Portugal ↓, Espanha vs Argentina). Caminho **já montado**: o **prior
   de xG na perna AD** (`scm.attack_defense --xg-prior`, precisa do CSV do StatsBomb) — xG é o proxy
   gratuito/auditável mais próximo do "rating de elenco". **Maior alavanca** para chegar perto do EA
   sem violar as restrições (R$0, local, sem ML opaco).
2. **Misturar o mercado (já montado).** O mercado encapsula notícia/lesão/elenco que o modelo não vê
   e reagiu ao tropeço da Espanha. O blend de 0,20 (`predict_match --date`/`odds bench`) puxa para o
   consenso. Capturar odds de título e blendar **moderaria** o viés Argentina‑pesado e o Colômbia.
3. **Revisar o bônus de anfitrião (+40) e a altitude no torneio.** Bench (Canadá) **e** sim (México
   8º vs Opta 20º) apontam **super‑rateio de mandante**. O +40 é `[a calibrar]` sem jogos de
   anfitrião no backtest → é juízo. Sugestão: testar +20/+30 e medir no registro prospectivo da Copa
   (não há portão histórico possível — é decisão declarada).

## 5. Conclusão

O seu modelo está **no consenso no topo** e é **honesto** (probabilidade calibrada + backtest +
portão) — coisa que nem o EA (previsão pontual) nem o mercado (com vig) entregam. **Mas** ele é
**Elo‑cego para elenco**, e é exatamente aí que o EA/Opta ganham: a Colômbia inflada, o Portugal
afundado e o anfitrião super‑rateado são todos o mesmo buraco. **Não dá para "virar o EA"** sem dado
de jogador (que o EA tem do próprio jogo) — mas dá para **fechar a maior parte do gap** com o que já
está encaixado: **xG (elenco) + mercado**. Quem está certo sobre Argentina×Espanha em 2026, só a
Copa dirá — e **um resultado não decide** (precisa de muitas Copas); a vantagem do seu modelo é dar
**probabilidade calibrada**, não cravar um nome.

*Comparação 2026-06-20. Números do modelo: `scm.simulate` (8k sims, v0.4). Opta/EA/mercado: busca web
(pré‑torneio p/ Opta/EA; mercado de 20/06). Probabilidades, nunca certezas.*

---

## Experimento executado 2026-06-21 — sinal de GOLS no λ da simulação (ADOTADO)

**Problema:** a simulação do título usava só `lambdas(dr)` (**Elo puro**) — cega para gols/elenco.
Por isso destoava (Spain/Colômbia/Portugal/anfitrião). A perna AD (gols, não-Elo) existia, mas só
no ensemble de **1 jogo**, não na simulação.

**Experimento:** misturar a λ da perna AD no λ que a sim amostra: `λ = (1−α)·λ_Elo + α·λ_AD`.

**Portão** (poisson_reads do blend vs Elo-só, histórico, IC bootstrap):
- Sweep de α: Brier major **0,5588 (α=0) → 0,5502 (α=1)**; mínimo em todos os jogos ≈ α=0,5.
- **Adotado α=0,5:** major **ΔBrier +0,00712 IC[+0,00474, +0,00960]**; todos **+0,00497
  IC[+0,00430, +0,00562]**. Passa com folga — **o maior ganho de todo este trabalho** (a sim
  deixava o sinal de gols inteiro na mesa). Ligado em `config.SIM_AD_BLEND = 0.5`.

**Efeito na P(campeão) — Elo-só → +AD(0,5):**

| Seleção | Elo-só | +AD(0,5) | Δ | vs Opta/mercado |
|---|---:|---:|---:|---|
| Argentina | 18,2 | **18,1** | ≈0 | segue 1º (era o único a cravar Argentina) |
| Spain | 15,1 | **9,9** | −5,2 | **DISCORDA** de Opta(1º)/EA(campeão): os gols não sustentam |
| England | 8,4 | 9,2 | +0,8 | ~consenso |
| France | 11,0 | 8,9 | −2,1 | ainda alto |
| Brazil | 5,1 | **7,6** | +2,5 | rumo ao consenso (Elo subestimava o ataque) |
| Colombia | 6,5 | 7,5 | +1,0 | segue alta — Copa América 2024 a **defende** |
| Germany | 3,6 | 5,3 | +1,7 | rumo ao consenso |
| Portugal | 2,5 | 3,2 | +0,7 | rumo ao consenso (Opta 5º) |
| Mexico (anf.) | 3,3 | 2,8 | −0,5 | corrige parte do super-rateio de anfitrião |

**Leitura honesta:** o blend move por **gols reais**, não por reputação de elenco. Concorda com o
consenso onde o Elo subestimava o ataque (Brasil/Portugal/Alemanha ↑) e **corrige** o anfitrião
(México ↓). **Discorda** do EA/Opta na Espanha (eles amam o elenco; os gols recentes da Espanha não
sustentam 1º) e **mantém** a Colômbia (os gols dela na Copa América a defendem). É uma visão
**informada por gols e validada no histórico** (+0,0071) — divergência **defensável**, não erro. Só
a Copa decide; um resultado não fecha a conta.

**Importante (escopo):** isto muda a **simulação** (engine de λ, validado pelo portão). O modelo de
**1 jogo** (`predict_match`/`predictor`, v0.4-ad) **não muda** — ele já usava a perna AD no ensemble.

---

## Experimento (b) 2026-06-21 — mercado no λ da simulação: ESTRUTURALMENTE INVIÁVEL

Tentativa: blendar o mercado no λ da sim, **igual à perna AD**. **Não dá, por construção:**
- A perna **AD** gera λ p/ **qualquer** par (de ratings de ataque/defesa) → cobre toda a árvore.
- O **MERCADO** só precifica jogos **agendados**. A sim precisa de λ p/ **1.128** pares possíveis e
  p/ um mata-mata **hipotético** (ex.: Morocco×Norway numa quarta) que o mercado **nunca** precificou.
- Cobertura do mercado p/ as necessidades da sim: **~1,1%** (12 jogos disputados / 1.128 pares).

**Veredito: não há portão a rodar** — o sinal não existe para a maioria dos confrontos (não é que
falhou o IC; é que o dado não existe). O lugar **validado** do mercado é a **previsão de 1 jogo**
(`predict_match`, peso 0,20, já ligado) e ele cresce de forma **operacional** (capturar odds +
`odds bench` a cada rodada). Opção cosmética (não-validável, não recomendo embutir): misturar a
**tabela final** de título 80/20 com as odds de título do mercado — isso é "concordar com o
mercado", não um ganho de modelo.
