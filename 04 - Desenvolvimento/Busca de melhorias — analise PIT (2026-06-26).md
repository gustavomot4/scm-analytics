---
tags: [dev, evolucao, portao, analise]
status: vivo
tipo: analise
data: 2026-06-26
modelo: baseline-v0.4-ad
aliases: ["Busca de melhorias 2026-06-26", "Evolucao — analise cetica"]
---

# Busca de melhorias — análise céptica com STEP 0 medido (2026-06-26)

> Régua: assuma que o núcleo Elo→Poisson está **no teto**. O juiz é o **portão de backtest** (treino <2015 / teste ≥2015, PIT), não a literatura. Nenhuma proposta entra na tabela sem **3 números medidos no snapshot**. Prior honesto de aprovação ~20–30% (a maioria dos candidatos deste projeto FALHOU).
> Snapshot: `dados/scm.sqlite` (49.457 jogos, até 2026-06-24); teste ≥2015 = **11.044 jogos** (não-amistosos 7.893; major-torneio 479).

## Veredito em 3 linhas
1. **O maior ganho seguro hoje é operacional, não de modelo:** a Copa está a acontecer — capturar **linha de fechamento (CLV real)** e ligar **reliability + alarme de drift por mercado** no `monitor` já existente. Sem portão a falhar (é medição), custo baixo, valor alto. **Faça já.**
2. **Único termo de modelo com sinal NOVO real:** **mando por confederação** (CONMEBOL home **+0,040** acima do mando mesmo *fora* de altitude; UEFA home **−0,040**, estável nas duas eras). Passa o kill-switch (corr c/ `dr` ~0,02–0,18). **Mas o impacto na Copa 2026 é ~nulo** (sede CONCACAF neutra) → ganho é de Brier histórico, não de previsão da Copa. P(passar o portão) ~0,45; prioridade média.
3. **O resto está esgotado ou sub-powered:** descanso/congestão tem efeito **medido ~0** e a Copa tem calendário simétrico; ε de pênaltis já é **medível** (0,049) mas não move decisão; Elo intra-torneio não é gateável com potência (poucas Copas). Poço de dado externo R$0 **seco** além de `shootouts`.

---

## 0. Lista-morta (varri e matei)

| Ideia | Por que morreu (1 linha) |
|---|---|
| **Viagem / fuso (Δfuso)** | `venues` vazia; precisaria construir tabela de long/lat; e numa Copa todos co-localizados → Δfuso≈0 no mata-mata. Não-aplicável a 2026 + mecanismo ~0. |
| **K por fase do torneio** | K já afinado no `elo_engine`; mexer em K é ajuste de **parâmetro do núcleo** (esgotado, D-39/40/47) e é colinear com o próprio rating. Sem sinal independente. |
| **xG como prior (StatsBomb)** | Já RODADO e barrado (06-21: +0,0002 IC quase cruza; sim usa só `lambdas(dr)`). Re-propor sem ângulo novo = proibido (D-50). |
| **Cartões/escanteios por seleção** | D-72: LOO MAE +0,3%/+1,7% = ruído. Sem sinal no dado grátis. Já é histórico descritivo. |
| **Dixon-Coles / recal 1X2 / σ-Glicko / σ_dr-scaling / calor / estilo / T_base / forma-tanh** | Todos testados e barrados pelo portão (D-19/23/39/40/42/47). Sem ângulo genuinamente novo. |
| **Mercado no λ da simulação** | Estruturalmente inviável (mercado só precifica jogos agendados; cobertura ~1% da árvore). Sem portão a rodar. |
| **σ por-time correlacionado na sim** | D-74: ΔBrier −0,0009 IC cruza zero, sub-powered no avanço de grupo. Morto. |
| **Prior de "batedor de pênalti" por seleção (goalscorers.csv)** | n por seleção minúsculo; `timing` (D-71) já extrai o sinal de minuto; sem potência de portão. |
| **Booster de mando para os anfitriões 2026 via confederação** | CONCACAF home resid **+0,015 (NS)** → hosts não ganham nada além do +40 já declarado (D-47). Dobrado no caveat do item #2. |
| **Congestão (3º jogo em janela curta)** | 3.776 jogos com um time a ≤4d no teste, mas o efeito no resíduo é ~0 (ver §2.4) e na Copa o calendário é fixo/simétrico. |

---

## 1. Tabela priorizada (valor × P ÷ custo)

| # | Ideia | Categoria | Sinal esperado | corr c/ `dr` (medida) | Dado R$0? | n no teste (≥2015) | Potência | Custo experimento | Custo adoção | P(passar) |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **CLV de fechamento + reliability/drift por mercado** | Operacional / medição | detecta drift na Copa, mede edge real vs fechamento | n/a (não é termo de λ/dr) | sim (odds manuais) | registro vivo (~36+ jogos, cresce) | n/a — **não-gateado** | baixo (estende `monitor`) | **nenhuma** (instrumentação, sem versão) | **~1,0** (não há portão a falhar) |
| 2 | **Mando por confederação** (CONMEBOL+ / UEFA−) | Modelo — **sinal novo** | +ΔBrier 1X2 **histórico**; ~0 na Copa 2026 | **+0,017** (CONMEBOL), +0,185 (UEFA) — passa kill-switch | sim (derivado de `results`) | UEFA 1.530 / CONMEBOL 369 (não-neutros) | UEFA powered; CONMEBOL marginal | médio (`calibrate_confed` + portão) | **rebuild + nova versão** | **~0,45** |
| 3 | **ε do mata-mata (pênaltis) recalibrado** | Simulação / config | ε 0,03 → **0,049** (medido) | ~0 | sim (`shootouts.csv`) | 677 disputas (estima ε); ~3/Copa (gate título) | ε **powered**; título **sub-powered** | trivial (`calibrate_ko` já existe) | **flag de config** (sim-only) | ~0,7 útil / impacto baixo |
| 4 | Elo intra-torneio na simulação | Simulação | pequeno; mais realismo | ~0 | sim | poucas Copas | **sub-powered** (gate fraco) | médio | só simulação | ~0,20 (≈não-gateável c/ potência) |
| 5 | Descanso / congestão (Δdescanso) | Modelo | **~0 (efeito nulo medido)** | −0,084 | sim (datas) | 1.860 não-amistosos; **49 major** | sub-powered **e** efeito nulo | médio | rebuild + versão | **~0,10** |

Ordenação por valor×P÷custo: **#1 (operacional) ≫ #2 (confederação) > #3 (ε, quase grátis) > #4 ≈ #5 (baixos).**

---

## 2. Top 3 detalhados (8 pontos + harness)

### TOP 1 — CLV de fechamento + reliability/drift por mercado (operacional)

**1. Hipótese e mecanismo.** O ganho mais seguro durante um torneio não é mais fórmula — é **medir bem**. Hoje o `monitor` mede Brier vs uniforme, ECE do top-pick e edge vs mercado de **abertura**. Falta (a) **CLV verdadeiro** = p_modelo vs **linha de fechamento** (o melhor proxy não-enviesado de "valor"), e (b) **reliability/drift por mercado** (1X2, BTTS, over, timing) — um mercado pode derivar enquanto o agregado parece bem.

**2. Independência medida.** N/A — não é termo de λ/dr, não há colinearidade a checar. É instrumentação sobre o **registro imutável** (`registro-auto.csv`) + `odds_hist`.

**3. Dado.** Linha de **fechamento** capturada à mão antes do kickoff → `odds_hist` com `source='close'` (o `monitor` já prevê esse gancho no docstring). R$0, offline, cabe no PIT (a linha de fechamento é pré-jogo). Per-mercado: o registro já guarda os mercados derivados.

**4. Portão.** **Não-gateado de propósito** — é medição, não toca λ/dr, logo não passa (nem deve passar) pelo portão de Brier. Adoção = instrumentação, sem bump de versão. O "teste" é operacional: rodar a cada rodada e ler.

**5. Efeito esperado.** Não muda o Brier do modelo; muda a **capacidade de detectar drift cedo** (antes que custe) e de afirmar/negar skill vs fechamento com IC. Valor = evitar a auto-ilusão da amostra de 1 Copa (o `cup_scorecard` já mostrou IC [−0,067,+0,219] **cruzando zero** com 36 jogos).

**6. Custo de adotar.** Baixo. Estender `monitor.py`: laço de ECE por mercado sobre o registro; comparar p_modelo×fechamento quando `source='close'` existir. **Sem nova versão de modelo.**

**7. P(passar).** ~1,0 — não há portão a falhar. O risco é só de **disciplina de captura** (lembrar de gravar o fechamento).

**8. Harness reproduzível.**
```bash
# (a) capturar a linha de FECHAMENTO de cada jogo, pré-kickoff:
python -m scm.odds ingest dados/odds_close.csv --source close   # natural_key,p_home,p_draw,p_away
# (b) rodar o painel operacional após settle:
python -m scm.ingest --download && python -m scm.registrar settle-from-db
python -m scm.monitor --db dados/scm.sqlite --reg dados/registro-auto.csv
```
*Extensão a escrever* (`monitor.reliability_by_market`): para cada mercado m em {1X2, BTTS, over2.5, gol-1ºT, HT}, agrupar linhas settled por faixa de p, computar |p̄−obs| (ECE_m) e o sinal de **drift** = ECE da janela recente − ECE histórico do backtest; alarmar se > banda. Seed irrelevante (determinístico). Vira `calibrate_*`-style sem portão: imprime tabela por mercado + bandeira de drift.

---

### TOP 2 — Mando por confederação (CONMEBOL+ / UEFA−)

**1. Hipótese e mecanismo.** O motor usa **mando fixo = +100 Elo** para todo jogo não-neutro. D-47 confirmou que **na média global** 100 é ok (H≈110–120, dentro do ruído). Mas a **heterogeneidade por confederação** é grande e nunca foi medida: casa sul-americana (eliminatórias longas, viagem, altitude, público hostil) vale mais; casa europeia vale menos (times próximos, declínio do fator-casa). Mando seria `+100 + δ_conf` em vez de fixo.

**2. Independência MEDIDA.** `corr(1[CONMEBOL home], dr_adj) = +0,017`; `corr(1[UEFA home], dr_adj) = +0,185`. Ambos **muito abaixo** do kill-switch 0,95 → é sinal de **onde** (geografia do mando), ortogonal a **quem** (força). Não é releitura do `dr`. Vetado o confundidor de altitude (já adotada, D-18): **CONMEBOL home fora de altitude segue +0,040 (±0,024, IC>0)**; a parte de altitude (+0,164) é o termo já existente. Vetado o confundidor de tempo: **UEFA home é −0,037 (2000–11) e −0,040 (2012–25)** — estável, não é tendência temporal (o declínio global do fator-casa é só +0,012→−0,008).

**3. Dado.** Derivado de `results.csv` (mapa seleção→confederação, fixo e auditável). R$0, offline, PIT trivial (a confederação do mandante é conhecida pré-jogo).

**4. Portão.** Métrica = **ΔBrier 1X2 pareado** (IC95 bootstrap) nos **jogos não-neutros do teste ≥2015**. Treino <2015: **congelar** a tabela `δ_conf` (CONMEBOL, UEFA, demais=0) minimizando Brier de treino. Teste ≥2015: aplicar e medir. **n informativo:** UEFA 1.530 (powered), CONMEBOL 369 (marginal — a perna UEFA carrega a potência). **MDE:** resíduo medido ~0,04 → ΔBrier esperado +0,001…+0,003 no subconjunto; com n≈1.900 o IC deve sair **apertado o bastante para decidir** na perna UEFA (≈±0,0015). **Guardas:** ECE não pode subir; **não-regressão** em jogos neutros (onde δ_conf=0, Brier idêntico) e em BTTS/over (mando não mexe no total → deve ficar estável). DOF: a tabela tem ≤3 valores → fixar no treino, sem peeking (mesma disciplina da curva de empate D-26).

**5. Efeito esperado.** Brier 1X2 **histórico**: ordem de +0,001…+0,003 (compatível com altitude, +0,049 mas em n menor). **Na Copa 2026: ~0** — sede CONCACAF é neutra; Brasil/Argentina/Europa jogam em campo neutro, então δ_conf não dispara. **Este é o ponto honesto:** o termo melhora o backtest (eliminatórias/Copa América/Euro/Nations League), **não** as previsões da Copa.

**6. Custo de adotar.** **Médio-alto:** é mudança de modelo → `predictor.lambdas`/`ved_from_elo` passam a ler `δ_conf` no mando; **rebuild** (`features_pit`+`predictor`) + **nova versão** (`baseline-v0.5-confed`). Não é flag barata.

**7. P(passar).** **~0,45** — **acima** do prior base (~0,25), justificado: não é tweak de parâmetro do núcleo (esses estão esgotados), é **sinal geográfico novo e independente**, da mesma família da altitude (que passou), com sinal bruto já medido sobrevivendo aos dois confundidores óbvios com IC>0. Não inflo além disso porque a perna CONMEBOL é marginal em n e o valor para 2026 é baixo.

**8. Harness reproduzível** (`calibrate_confed.py`, esqueleto):
```python
# treino<2015: fit δ_conf por mando; teste>=2015: ΔBrier 1X2 pareado + IC bootstrap
CONF = {...}  # seleção -> {CONMEBOL,UEFA,...}; congelar do treino
def gate_confed(conn, B=10000, seed=12345):
    rows = q("SELECT mf.dr_adj, m.home_score, m.away_score, m.neutral, th.name hn, m.date "
             "FROM matches m JOIN match_features mf USING(match_id) JOIN teams th ...")
    train = rows[date<2015 & not neutral]; test = rows[date>=2015 & not neutral]
    delta = fit_home_delta_by_conf(train)            # 1 tabela, escolhida no treino
    base  = brier_1x2(test, mando=100)               # modelo atual
    cand  = brier_1x2(test, mando=100+delta[conf])   # com confederação
    return paired_delta_brier(base, cand, B, seed)   # ΔBrier + IC95; guarda ECE + neutro + BTTS
```
Decisão: adota só se IC95 **não cruza zero** na perna UEFA **e** ECE/neutro/BTTS não regridem. Seed 12345, B=10.000 (padrão do projeto).

---

### TOP 3 — ε do mata-mata (pênaltis) recalibrado com `shootouts.csv`

**1. Hipótese e mecanismo.** No `knockout_advance`/`simulate`, o empate do mata-mata é dividido `0,5 + ε·sinal(dr)`, com **ε = 0,03 hardcoded "[a calibrar]"**. A disputa de pênaltis não é moeda perfeita: o mais forte avança um pouco acima de 50%. O `calibrate_ko.py` já existe para medir ε empiricamente — só nunca foi fechado.

**2. Independência medida.** ε é um parâmetro da **árvore de simulação**, não um termo de λ/dr de jogo; corr com `dr` ~0 por construção (mede o resíduo do desempate condicionado em `dr`).

**3. Dado.** `dados/shootouts.csv` (677 disputas com `dr` pré-jogo casável). R$0, offline, **intacto** (a fonte que o prompt aponta como a única do poço externo ainda não esgotada).

**4. Portão (dois níveis).**
- **Estimação de ε (powered):** `ε̂ = P(mais forte vence) − 0,5 = +0,049`, **IC95 Wilson [+0,012, +0,087]**, n=677. O `0,03` atual **cai dentro** do IC (não é rejeitado), mas o ponto medido é **0,049**.
- **Impacto no título/avanço (sub-powered):** gate seria leave-one-World-Cup-out no Brier de avanço, mas só há **35 disputas em toda a história da Copa (~2,9 por edição)** → o portão **não tem potência** para distinguir 0,03 de 0,05. **Reprova por falta de dado, não de sinal** — então não se "adota via portão de título"; adota-se via **calibração direta do parâmetro** (fecha o `[a calibrar]` com o número medido).

**5. Efeito esperado.** Microscópico nas probabilidades de título: ε só atua na fração de empate (~25%) dos ~2–3 mata-matas que vão a pênaltis por Copa. Mover 0,03→0,049 desloca um avanço em ~0,005 nos confrontos afetados. **Não muda decisão.**

**6. Custo de adotar.** **Trivial:** `PredictParams.eps_ko = 0.049` (config), **só simulação**, sem rebuild, sem nova versão de modelo de 1 jogo. Documentar como D-novo "ε fechado em 0,049 [medido, n=677]".

**7. P(passar).** ~0,7 de **ser útil/honesto** (fechar placeholder com dado), mas **P(mudar qualquer conclusão) ~baixa**. É higiene boa, não evolução.

**8. Harness reproduzível** (já existe):
```bash
python -m scm.calibrate_ko --shootouts dados/shootouts.csv          # imprime ε̂ + IC + buckets por |dr|
# resultado atual: P(mais forte vence)=0,549  IC[0,512,0,587]  ε̂=+0,049 [+0,012,+0,087]  (n=677)
# ação: setar PredictParams.eps_ko=0.049; opcional --only-major (n=93, P=0,624) como sensibilidade
```

---

## 3. Veredito honesto

**O que NÃO vale tentar (e por quê).**
- **Descanso/congestão como termo de modelo:** efeito **medido ~0** (`corr(Δdescanso, resíduo)=0,0005`; swing de mando ~0,0037 ponto). "Descanso desde o último jogo internacional" **não é fadiga** — entre datas FIFA os jogadores jogam pelos clubes. Pior: numa Copa o calendário é **fixo e simétrico** (Δdescanso≈0), então mesmo se houvesse sinal, ele não tocaria a previsão de 2026. Sub-powered no único recorte que importa (49 jogos major no teste).
- **Re-propor qualquer rejeitado** (DC, recal, σ-Glicko, σ_dr, calor, estilo, T_base, xG, cartões/escanteios, σ-por-time na sim): sem ângulo novo, é proibido e perde tempo.
- **Buscar dado externo R$0 novo:** o poço **secou**. `results`/`shootouts`/`goalscorers`/StatsBomb(`xg`,`setpiece`,`timing`)/`climatology` já foram explorados; o que passou já está dentro. `shootouts` é o último com algo a fechar (ε acima) e mesmo assim não move decisão.
- **Elo intra-torneio / correlação entre jogos na sim:** ideias reais, mas o gate é leave-one-WC-out com **pouquíssimas Copas** → não-gateável com potência. Reprova por dado, não por sinal; mantenha como nota, não como entrega.

**A melhor melhoria agora é OPERACIONAL, não de modelo.** O núcleo Elo→Poisson está no teto (confirmado por ~12 rejeições do portão). O único termo com sinal novo (mando por confederação) **melhora o Brier histórico mas ~não toca a Copa 2026** (sede neutra). Logo, durante o torneio que está acontecendo, o retorno por unidade de esforço é máximo em **medir bem**: capturar a **linha de fechamento** para CLV real, e ligar **reliability + alarme de drift por mercado** no `monitor`. Isso não promete ganho de Brier — promete **saber, com IC, se o modelo tem skill na Copa real e detectar deriva antes que custe**. É o que o próprio projeto vem concluindo desde D-49/06-21: **pare de adicionar fórmula; meça.**

> Se for mexer no modelo mesmo assim, o único candidato que merece o portão é o **mando por confederação** (Top 2) — com a expectativa explícita de que é um ganho de *backtest*, não de *Copa 2026*.

---

### Anexo — comandos do STEP 0 (reprodutível)
Todas as medidas saíram de `dados/scm.sqlite` + `dados/shootouts.csv` (até 2026-06-24):
- **Descanso:** rest-days PIT por time (dias desde o jogo anterior) → Δrest; teste≥2015; `corr(Δrest,dr_adj)=−0,084`; `corr(Δrest,resíduo)=0,0005`; informativo |Δrest|≥3 não-amistoso = 1.860 (major 49).
- **Pênaltis:** join `shootouts.csv`↔`match_ratings.dr`; `P(mais forte vence)=0,549` IC[0,512,0,587]; ε̂=0,049; WC=35 disputas (~2,9/edição).
- **Confederação-mando:** resíduo `(pontos_casa − we_home)` em não-neutros 2000+; CONMEBOL +0,061 (fora-altitude +0,040 IC>0); UEFA −0,037/−0,040 (estável); teste≥2015 não-neutro: CONMEBOL 369, UEFA 1.530; corr com `dr_adj` 0,017/0,185.
