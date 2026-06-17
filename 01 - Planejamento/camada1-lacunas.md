---
tags: [camada1, pesquisa, fatores]
status: concluido
tipo: pesquisa
data: 2026-06-15
aliases: ["Pesquisa de lacunas"]
---

# Camada 1 — Lacunas de Cobertura: Fatores de Alto Impacto (pesquisa de expansão)
**Projeto:** Sistema de previsão de partidas — Copa do Mundo 2026
**Modelo de referência:** [[camada1-planejamento-v4]] (v4.0, contrato atual)
**Data:** 2026-06-15 · **Status:** pesquisa (sem código) · **Custo-alvo:** R$ 0

> Convenções herdadas (V/E/D, λ, dr, σ_dr, T_m, GD, **[a calibrar]**). Esta pesquisa **não** altera o contrato congelado — ela levanta **evidência externa** para fatores ainda não cobertos (ou cobertos sem fonte citada) e diz, sem inflar, **o que tem dado gratuito e o que não tem**. Marcadores de público: 🎲 apostador · 🧠 treinador · 📐 matemático. Severidade de prioridade: 🟢 entra já (dado grátis + evidência forte) · 🟡 candidato (atrás do portão de backtest) · 🔴 descartar/declarar lacuna (sem dado grátis viável). **Toda fonte citada foi recuperada da web em 2026-06-15** (lista no fim). Princípio do projeto mantido: probabilidades, nunca certezas — e nenhum fator entra em λ sem passar no portão de IC-que-não-cruza-zero.

> **Nota de honestidade (leia primeiro):** boa parte dos fatores abaixo **já está listada como diagnóstico na v4** (§3.11), porém **sem fonte e sem magnitude**. O valor desta pesquisa é (a) trazer a **evidência citável** que faltava, (b) **afinar** o que a v4 mede de forma grosseira (ex.: viagem em km → *direção/fuso*; altitude "Cidade do México" → *diferencial quantificado*), e (c) declarar com clareza as **lacunas reais** (árbitro individual). Onde a evidência **valida a escolha atual da v4** (ex.: técnico novo = mais incerteza, não bounce), isso é dito explicitamente.

---

## 0. Resumo executivo

Dos seis grupos investigados, **três fatores têm evidência forte E dado gratuito** e merecem entrar como ajuste calibrável (não como nova perna do ensemble): **altitude diferencial** (efeito quantificado em paper revisado por pares), **calor/estresse térmico** (relevante e específico para 9 das 16 sedes de 2026) e **mando mediado por árbitro/torcida** (o experimento natural dos "jogos-fantasma" da COVID mostra que a vantagem de casa é, em boa parte, viés de arbitragem — o que para uma Copa em sede majoritariamente neutra **reduz** o mando esperado). Três têm evidência forte mas **dado só parcial/histórico**: **xG** e **bolas paradas** (StatsBomb, sem cobertura ao vivo das 48 seleções) e **fuso/circadiano** (derivável, mas efeito pequeno e fácil de overfittar). Dois são **insights de transparência** mais que termos de λ: **importância da partida / jogo-morto** e **rivalidade/clássico**. Um é **lacuna declarada**: **tendência individual do árbitro** (sem fonte estruturada gratuita confiável para árbitros internacionais). Um **confirma a escolha da v4 e não vira termo**: **"efeito técnico novo"** (a evidência aponta regressão à média, não bounce → a v4 já trata como **mais incerteza**, não como deslocamento do ponto).

Nenhum desses fatores vira **membro do ensemble**. Eles entram **a montante** (ajuste de `λ` via `T_m`/`GD`, de `dr`, ou de `σ`/confiança). Os pesos do ensemble (Poisson/Elo/mercado) **não mudam** por causa deles — só mudam por backtest com ≥30 jogos (§6).

---

## 1. Fatores de alto impacto identificados (com fonte/evidência)

| # | Fator | Categoria | Evidência (resumo) | Magnitude | Já na v4? |
|---|---|---|---|---|---|
| F1 | **Altitude diferencial** | Ambiental/Físico | McSharry 2007 (BMJ): ~**½ gol de saldo por 1000 m** de diferença de altitude; P<0.001 | Forte, **quantificada** | Parcial (só "Cidade do México", sem magnitude) |
| F2 | **Calor / estresse térmico** | Ambiental | 9/16 sedes 2026 em "risco extremo"; calor **reduz ritmo, pressing e total de gols**; FIFA impôs pausas | Moderada, específica de 2026 | Sim, diagnóstico (sem fonte) |
| F3 | **Mando mediado por árbitro/torcida** | Psicológico/Arbitragem | Jogos-fantasma COVID: mando caiu (Bundesliga **48,2%→32,5%** de vitórias em casa); faltas contra o mandante **+26%** sem torcida; Garicano: árbitro manipula acréscimos a favor da casa | Forte (experimento natural) | Implícito em `H_host2026` (sem a leitura "é viés de árbitro") |
| F4 | **xG / xGA** | Tático | xG é **melhor preditor de resultados futuros que gols** (PLOS One 2023; replicação ASA 2022) | Forte | Sim, backtest/prior (StatsBomb) |
| F5 | **Bolas paradas (eficiência/dependência)** | Tático | ~**27% dos gols** da Premier 2025-26 vêm de bola parada (sem pênalti); escanteios 17,5% | Forte (tendência crescente) | Sim, papel novo na v4 (D7) |
| F6 | **Viagem: direção/fuso (circadiano)** | Físico/Fadiga | Jet lag **pior para leste** que oeste; ressincroniza ~1 h/dia; jogadores cruzando 7 fusos a leste dormem menos | Pequena-moderada, **direcional** | Parcial (v4 mede **km**, não direção/fuso) |
| F7 | **Descanso diferencial / congestão** | Físico/Fadiga | <5 dias entre jogos ↑ lesão (Dupont 2010; revisão sistemática 2022); 2 dias é insuficiente | Efeito **no risco/lesão**, não direto no placar | Sim, diagnóstico |
| F8 | **Importância da partida / jogo-morto** | Contextual | "Seasonal Pacing": jogos importantes têm **+4% corridas rápidas, +16% duelos, +36% faltas**; jogo-morto → menos intensidade / time B | Moderada (intensidade) | Sim, via **cenários determinísticos** |
| F9 | **Rivalidade / clássico** | Contextual/Psicológico | Clássicos **reduzem a vantagem de casa** e elevam cartões (estudos de derby) | Pequena, contextual | Não |
| F10 | **Técnico novo (regime)** | Psicológico | "New manager bounce" é majoritariamente **regressão à média** (Ter Weel: efeito médio ~zero) | Efeito no ponto ~zero; **sobe a incerteza** | Sim — v4 trata como **σ**, não bounce ✅ |
| F11 | **Tendência individual do árbitro** | Arbitragem | Árbitros variam em cartões/pênaltis; viés de casa documentado (Garicano) | Real, mas… | **Lacuna** (ver §4) |
| F12 | **Ordem no pênalti (mata-mata)** | Psicológico | Apesteguia-Palacios-Huerta 2010: **60:40** para quem bate 1º — **mas replicações divergem** (Kocher 53:47; Vollmer 2024 sem efeito) | **Incerta/contestada** | Sim — v4 já usa ε≈0.03 [a calibrar] ✅ |

### Detalhe por fator

**F1 — Altitude diferencial (🟢 entra já · 🎲🧠📐).** O paper de McSharry (BMJ, 2007), sobre **1.460 jogos** sul-americanos em mais de um século, encontra que cada **1000 m de diferença de altitude** entre o mando do time e o do adversário muda o saldo esperado em **~½ gol**, com times de baixa altitude rendendo abaixo do esperado na altitude (efeito P<0.001). É a evidência mais limpa e **quantificada** desta pesquisa. Para 2026 importa **Cidade do México (~2.240 m), Guadalajara (~1.560 m) e Monterrey (~540 m)** vs. seleções de planície. A v4 só tem um flag genérico de "Cidade do México"; o paper permite **um termo de GD calibrado pelo diferencial**.

**F2 — Calor / estresse térmico (🟡 candidato → 🟢 p/ confiança · 🎲🧠).** Cobertura de imprensa especializada (The Conversation, Sky Sports, Al Jazeera) e a própria FIFA (pausas de hidratação obrigatórias) convergem: o calor **baixa o ritmo, reduz o pressing e tende a derrubar o total de gols**. **Nove das 16 sedes** estão em faixa de "risco extremo". Não achei um paper com um coeficiente "−X gols por °C WBGT" gratuito e revisado — então a magnitude é **declaradamente estimada**, e o fator entra primeiro em `T_m` (total) e na confiança, atrás do portão.

**F3 — Mando é, em boa parte, viés de árbitro (🟢 entra já como *redução* do mando · 🎲📐).** O experimento natural dos jogos sem torcida (COVID) é a evidência mais forte do conjunto: uma **revisão de 26 estudos** não achou **nenhum** caso de mando *aumentado* sem torcida, e a maioria achou mando **reduzido ou fortemente reduzido**; na Bundesliga as vitórias de casa caíram de **48,2% para 32,5%**, e as **faltas marcadas contra o mandante subiram ~26%** sem público (Nature, Scientific Reports). Garicano et al. (NBER) já mostravam que o árbitro **encurta o jogo quando a casa ganha e alonga quando a casa perde**. **Implicação direta para 2026:** numa Copa em sede **majoritariamente neutra**, a vantagem de casa "clássica" **não se aplica** — e mesmo o `H_host2026` dos anfitriões deve ser tratado como **parcialmente um efeito de arbitragem/torcida**, possivelmente **menor que os +60 Elo** assumidos, porque o público de Copa é mais misto que o de um clássico de liga.

**F4 — xG/xGA (🟡 já previsto, evidência reforça prioridade · 🎲🧠📐).** Múltiplas fontes (PLOS One 2023; replicação da American Soccer Analysis, 2022; trabalho seminal de Caley/IJtsma 2015) confirmam que **xG prediz pontos futuros melhor que gols**. Isso **justifica** usar xG como **prior de estilo** (menos ruidoso que gols brutos) e como régua de backtest — exatamente o papel que a v4 reserva ao StatsBomb. Limite honesto: **não há xG ao vivo gratuito para as 48 seleções** (StatsBomb é histórico).

**F5 — Bolas paradas (🟡 candidato forte · 🎲🧠).** A imprensa de dados (Opta/The Analyst, bet365) mostra que **~27% dos gols** da Premier 2025-26 saíram de bola parada sem pênalti (escanteios sozinhos = 17,5%), tendência **em alta**. Importa para o projeto porque ataca um erro já detectado à mão: **ESP×CPV BTTS 22% (modelo) vs ~40% (mercado)** — o modelo é severo demais com o ataque do azarão, que costuma marcar **justamente em bola parada**. Entra como **piso de λ do azarão** calibrado por propensão de bola parada (StatsBomb).

**F6 — Viagem: direção e fuso, não km (🟡 candidato · 🧠📐).** A literatura de cronobiologia (Reilly et al., PubMed 9631214; revisão de Botonis 2025) é clara: o que pesa é **cruzar fusos, e para leste é pior** (ressincroniza ~1 h por dia). A v4 mede **distância em km** (haversine) — métrica **errada**: o sinal correto é o **deslocamento de fuso com sinal** (leste/oeste) e dias para ressincronizar. Refinamento de graça (coordenadas → fuso). Efeito pequeno e fácil de overfittar → entra como modificador de confiança/σ antes de λ.

**F7 — Descanso diferencial / congestão (🟡 como risco, não como placar · 🧠📐).** Dupont (2010) e a revisão sistemática de 2022 mostram que **<5 dias** de recuperação elevam **lesão**, não necessariamente derrubam o resultado diretamente. Honestidade: o efeito comprovado é em **risco de lesão e fadiga acumulada**, não num coeficiente de placar. Logo entra melhor como **σ_ajuste / robustez de confiança** (incerteza de desempenho sob fadiga) do que como termo de λ. Casa com o `σ_ajuste` que a v4 introduziu (D3).

**F8 — Importância / jogo-morto (🟡 transparência · 🎲🧠📐).** O estudo "Seasonal Pacing" mede **+4% corridas rápidas, +16% duelos, +36% faltas** em jogos importantes vs. de baixa importância; jogo-morto → menos intensidade e/ou time reserva. O modelo **não prevê motivação** (risco irredutível, já declarado), mas a v4 já transforma isso em **cenários de classificação determinísticos** ("quem precisa de quê"). A evidência **valida** manter como flag/insight, não como termo de λ.

**F9 — Rivalidade / clássico (🟡 baixa prioridade · 🎲🧠).** Estudos de derby mostram que clássicos **reduzem a vantagem de casa** e elevam cartões/agressividade. Em Copa, "rivalidade" são pares históricos (ARG-BRA, ENG-GER, etc.), definíveis **à mão**. Efeito pequeno e ruidoso; candidato de baixa prioridade, mais como **flag de variância** (cartões, jogo truncado) que como ajuste de P(V).

**F10 — Técnico novo (✅ confirma a v4, não vira termo · 📐).** A análise pública (Football365, Soccer Analytics; trabalho de Ter Weel) aponta que o "new manager bounce" é, **em média, regressão à média** — efeito ~zero no ponto. **Isso valida a decisão da v4** de tratar técnico recente como **aumento de σ_R** (regime novo = rating mais incerto), **não** como deslocamento do favoritismo. Nenhuma mudança necessária; só registrar a evidência.

**F11 — Árbitro individual (🔴 lacuna, ver §4 · 🎲📐).** O viés de casa do árbitro é real (Garicano), mas o **dado por árbitro** (taxa de cartões/pênaltis) para **árbitros internacionais**, em fonte **gratuita e estruturada**, **não existe de forma confiável** — as escalações saem ~2 dias antes e o histórico por árbitro está espalhado em sites com ToS restritivo. Declarado como lacuna.

**F12 — Ordem no pênalti (✅ confirma a v4 · 🎲📐).** A vantagem "60:40" de Apesteguia-Palacios-Huerta (2010) **não se replicou de forma robusta** (Kocher 2012: 53:47; Vollmer 2024: sem efeito em 1.759 disputas). Conclusão honesta: o efeito é **incerto/contestado** → manter o pênalti praticamente como **moeda** e o ε≈0.03 [a calibrar] da v4, sem inflar.

---

## 2. Viabilidade de cálculo com dados gratuitos (por fator)

| Fator | Dado grátis hoje? | Fonte | Como derivar | Limite honesto |
|---|---|---|---|---|
| F1 Altitude | **Sim** | Open-Meteo Elevation + coords das sedes; altitude "de casa" de cada seleção | diferencial = elev(sede) − elev(casa do time) | efeito medido na América do Sul; extrapolar p/ outras confederações com cautela |
| F2 Calor | **Sim** | Open-Meteo (histórico desde 1940 + previsão 16 dias), WBGT aproximável | temp/umidade no horário do jogo por sede | sem coeficiente publicado grátis → magnitude estimada |
| F3 Mando/árbitro | **Sim (derivado)** | flag de anfitrião + literatura | reduzir/condicionar `H_host2026`; tratar como banda | efeito de torcida não se separa do de arbitragem no dado |
| F4 xG | **Parcial** | StatsBomb Open Data (WC 2018/2022, Euro, WWC) | prior de estilo + backtest | **não cobre as 48 seleções nem é ao vivo**; licença não-comercial |
| F5 Bola parada | **Parcial** | StatsBomb (tipo de jogada por gol) | % de gols de bola parada por seleção | mesma cobertura histórica do StatsBomb |
| F6 Fuso/direção | **Sim** | coords das sedes + casa do time → offset de fuso (base tz gratuita) | Δfuso com sinal (leste/oeste) + dias p/ ressincronizar | efeito pequeno; risco de overfit |
| F7 Descanso | **Sim** | fixturedownload (calendário já em mãos) | dias desde o último jogo; diferencial entre os dois | evidência é de **lesão**, não de placar |
| F8 Importância | **Sim** | calendário + classificação parcial | cenários determinísticos de avanço | motivação em si não é observável |
| F9 Rivalidade | **Sim (manual)** | pares de rivalidade definidos à mão | flag binário/ordinal | subjetivo; amostra pequena |
| F10 Técnico novo | **Sim** | Wikidata (data de nomeação) — já proposto na v4 (D7) | semanas no cargo → σ_R | — |
| F11 Árbitro | **Não (confiável)** | — | — | **sem fonte gratuita estruturada p/ árbitros internacionais** |
| F12 Pênalti ordem | **Sim (irrelevante)** | — | manter ε pequeno | efeito contestado |

---

## 3. Como cada fator se integra ao modelo existente

Princípio: **nenhum vira perna do ensemble**; todos entram a montante, com **cap** e atrás do **portão de backtest** (IC que não cruza zero). Mapeamento ao pipeline da v4 (§8):

```
# AJUSTES DE λ (entram em GD/T_m, passos 3–6 da §8 do v4):
F1 altitude:   GD += θ_alt · (Δaltitude_km)          # θ_alt ancorado em ~0.5 gol/1000 m (McSharry), [a calibrar] p/ não-CONMEBOL
F2 calor:      T_m *= (1 − κ_heat · excesso_WBGT)     # calor alto reduz o TOTAL; cap pequeno; [a calibrar]
F5 bola parada: λ_azarão = max(λ_azarão, piso(propensão_bola_parada))   # corrige o BTTS-do-azarão subestimado

# AJUSTES DE dr / MANDO (passos 1–2):
F3 mando:      H_host2026 ← revisar p/ baixo e publicar como BANDA (parte é arbitragem; nulo em sede neutra)

# AJUSTES DE σ / CONFIANÇA (não mexem no ponto — §3.12 e §14 do v4):
F6 fuso:       σ_ajuste += f(Δfuso_leste)             # leste pesa mais
F7 descanso:   σ_ajuste += f(dias<5, diferencial)     # fadiga = mais incerteza, não placar
F10 técnico:   σ_R       += f(semanas_no_cargo)        # JÁ na v4 (D7) — evidência confirma
F9 rivalidade: robustez  −= ε_derby                    # mais cartões/variância

# SAÍDAS DE TRANSPARÊNCIA (não entram em λ):
F8 importância: cenários determinísticos de classificação (já na v4, §6-insights)
F12 pênalti:    P(avança) = P(V)+P(E)·(0.5+ε·sinal(dr)), ε pequeno [mantido]

# DIAGNÓSTICO/PRIOR (backtest):
F4 xG:         prior de estilo (substitui gols brutos onde houver StatsBomb) + régua de calibração
```

Observação de modelagem (📐): F1 e F2 agem em **direções potencialmente opostas no tail** — altitude pode **aumentar** o saldo do time aclimatado, calor tende a **reduzir** o total. Não somar cegamente; calibrar **juntos** e com a forma de `GD`/`T_m` (que a v4-D2 já manda escolher por dados), senão um cancela o outro sem evidência.

---

## 4. Fatores descartados (sem dado gratuito viável) e por quê

- **F11 — Tendência individual do árbitro (cartões/pênaltis).** O efeito é real e citável (Garicano), mas **não há fonte gratuita e estruturada** de estatística por árbitro para o corpo de arbitragem **internacional** da Copa. Escalações saem ~2 dias antes; bases por árbitro (Transfermarkt/worldfootball) têm **ToS restritivo** e cobertura irregular de seleções. **Não inventar** um "índice de rigor" sem base. Reabordar só se a FIFA publicar histórico estruturado (improvável a tempo).
- **Posse de bola e distância percorrida.** Sem fonte gratuita estruturada para seleções; posse descreve estilo, não resultado (reafirmado das rodadas anteriores).
- **Tipo de grama (natural × sintético).** Praticamente **neutralizado**: a FIFA exige **grama natural** em Copas (sedes com sintético recebem grama temporária), então não é fator diferenciador em 2026. Sem estudo gratuito específico citável aqui → não modelar (declarado, não inventado).
- **xG ao vivo das 48 seleções.** Existe StatsBomb **histórico**, não feed gratuito ao vivo das 48 — o uso fica em backtest/prior, não em previsão ao vivo.
- **Métricas de tracking (sprints, aceleração) por seleção.** Sem fonte gratuita pública para seleções; descartado.

---

## 5. Relevância por público (apostador / treinador / matemático)

| Fator | 🎲 Apostador | 🧠 Treinador | 📐 Matemático |
|---|---|---|---|
| F1 Altitude | value em jogos de altitude (mercado subprecifica) | gestão de aclimatação/rodízio | coeficiente publicado e testável (raro) |
| F2 Calor | over/under e ritmo; props de total | pacing, hidratação, banco | efeito de interação com horário/sede |
| F3 Mando/árbitro | **calibrar mando real em sede neutra** (não pagar "casa" que não existe) | leitura de pressão/arbitragem | experimento natural limpo (COVID) p/ identificar o efeito |
| F4 xG | detectar over/under-performance vs mercado | qualidade de chance criada/cedida | melhor preditor → baseline de validação |
| F5 Bola parada | corrigir BTTS/again-scorer do azarão | treino de bola parada = arma do azarão | piso de λ principiado p/ amostra pequena |
| F6 Fuso | edge pequeno em jogos transcontinentais | janela de treino/sono | direcionalidade (leste≠oeste) testável |
| F7 Descanso | fade do time congestionado | carga e rotação | confunde com lesão; cuidado causal |
| F8 Importância | **jogo-morto é onde o mercado erra mais** | poupar titulares com segurança | risco não-modelável → cenários, não ponto |
| F9 Rivalidade | mais cartões/under em clássicos | gestão emocional | amostra pequena; variância |
| F10 Técnico novo | não pagar "bounce" que é ruído | — | regressão à média (caso-escola) |
| F11 Árbitro | (se houvesse dado) props de cartões | disciplina | **lacuna de dados** |

Leitura rápida: para **apostadores**, os de maior valor são **F3 (mando real em sede neutra)**, **F8 (jogo-morto)** e **F5 (BTTS do azarão)** — onde o mercado erra com mais frequência. Para **treinadores**, **F1/F2/F7** (gestão física) e **F5** (arma de bola parada). Para **matemáticos**, **F4 (xG como régua)**, **F3 (identificação causal limpa)** e **F10/F12** (casos clássicos de regressão à média / efeito contestado que disciplinam o modelo a **não** inventar sinal).

---

## 6. Atualização proposta dos pesos do ensemble

**Posição honesta: os pesos do ensemble não mudam por causa destes fatores.** Eles ajustam `λ`, `dr` e `σ` **a montante** — entram **dentro** das leituras Poisson e Elo, não como novas leituras. Mudar pesos pré-backtest seria overfitting (a v4 já fixa: pesos finos só com ≥30 jogos).

Estrutura atual (v4, mantida):

| Componente | Peso c/ odds | Peso s/ odds |
|---|---|---|
| P_poisson | 0.45 | 0.56 |
| P_elo (propagado) | 0.35 | 0.44 |
| P_mercado | 0.20 | 0.00 |

Ajustes **defensáveis** ligados a esta pesquisa (todos atrás do portão):

1. **Mercado (F3-adjacente):** quando houver **mercado de previsão multiagente** (Kalshi/Polymarket, já proposto na v4-D7), ele é benchmark mais forte que 1 casa → **candidato** a subir o peso de mercado de 0.20 para ~0.25 **se** o backtest mostrar melhor calibração. Não antes.
2. **3ª leitura independente (xG/AD):** se o gerador ataque/defesa entrar com **prior de xG/gols (não-Elo)** — a única forma de ser de fato independente (v4-D5) —, os pesos passam a ~**0.35 / 0.25 / 0.20 / 0.20** (Poisson / Elo / AD / mercado). Só nesse caso a **tabela de pesos** muda.
3. **Tudo o mais (F1, F2, F5, F6, F7, F9):** **não** altera pesos; altera os **inputs** das leituras existentes, com cap e gate.

Em resumo: a "atualização de pesos" honesta é **condicional** (mercado de previsão e/ou P_ad independente), não uma redistribuição nova fator-a-fator.

---

## 7. Próximos passos

1. **Promover F1 (altitude diferencial) e F3 (mando reduzido em sede neutra) primeiro** — são os de evidência mais forte e dado gratuito: F1 tem coeficiente publicado (~½ gol/1000 m) e F3 tem o experimento natural da COVID. Ambos entram no **mesmo backtest** que a v4 já exige, como termos calibráveis com cap.
2. **F2 (calor) e F5 (bola parada) como candidatos no backtest** — F2 em `T_m`, F5 como piso de λ do azarão (ataca o gap BTTS já medido). Magnitudes **declaradamente estimadas** até o backtest.
3. **F6 (fuso) e F7 (descanso) como σ/confiança, não placar** — corrigir a métrica de viagem (km → Δfuso com sinal) e ligar descanso ao `σ_ajuste` (v4-D3).
4. **F4 (xG) como prior de estilo e régua de calibração** — ingerir StatsBomb (2018/2022) no mesmo passo do backtest.
5. **F8/F9/F12 como transparência/variância** — cenários de classificação (já na v4) + flags de clássico; manter pênalti como moeda.
6. **F10 (técnico) — nada a fazer além de registrar:** a v4 já o trata corretamente como σ.
7. **F11 (árbitro) — manter como lacuna declarada**; reabrir só se surgir fonte gratuita estruturada.
8. **Portão obrigatório para todos:** cada fator só vira termo de λ/dr se melhorar Brier/RPS com **IC que não cruza zero** (point-in-time). Overfitting cresce com cada variável — disciplina inegociável.

**Critério de aceite desta expansão:** nenhum fator entra "porque a literatura diz"; entra **se e somente se** o backtest histórico congelado mostrar ganho com IC. A literatura aqui serve para **priorizar o que testar** e **descartar o que não tem dado** — não para adicionar peso sem medida.

---

## Fontes (recuperadas da web em 2026-06-15)

**Físico / Fadiga**
- McSharry, P. (2007). *Effect of altitude on physiological performance: a statistical analysis using results of international football games.* BMJ. [PubMed 18156225](https://pubmed.ncbi.nlm.nih.gov/18156225/) · [ScienceDaily resumo](https://www.sciencedaily.com/releases/2007/12/071221094837.htm)
- Reilly et al. *Circadian rhythms, athletic performance, and jet lag.* [PubMed 9631214](https://pubmed.ncbi.nlm.nih.gov/9631214/) · Botonis (2025), *Impact of long-haul travel on athletic performance,* [Wiley/Exp Physiol](https://physoc.onlinelibrary.wiley.com/doi/full/10.1113/EP091831)
- Dupont et al. (2010) e revisão sistemática (2022). *Fixture congestion & injury.* [Springer, Sports Medicine](https://link.springer.com/article/10.1007/s40279-022-01799-5) · [PubMed 22012641](https://pubmed.ncbi.nlm.nih.gov/22012641/)

**Tático**
- *Expected goals in football: improving model performance and demonstrating value.* PLOS One (2023). [Artigo](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0282295)
- American Soccer Analysis (2022). *The Replication Project: Is xG the Best Predictor of Future Results?* [Link](https://www.americansocceranalysis.com/home/2022/7/19/the-replication-project-is-xg-the-best-predictor-of-future-results)
- Opta / The Analyst e bet365 News (2025-26): % de gols de bola parada. [The Analyst](https://theanalyst.com/articles/arsenal-tottenham-corners-record-premier-league-title-race-relegation-battle) · [bet365 News](https://news.bet365.com/en-gb/article/premier-league-set-piece-trend/2025102816520284583)

**Ambiental**
- McSharry 2007 (altitude, acima).
- *Extreme heat at the World Cup 2026.* [The Conversation](https://theconversation.com/extreme-heat-at-the-world-cup-are-fifas-safeguards-enough-282489) · [Sky Sports](https://www.skysports.com/football/news/12098/13549718/world-cup-2026-how-will-extreme-heat-impact-this-summers-tournament-in-the-usa-canada-and-mexico) · [Al Jazeera](https://www.aljazeera.com/sports/2026/6/8/how-extreme-weather-and-heat-could-affect-players-at-world-cup-2026)

**Psicológico / Contextual**
- *Home advantage during COVID (ghost games):* revisão sistemática, [Management Review Quarterly / Springer](https://link.springer.com/article/10.1007/s11301-021-00254-5) · *HAM by referee bias,* [Nature, Scientific Reports](https://www.nature.com/articles/s41598-021-00784-8) · [SN Explores resumo](https://www.snexplores.org/article/empty-stadium-ghost-games-increase-losses-for-home-teams)
- *Seasonal Pacing — Match Importance Affects Activity in Professional Soccer.* [PMC4900650](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4900650/)
- *New manager bounce:* [Football365](https://www.football365.com/news/championship-stat-pack-forecast-is-the-new-manager-bounce-actually-real) · [Soccer Analytics (Ter Weel)](https://socceranalytics.substack.com/p/is-the-new-manager-bounce-really)
- *Derby / rivalry & home advantage:* [Home advantage in derby matches (Brazil), ResearchGate](https://www.researchgate.net/publication/278158148_Home_advantage_in_derby_and_non-derby_matches_of_Premier_Brazilian_National_Football_League_played_from_2007_to_2011_seasons)

**Arbitragem**
- Garicano, Palacios-Huerta, Prendergast. *Favoritism Under Social Pressure.* [NBER w8376](https://www.nber.org/papers/w8376)
- *Referee bias in football: actual vs. expected additional time.* [ScienceDirect](https://www.sciencedirect.com/science/article/pii/S2773161825000011)
- Apesteguia & Palacios-Huerta (2010) e replicações: [Berkeley (ABAB/ABBA)](https://eml.berkeley.edu/~fechenique/wp/penales.pdf) · [Kiel Institut — no first-mover advantage](https://www.kielinstitut.de/fileadmin/Dateiverwaltung/IfW-Publications/fis-import/dd0d3c61-6eca-407c-b2f4-603ee3adaa2c-1-s2.0-S0167487025000285-main__5_.pdf)

---
*Pesquisa de expansão — sem código de implementação, por escopo. Não altera o contrato v4; alimenta o backlog de variáveis candidatas, todas atrás do portão de backtest. Fontes verificadas em 2026-06-15; disponibilidade muda → snapshot local é a defesa. Evidência prioriza o que testar e descarta o que não tem dado — não adiciona certeza. Probabilidades, nunca certezas.*
