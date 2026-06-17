---
tags: [camada1, planejamento, contrato, atual]
status: atual
tipo: planejamento
data: 2026-06-15
aliases: ["Modelo v5 (contrato atual)"]
---

# Camada 1 — Planejamento Matemático e de Dados (v5 — fatores de alto impacto com evidência)
**Projeto:** Sistema de previsão de partidas — Copa do Mundo 2026 (EUA/Canadá/México)
**Data:** 2026-06-15 · **Status:** planejamento (sem código) · **Custo-alvo:** R$ 0
**Supersede:** [[camada1-planejamento-v4]] (v4, 2026-06-15). Base da revisão: [[camada1-lacunas]] (pesquisa de fatores F1–F12, com fontes).

> Convenções herdadas (V/E/D, λ, dr, σ_R, σ_ajuste, σ_dr, T_m, GD, **[a calibrar]**). Marcador **▲v5** sinaliza o que mudou em relação à v4 e por quê, com a **evidência** (fonte em §6). **Todas as correções da v2 (anti-saturação, mando histórico), da v3 (coerência [0,1], incerteza de rating) e da v4 (propagação inteira, σ_ajuste, desfalque direcional) continuam válidas e integradas.** A v5 promove ao contrato os fatores que passaram no duplo critério da pesquisa: **evidência publicada + dado gratuito**. Tudo entra **a montante** (λ/dr/σ), **com cap** e **atrás do portão de backtest** (IC que não cruza zero) — nenhum fator novo vira perna do ensemble. Tabelas novas reconferidas em código (§3.5, §3.13, §8).

---

## 0. Changelog v5 (o que mudou, por quê, e com qual evidência)

A v4 cobria os fatores físicos/ambientais apenas como "diagnóstico" **sem fonte nem magnitude**. A pesquisa [[camada1-lacunas]] levantou a evidência e separou o que tem dado gratuito do que não tem. A v5 **promove** os de evidência forte a **termos calibráveis** (com cap), **rebaixa** o que a v4 media errado, e **declara** as lacunas. Princípio inegociável: a literatura **prioriza o que testar**; só o backtest decide se entra.

| # | Mudança | Sev. | Seções | Fator/Fonte |
|---|---|---|---|---|
| E1 | **Altitude diferencial vira termo de GD.** McSharry (BMJ 2007): ~**½ gol de saldo por 1000 m** de diferença, P<0.001. Penalidade de não-aclimatação **assimétrica** (só *subir* machuca): `pen(T)=max(0, alt_sede − alt_casa_T)`; `GD += θ_alt·(pen_B − pen_A)/1000`. Verificado: morde só quando **uma** seleção é adaptada (ex.: México na Cidade do México, GD_alt≈+1,1); duas planícies na altitude → 0 (efeito vai para fadiga/total). | 🟡 modelagem | 3.13, 8, 11.1 | F1 / McSharry 2007 |
| E2 | **Mando revisto para baixo e em banda — parte é viés de árbitro.** Experimento natural dos jogos-fantasma (COVID): mando caiu (Bundesliga **48,2%→32,5%** de vitórias em casa) e faltas contra o mandante subiram **~26%** sem torcida → a vantagem de casa é **majoritariamente mediada por árbitro/torcida**. Numa Copa em sede **neutra**, mando = 0 (reforçado). Para os **anfitriões**, `H_host2026` cai de +60 para **+40 [a calibrar]** e vira **banda** (parte do efeito pode não transferir para um público de Copa mais misto); a incerteza entra em σ_dr. | 🟡 modelagem | 3.5, 8, 16 | F3 / ghost games; Garicano |
| E3 | **Calor reduz o total (T_m).** 9/16 sedes de 2026 em "risco extremo"; calor **baixa ritmo/pressing e total de gols**. `T_m *= (1 − κ_heat·excesso_WBGT)`, cap pequeno; também derruba a confiança nas sedes quentes. Sem coeficiente publicado gratuito → magnitude **declaradamente estimada**, [a calibrar]. | 🟡 modelagem | 3.11, 8 | F2 / cobertura WC2026 |
| E4 | **Piso de λ do azarão por bola parada.** ~**27% dos gols** vêm de bola parada (sem pênalti); o azarão marca desproporcionalmente assim. Corrige o gap medido **BTTS 22% (modelo) vs ~40% (mercado)** em ESP×CPV. `λ_azarão = max(λ_azarão, piso(propensão_bola_parada))`. Verificado: λ_B 0,26→0,50 leva BTTS **22%→37%** sem destruir P(V) (90%→85%). | 🟡 modelagem | 3.13, 8, 11.1 | F5 / Opta 2025-26 |
| E5 | **Métrica de viagem corrigida: km → fuso com sinal.** Cronobiologia: o que pesa é **cruzar fusos, e leste é pior** (ressincroniza ~1 h/dia), não a distância. A v4 media **km** (haversine, métrica errada). Agora `Δfuso` com sinal (leste pesa mais) entra em **σ_ajuste** (confiança), não em λ — efeito pequeno e fácil de overfittar. | ⚪ → σ | 3.11, 3.12 | F6 / Reilly; Botonis 2025 |
| E6 | **Descanso curto/diferencial em σ_ajuste, não em placar.** Dupont (2010) e revisão 2022: <5 dias elevam **lesão/fadiga**, não comprovadamente o resultado. Entra como **incerteza** (σ_ajuste/robustez), coerente com a evidência — não como termo de λ. | ⚪ → σ | 3.11, 3.12, 13 | F7 / Dupont 2010 |
| E7 | **Confirmações e transparência (sem novo termo).** **Técnico novo** = aumento de σ_R, não "bounce" (Ter Weel: efeito médio ~zero) — a v4 já fazia, agora com fonte. **Pênalti** = moeda, ε≈0.03 pequeno (replicações divergem: 60:40 não se sustentou) — mantido. **Importância/jogo-morto** e **rivalidade/clássico** → cenários determinísticos e flags de variância, não λ. **xG** = prior de estilo + régua de calibração. **Árbitro individual** = **lacuna declarada** (sem fonte gratuita estruturada). | ⚪ | 3.5, 4, 6, 12, 16 | F8–F12, F4 |

Princípio mantido desde a v1: **nada de certezas — só probabilidades**; tudo roda local; nenhuma previsão lê a internet no cálculo (snapshot diário). **Esta versão passa a ser `v5.0`. Coerência [0,1] garantida; acurácia não-comprovada até o 1º backtest — e agora com mais variáveis [a calibrar], o portão de IC é ainda mais crítico.**

---

## 1. Visão geral do sistema em camadas

| Camada | Função | Estado |
|---|---|---|
| 1 | Motor matemático e dados base | **este documento (v5)** |
| 2 | Coleta e normalização (CSV/JSON → SQLite local) | próxima |
| 3 | Detector de notícias/lesões/desfalques | depois da 2 |
| 4 | Sistema de previsão (ensemble) | consome 1–3 |
| 5 | Geração de insights/explicações | consome 4 |
| 6 | Interface local | última |

A Camada 1 define **contratos matemáticos**. Mudança em qualquer fórmula = nova `versao_modelo`.

## 2. Objetivo da Camada 1

Transformar dados públicos em P(V/E/D) **com banda por percentis**, λ_A/λ_B, placares, P(over 2.5), P(BTTS), ajuste **direcional** de desfalques, **ajustes ambientais com evidência** (altitude, calor — ▲v5), score de confiança e validação. Critério de pronto: cada saída rastreável a uma fórmula e a um dado; **toda probabilidade em [0,1] por construção**; incerteza dos inputs (rating + ajustes + ambiente) propagada; **e cada termo ambiental ancorado em fonte publicada, não em palpite** (▲v5).

## 3. Cálculos recomendados

Pipeline: Elo (+ forma + desfalques + mando **revisto**) estima a *diferença* e sua *incerteza total*; ataque/defesa e ambiente estimam o *total* e a *direção* dos gols; Poisson gera placares; mini-ensemble combina; odds e mercado de previsão são benchmark.

### 3.1 Elo Rating — mantido da v3/v4
```
R_novo = R_antigo + K·G·(W − W_e) ;  W_e = 1/(1+10^(−dr/400)) ;  dr = R_A − R_B + mando
K = 60 Copa · 50 continental · 40 elim. · 30 Nations · 20 amistoso
G = 1 (≤1) · 1.5 (2) · (11+N)/8 (N≥3)
```
`H_hist`=100 (construção do Elo, todo jogo não-neutro). Inicialização 1500; <30 jogos = provisório. σ_R por seleção (3.12). Benchmark eloratings.net (±25 top-30).

### 3.2 Poisson — mantido da v4
Matriz `M[i][j]=Pois(i;λ_A)·Pois(j;λ_B)`, i,j=0..10, resíduo na borda. V/E/D, over 2.5, BTTS, top-k da matriz. **Mercados derivados são Poisson-condicionais (declarado, ▲revisao-v5/A1 — nota pós-congelamento, sem mudança de fórmula):** over 2.5, BTTS e placares saem **só** da leitura `P_poisson` (matriz de λ), não do V/E/D do *ensemble*; logo a diagonal da matriz soma o `P(E)` **da Poisson**, não o do ensemble (ex.: IRN×NZL 27.5% vs 25.3%). Não somar a diagonal esperando o empate do ensemble, nem existe "matriz de placares do ensemble". **Duas P(E)** (matriz vs curva empírica) a reconciliar quando a Dixon-Coles entrar (a DC sobe 0×0/1×1 → muda P(E); recomputar V/E/D, over, BTTS). Mata-mata: avanço = `P(V)+P(E)·(0.5+ε·sinal(dr))`, ε≈0.03 [a calibrar].

### 3.3 Forma recente — mantido da v4
Janela 10, `w_i=0.9^meses·(1 oficial·0.5 amistoso)`, `ΔE_forma=15·(PPJ_pond−PPJ_esp)`, cap ±30. Ajustada a adversário; Elo point-in-time no backtest. Dispersão da forma → σ_ajuste (3.12).

### 3.4 Força ofensiva/defensiva — mantido da v4 (+ E4 em 3.13)
`estilo_T = shrinkage(tendência_gols → 1.0)`. Upgrade Dixon-Coles (11.2): λ direcional, gerador primário XOR `P_ad` independente — e, se membro do ensemble, **prior de gols/xG, não Elo** (v4-D5).

### 3.5 Mando de campo ▲v5 (E2)
```
H_host2026 = +40 Elo [a calibrar, ▲v5: era +60]  para anfitrião (EUA/MEX/CAN) em solo próprio
           = 0                                     nos demais (NEUTRO — a maioria dos jogos de Copa)
banda_mando = ±20 Elo  -> entra em σ_dr nos jogos de anfitrião
```
**▲v5 — por que baixou (F3).** O experimento natural dos jogos-fantasma da COVID mostra que a vantagem de casa é **majoritariamente viés de árbitro + torcida** (Bundesliga: vitórias de casa 48,2%→32,5% sem público; faltas contra o mandante +26%; Garicano: árbitro manipula acréscimos a favor da casa). Implicações: (i) em **sede neutra** o mando "clássico" **não existe** — já era 0, reforçado; (ii) mesmo o anfitrião deve ganhar **menos** que +60, porque o público de Copa é mais **misto/neutro** que o de um clássico de liga, e parte do efeito é arbitragem que pode não transferir. O `+40` é **estimativa rebaixada [a calibrar]**, publicada como **banda** (a incerteza vai para σ_dr). Caso "quase-casa" (México em solo americano): `bonus_mando_override` manual, também banda.

### 3.6 Lesões e desfalques — mantido da v4 (direcional, §13)
`setor` ("ataque"/"defesa"/"goleiro") obrigatório: ofensivo corta λ_pró; defensivo/goleiro infla λ_contra. "Dúvida" alimenta σ_ajuste.

### 3.7 Odds e mercado de previsão — mantido da v4
De-vig proporcional. **Mercado de previsão (Kalshi/Polymarket)** = benchmark multiagente > 1 casa (captura manual com timestamp). Peso ≤0.20.

### 3.8 Ensemble — mantido da v4
`P_poisson` e `P_elo` compartilham o Elo; diversidade real vem do mercado e (se aplicável) do AD com prior não-Elo. Clamp por leitura antes do pool. Leitura Elo-direto entra **inteira e propagada**.

### 3.9 Confiança — mantido da v4 + ▲v5 (E3, E5, E6)
Gate `g_rating`. **▲v5:** calor (sedes de risco), fuso a leste e descanso curto **derrubam a confiança** (via σ_ajuste/robustez), não o ponto.

### 3.10 Validação — mantido da v4
Brier+LogLoss+RPS+calibração, IC bootstrap, registro imutável com `sigma_dr`/`banda_pv`/`hash_inputs`/`preco_mercado_previsao`, filtro por versão.

### 3.11 Contexto físico e ambiente ▲v5 (E1, E3, E5, E6)
A v4 listava tudo como "diagnóstico". A v5 **separa por evidência**:
- **Altitude (F1) → termo de GD** (3.13/§8) — tem coeficiente publicado (McSharry).
- **Calor (F2) → modificador de T_m** (§8) + confiança — relevante e específico de 2026; magnitude estimada.
- **Viagem (F6) → σ_ajuste como Δfuso COM SINAL** (leste pior), **não km** — correção da métrica da v4.
- **Descanso (F7) → σ_ajuste** (evidência é lesão/fadiga, não placar).
- **xG (F4)** → prior de estilo + régua de backtest (StatsBomb; histórico, não ao vivo).
- **Idade/caps, técnico (regime)** → σ_R (Wikidata para data de nomeação).
Não perseguir: posse, distância percorrida (sem fonte gratuita p/ seleções).

### 3.12 Incerteza total `σ_dr` — mantido da v4 + ▲v5 (E5, E6)
```
σ_ajuste(T) = sqrt( (a·Σ|ΔE_i| desfalque em DÚVIDA)²
                  + (b·n_meio_tier)²
                  + (c·desvio_forma)²
                  + (d·Δfuso_leste)²        # ▲v5 (E5): viagem a leste
                  + (e·descanso_curto)² )   # ▲v5 (E6): <5 dias / diferencial      [a,b,c,d,e a calibrar]
σ_dr = sqrt( σ_R(A)² + σ_R(B)² + σ_ajuste(A)² + σ_ajuste(B)² + banda_mando² )   # ▲v5: banda_mando p/ anfitrião
# RSS — APROXIMAÇÃO (ignora covariância intra-confederação, declarado na v4)
```
Propagação: leitura V/E/D inteira sobre σ_dr (MC); banda = percentis 16/84 da mesma amostra (encolhe `W_e` para **½**, não 1/3). Tabela E[W_e] mantida da v4.

### 3.13 Ajustes ambientais de λ ▲v5 (E1, E4) — NOVO
Os dois ajustes ambientais com dado gratuito que mexem em **λ** (os demais vão para σ):

**Altitude (E1, F1).** Penalidade de não-aclimatação assimétrica (McSharry: só *subir* machuca):
```
pen(T)  = max(0, alt_sede − alt_casa_T)            # metros acima do que o time está acostumado
GD_alt  = θ_alt · (pen_B − pen_A) / 1000           # θ_alt ≈ 0.5 gol/1000 m (McSharry); [a calibrar] fora da CONMEBOL
```
Verificado (θ_alt=0.5):

| Sede / confronto | pen_A | pen_B | GD_alt |
|---|---:|---:|---:|
| Miami 0 m · planície × planície | 0 | 0 | **0.00** |
| Cidade do México 2240 m · planície × planície | 2240 | 2240 | **0.00** |
| Cidade do México 2240 m · **México (casa 2240)** × planície | 0 | 2240 | **+1.12** |
| Guadalajara 1560 m · planície × adaptado (1560) | 1560 | 0 | **−0.78** |

Leitura crítica: o diferencial **só morde quando uma seleção é adaptada** (na prática, **México na Cidade do México** — que se sobrepõe ao mando). Para duas seleções de planície na altitude, `GD_alt=0` e o efeito real é **fadiga/total** (ambas sofrem) → vai para T_m/confiança, não para o saldo. Honesto: o coeficiente de McSharry é da **CONMEBOL**; extrapolar para outras confederações exige cautela e σ maior.

**Bola parada — piso de λ do azarão (E4, F5).** O azarão marca desproporcionalmente em bola parada:
```
λ_azarão = max( λ_azarão, piso_setpiece(propensão_bola_parada_T) )   # propensão via StatsBomb; piso [a calibrar]
```
Verificado (ESP×CPV, λ_A=2.84):

| λ_B (azarão) | P(V) | P(E) | P(D) | over 2.5 | BTTS | vs mercado |
|---:|---:|---:|---:|---:|---:|---|
| 0.26 (v4) | 0.896 | 0.085 | 0.019 | 0.599 | **0.216** | mercado BTTS ~40% |
| 0.40 | 0.870 | 0.098 | 0.032 | 0.628 | 0.310 | |
| 0.50 | 0.852 | 0.107 | 0.042 | 0.648 | **0.370** | mais perto |
| 0.60 | 0.832 | 0.115 | 0.053 | 0.668 | 0.425 | |

Pisar λ_B de 0.26→0.50 leva o **BTTS de 22%→37%** (perto do mercado) e **não destrói o favoritismo** (P(V) 90%→85%). É a correção principiada para o azarão-defensivo subestimado — atrás do portão, calibrada pela propensão real de bola parada.

## 4. Cálculos fora da baseline ▲v5
**Upgrade #1:** ataque/defesa + Dixon-Coles (prior não-Elo se for membro do ensemble — v4-D5). **Insights:** Monte Carlo + cenários de classificação (F8). **Continuam fora:** xG ao vivo p/ 48 seleções (sem fonte grátis); ML/boosting (overfit); hierárquico bayesiano (mata auditabilidade); **árbitro individual (F11 — lacuna de dados, §16)**; tracking/posse/distância (sem fonte). **▲v5 — cuidado de interação:** altitude (↑ saldo do adaptado) e calor (↓ total) agem em direções diferentes no tail; calibrar **juntos** com as formas de GD/T_m, senão um cancela o outro sem evidência.

## 5. Dados necessários por cálculo ▲v5 (só o que mudou vs v4)

| Cálculo | Dado | Fonte | Grátis? |
|---|---|---|---|
| Altitude (E1) | elevação da sede + altitude "de casa" da seleção | Open-Meteo Elevation; Wikidata | Sim |
| Calor (E3) | temp/umidade no horário do jogo (WBGT aprox.) | Open-Meteo | Sim |
| Bola parada (E4) | % de gols de bola parada por seleção | StatsBomb (tipo de jogada) | Parcial (histórico) |
| Fuso (E5) | offset de fuso sede vs casa do time (com sinal) | coords + base tz gratuita | Sim |
| Descanso (E6) | dias desde o último jogo + diferencial | fixturedownload | Sim |
| Mando banda (E2) | flag anfitrião | calendário | Sim |

Demais entradas: iguais à v4 (Elo+σ_R, forma, estilo/AD, desfalques c/ setor, odds+mercado de previsão, xG).

## 6. Fontes ▲v5 (verificadas em 2026-06-15)
Acrescenta à tabela da v4 a **evidência** dos fatores promovidos (detalhe e links em [[camada1-lacunas]] §Fontes):
- **Altitude (E1):** McSharry, *Effect of altitude on physiological performance* (BMJ 2007, PubMed 18156225) — ~½ gol/1000 m, P<0.001.
- **Mando/árbitro (E2):** revisão de jogos-fantasma COVID (Management Review Quarterly/Springer); *HAM by referee bias* (Nature, Scientific Reports); Garicano et al., *Favoritism Under Social Pressure* (NBER w8376).
- **Calor (E3):** cobertura WC2026 (The Conversation; Sky Sports; Al Jazeera) — 9/16 sedes em risco extremo; FIFA com pausas.
- **Bola parada (E4):** Opta/The Analyst e bet365 (2025-26) — ~27% dos gols.
- **Viagem/fuso (E5):** Reilly et al. (PubMed 9631214); Botonis (Exp Physiol 2025).
- **Descanso (E6):** Dupont (2010); revisão sistemática (Sports Medicine 2022).
- **Confirmações (E7):** xG melhor preditor (PLOS One 2023; ASA 2022); técnico = regressão à média (Ter Weel); pênalti contestado (Kocher 2012; Vollmer 2024).

Fontes de **dados** (martj42, fixturedownload, StatsBomb, Open-Meteo, Wikidata, Kalshi/Polymarket, etc.): mantidas da v4 §6. **Lacuna mantida:** árbitro individual e xG ao vivo das 48 seleções — sem fonte gratuita estruturada. **APIs pagas — fora de escopo.**

## 7. Dados manuais no início — mantido da v4 + ▲v5
Acrescenta: **altitude "de casa" de cada seleção do shortlist** (uma constante por seleção) e **sede/horário** por jogo (para calor e fuso). Demais iguais à v4.

## 8. Pipeline completo ▲v5 (E1–E6)
```
ENTRADAS: R,σ (A,B) · forma · estilo · desfalques c/ setor · sede(alt,clima,fuso) · flag anfitrião

1) Elo ajustado:   R'_T = R_T + ΔE_forma(T) + ΔE_desfalques_DEF(T)
2) Diferença:      dr   = R'_A − R'_B + H_host2026            # ▲v5 (E2): +40 [a calibrar] anfitrião, 0 neutro
   Incerteza:      σ_dr = sqrt(σ_A² + σ_B² + σ_ajuste_A² + σ_ajuste_B² + banda_mando²)   # ▲v5: σ_ajuste inclui fuso/descanso (E5,E6); banda_mando (E2)
3) Saldo:          GD   = f(dr) + GD_alt                      # ▲v5 (E1): GD_alt = θ_alt·(pen_B−pen_A)/1000 ; f por backtest
4) Total:          T_m  = g(dr)·estilo_A·estilo_B·(1 − κ_heat·excesso_WBGT)   # ▲v5 (E3): calor reduz o total ; g por backtest
5) Gols base:      λ_A0 = (T_m+GD)/2 ;  λ_B0 = (T_m−GD)/2
6) Ofensivo+piso:  λ_T  = λ_T0·(1 − δ_ata_T) ;  λ_azarão = max(λ_azarão, piso_setpiece)   # ▲v5 (E4) ; depois λ ← max(λ, λ_min)
7) Matriz Poisson:  M[i][j] = Pois(i;λ_A)·Pois(j;λ_B), 0..10 (resíduo na borda)
8) Saídas Poisson:  V/E/D, over 2.5, BTTS, top placares
9) Leitura Elo-direto PROPAGADA INTEIRA: V/E/D + banda por percentis (3.12)
10) Ensemble (clamp por leitura) + banda por percentis
```
**Ordem de calibração (▲v5):** primeiro as formas de GD/T_m (v4-D2) **e** os termos ambientais E1/E3 **juntos** (interagem); cada um com cap e portão de IC. θ_alt ancorado em McSharry; κ_heat e piso_setpiece **[a calibrar]** sem coeficiente publicado.

## 9. Ensemble e leitura Elo-direto — mantido da v4
Curva de empate restrita (C1) propagada por amostra; pesos 0.45/0.35/0.20 (c/ odds); clamp por leitura; banda por percentis; fork AD (prior não-Elo se membro). Ponto/banda/confiança usam a **mesma** σ_dr (correlacionados).

## 10. Probabilidade final V/E/D — mantido da v4
Clamp por leitura → média ponderada → clamp final [0.02,0.96]. Banda = percentis 16/84 da leitura propagada (a perna de mercado não se move com dr).

## 11. Gols esperados ▲v5
### 11.1 Baseline (▲v5 E1, E3, E4)
Passos 3–6 da §8: `GD = f(dr)+GD_alt`, `T_m = g(dr)·estilo·(1−κ_heat·excesso_WBGT)` (formas por backtest), desfalque direcional, **piso de bola parada no azarão**. λ mínimo como regularização honesta.
### 11.2 Upgrade #1 — Ataque/Defesa + Dixon-Coles — mantido da v4
`ln λ = μ + ATA + DEF + γ·mando`; prior de gols/xG (não Elo) se for membro do ensemble; DC corrige 0-0/1-0/0-1/1-1; λ=exp(...)>0 dispensa clamp. Reconciliar as duas P(E) ao entrar.

## 12. Placares prováveis — mantido da v4
Top-5 da matriz; "chance de NÃO ser o modal" derivada por jogo (~88% parelho, ~82% goleada).

## 13. Lesões/desfalques — mantido da v4 (+ E6)
Roteamento por `setor` (ofensivo corta λ_pró; defensivo/goleiro infla λ_contra). "Dúvida" + **descanso curto (E6)** alimentam σ_ajuste e derrubam a robustez da confiança.

## 14. Confiança — mantido da v4 + ▲v5
`score = 100·(0.35·separação + 0.15·consist_int + 0.15·corrob_ext + 0.20·dados + 0.15·robustez)·g_rating·(0.90 mata-mata)·(0.85 última rodada)`. **▲v5:** σ_dr (logo `g_rating`) agora carrega banda de mando, fuso e descanso; calor entra na robustez nas sedes de risco. Declarado: ponto, banda e confiança usam a mesma σ_dr (não são 3 sinais independentes).

## 15. Validação — mantido da v4
Brier/LogLoss/RPS + calibração + **cobertura da banda**; IC bootstrap B=10000; filtro por `versao_modelo` (exclui `*-prelim`). Backtest histórico 2014/18/22 + Euro/Copa América (~400+ jogos), congelado e point-in-time.

## 16. Riscos e limitações ▲v5
**O maior risco é o mesmo: nada foi backtestado, e a v5 *adiciona* variáveis** (θ_alt, κ_heat, piso_setpiece, banda_mando, d/e de σ_ajuste). **Cada variável nova multiplica os graus de liberdade contra amostras minúsculas** — o portão de IC-que-não-cruza-zero é agora **mais** crítico, não menos. A v5 é mais **fundamentada em evidência**; não é mais **acurada** até a medição.

**Específicos da v5:**
- **Altitude (E1):** coeficiente de McSharry é **CONMEBOL**; extrapolar p/ outras confederações é incerto; na prática só morde para seleção adaptada (México em casa), sobrepondo-se ao mando — risco de **dupla contagem** com `H_host2026` (calibrar os dois juntos).
- **Mando rebaixado (E2):** `+40` é estimativa **rebaixada [a calibrar]**, não medida; pode estar baixo demais — por isso vira **banda**, não ponto. Risco oposto: subestimar o anfitrião real.
- **Calor (E3):** **sem coeficiente publicado gratuito** — magnitude estimada; risco de overfit; manter cap pequeno e tratar primeiro como confiança.
- **Bola parada (E4):** piso muda toda a distribuição (P(D)/over sobem junto com BTTS); calibrar pela propensão real, não chutar o piso.
- **Fuso/descanso (E5/E6):** efeitos pequenos, fácil overfit; por isso entram em **σ**, não em λ — e a evidência de descanso é de **lesão**, não de placar (cuidado causal).
- **Interação altitude×calor** pode se cancelar sem evidência (§4).

**Mantidos (v2–v4):** amostra pequena (104 jogos); formato de 48 times; fontes que atrasam/morrem (snapshot); eco do mercado; overfitting de pesos; prorrogação/pênaltis fora do modelo; escalações ~1h antes; RSS ignora covariância; reconciliação das duas P(E) aberta até a DC; **apostas: Brier ~0.60 não é edge — não é ferramenta de lucro.**

**Lacunas declaradas (não inventar):** árbitro individual (F11), xG ao vivo das 48 seleções, posse/distância. **Incerto mesmo após a v5:** `H_host2026`, θ_alt fora da CONMEBOL, κ_heat, piso_setpiece, σ_ref, México "quase-casa", incentivos de fim de grupo (tornados **transparentes** por cenários, não eliminados).

## 17. Roadmap ▲v5
**C1 (agora):** v5 = contrato congelado. **C2:** Elo histórico (H_hist + σ_R) → backtest base; milestone: Brier < 0.62 (IC) e < Elo público, P(D)≥0, confiança não-crescente com σ_dr, banda com cobertura nominal. **C2.5:** formas de GD/T_m **+ termos ambientais E1/E3 juntos**; ataque/defesa + DC; reconciliar P(E); re-backtest. **C3:** desfalques+descanso JSON → RSS. **C4:** ensemble + calibração de θ_alt/κ_heat/piso_setpiece/banda_mando/σ_ajuste/pesos. **C5:** insights (Monte Carlo + cenários + fatores por previsão). **C6:** interface.

## 18. Próxima etapa recomendada ▲v5 (ordem importa)
1. **Backtest base do contrato congelado** (Elo+mando histórico+σ_R → GD/T_m → Poisson), point-in-time, IC bootstrap. *Sem isto, o resto é decoração.*
2. **Calibrar mando rebaixado (E2)** contra o histórico (o `+40` e a banda saem do fit, não do decreto) — e **separar do altitude (E1)** p/ evitar dupla contagem em jogos do México na altitude.
3. **Formas de GD/T_m + altitude (E1) + calor (E3) juntos**, por Brier/RPS com IC; θ_alt ancorado em McSharry, κ_heat livre com cap.
4. **Piso de bola parada (E4)** calibrado pela propensão StatsBomb — validar contra o gap BTTS observado.
5. **Fuso (E5) e descanso (E6) em σ_ajuste** — corrigir a métrica de viagem (km → Δfuso) e ligar descanso à incerteza.
6. **xG (F4)** como prior de estilo + régua; **cenários de classificação (F8)** como insight.
7. **Manter como está:** técnico = σ (F10), pênalti = moeda (F12); **manter lacuna:** árbitro (F11).
8. **Só então** pesos finos do ensemble (≥30 jogos) e `P_ad` (prior não-Elo).

**Milestone de aceite:** backtest congelado e point-in-time com **Brier < uniforme (IC que não cruza o baseline)**, ≈ Elo público, **P(V),P(D) ∈ [0,1]**, **confiança não-crescente com σ_dr**, **banda com cobertura nominal**, e **cada termo ambiental novo só mantido se melhorar Brier/RPS com IC que não cruza zero** (senão é removido). Sem isso, o resto é decoração.

---
*Documento de planejamento v5 — sem código de implementação, por escopo. Promove ao contrato os fatores de [[camada1-lacunas]] com **evidência publicada + dado gratuito** (altitude, mando rebaixado por evidência de arbitragem, calor, bola parada, fuso/descanso como incerteza), mantendo v2 (anti-saturação, mando histórico), v3 (coerência [0,1], incerteza de rating) e v4 (propagação inteira, σ_ajuste, desfalque direcional). Tabelas reconferidas em código. Fontes verificadas em 2026-06-15; snapshot local é a defesa. Probabilidades, nunca certezas — e cada variável nova só sobrevive se o backtest a sustentar.*
