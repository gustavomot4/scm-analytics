---
tags: [camada1, auditoria, historico]
status: historico
tipo: auditoria
data: 2026-06-15
aliases: ["Auditoria 2"]
---

# Camada 1 — Revisão Crítica v2 (Auditoria de 2ª rodada)
**Projeto:** Sistema de previsão de partidas — Copa do Mundo 2026
**Documento auditado:** [[camada1-planejamento-v2]] (v2, 2026-06-15)
**Base de comparação:** [[camada1-revisao]] (auditoria que gerou a v2) · [[camada1-planejamento-v1]] · 3 execuções manuais em `analises/` · `dados/registro-previsoes.csv`
**Data da revisão:** 2026-06-15 · **Status:** auditoria de planejamento · **Custo-alvo:** R$ 0

> Convenções herdadas (V/E/D, λ, dr, W_e, [a calibrar]). Severidade: 🔴 estrutural (corrigir antes de o backtest valer) · 🟡 relevante (corrigir junto do backtest) · ⚪ menor (anotar). Esta é uma **segunda rodada**: a primeira auditoria já corrigiu a v1 → v2. O objetivo aqui é achar o que a v2 **introduziu ou deixou em aberto**, não repetir o que já foi resolvido. Toda afirmação numérica abaixo foi reconferida em código (Poisson, W_e, propagação de incerteza) — ver §2 e §5.

---

## 1. Resumo da revisão

**O que está sólido na v2 (e deve ser mantido sem mexer):**

- As duas correções 🔴 da 1ª auditoria estão **corretamente integradas ao contrato**: o gerador de gols não satura mais (`GD = θ·dr/100`, total sensível a mismatch) e o mando histórico está separado em `H_hist` (construção do Elo) vs `H_host2026` (previsão). A execução **ESP×CPV** demonstra o conserto em ação (λ 2.84×0.26, modal 3x0 — algo que a v1 era incapaz de exprimir).
- **A aritmética do pipeline está certa.** Reconferi as três execuções: over 2.5 e BTTS batem ao decimal (CAN-BIH 31.2%/32.6%, BEL-EGY 51.1%/49.2%, ESP-CPV 59.9%/21.6%), e o score de confiança reproduz exatamente (BEL-EGY 66.7≈67, ESP-CPV 82.4≈82). O documento é implementável e auditável como promete.
- A disciplina anti-autoengano continua madura: snapshot local, registro pré-jogo imutável, recusa explícita em inventar fontes (odds e lesões), portão de backtest para variáveis novas, IC bootstrap, teste pareado vs mercado. **Isto é o coração do projeto e está certo.**
- A postura honesta na própria saída ("placar mais provável ainda é improvável", "não é ferramenta de lucro") permanece.

**O que NÃO está sólido e precisa mudar:**

- 🟡 **A leitura Elo-direto produz P(D) negativo em mismatch alto.** Confirmado em ESP×CPV: P(D) = −0.42%. A própria análise flagou como "micro-achado", mas **o contrato da v2 (§9–10) nunca foi corrigido** — só o clamp acidental do ensemble final esconde o sintoma. É uma violação do invariante "probabilidades em [0,1]".
- 🟡 **O clamp `λ_B ≥ 0.2` viola silenciosamente `T_m` e `GD` no tail — e o doc afirma o oposto** ("clampa em 0.2 sem violar nada", §8). Em dr=900 o total e o saldo realizados divergem do definido. Pequeno na prática, mas é uma inconsistência não-documentada exatamente no regime de goleada que a v2 foi construída para tratar.
- 🟡 **O score de confiança fica ALTO onde a confiabilidade é MENOR.** `separação` (peso 0.35, o maior) cresce com o mismatch, mas mismatch extremo no formato de 48 times costuma vir de **estreantes com rating provisório e ruidoso**. Resultado real no registro: **ESP×CPV recebeu a maior confiança do registro (82)** apesar de a análise dizer que "o rating de Cabo Verde é o menos confiável". A v2 mede "quão definido é o jogo", não "quão confiável é a previsão" — e os dois divergem precisamente nos mismatches.
- 🟡 **Forma funcional do GD trocada por decreto.** A v1 saturava (subprevia goleada); a v2 impôs **linearidade estrita** (`GD = θ·dr/100`). A relação saldo×Elo é provavelmente **côncava** no extremo, e há pouquíssimos jogos com |dr|>500 (justo os ruidosos de minnow). Extrapolar linear até dr=900 dá GD=4.05 (~4–5 gols de margem rotineiros) — risco de cometer o **erro oposto** ao da v1. O backtest deve escolher a forma, não o planejamento.
- 🟡 **Contradição latente no papel do ataque/defesa (C3):** a v2 quer que o gerador ATA/DEF seja **gerador primário** (§18.2) E **leitura independente do ensemble** (§9) ao mesmo tempo — são mutuamente exclusivos.

**Lacuna de dados nº 1 (gratuita, local, ainda ausente):** a v2 trata o Elo como **estimativa pontual**, mas toda execução escreve "±20–30 de incerteza" à mão. **Promover a incerteza do rating a variável de primeira classe** (SE por seleção, grande para provisórios) e **propagá-la para a probabilidade** resolve de uma vez o problema do minnow (CPV), o P(D) negativo e a confiança invertida — e é de graça (deriva do mesmo histórico).

**Veredito de tech lead:** a v2 é uma **especificação melhor**, não ainda um **sistema melhor** — nenhuma linha foi backtestada e todo parâmetro é [a calibrar]. Aprovar para implementação **condicionada a**: (a) rodar o 1º backtest do contrato congelado antes de adicionar qualquer feature; (b) aplicar os patches de coerência 🟡 de §2 (são baratos e evitam que a sofisticação nova vire falsa confiança). Os itens ⚪ acompanham a Camada 2.

---

## 2. Erros e inconsistências encontrados

### 2.1 🟡 P(D) negativo na leitura Elo-direto em |dr| alto — invariante [0,1] violado
A decomposição da §9/§10 é `P(V) = W_e − P(E)/2`, `P(D) = 1 − P(V) − P(E) = 1 − W_e − P(E)/2`. Logo **`P(D) < 0` sempre que `P(E) > 2·(1 − W_e)`**. Em ESP×CPV (dr=572): `W_e = 0.9642`, `P(E)≈0.08` → `P(D) = −0.0042`. A condição geral de validade é:

```
P(E | dr)  ≤  2 · min(W_e, 1 − W_e)        # senão P(V) ou P(D) sai de [0,1]
```

A raiz é que a **curva de empate `P(E|dr)` é ajustada independentemente de `W_e`** e nada garante a compatibilidade entre as duas no extremo. O ensemble final clampa em [0.02,0.96] e mascara o sintoma — mas isso é sorte de pipeline, não correção: a leitura `P_elo` entra **errada** na média ponderada antes do clamp. A análise ESP×CPV já tinha apontado isto como "micro-achado"; **o contrato da v2 não foi atualizado**. Correção em §5.2.

### 2.2 🟡 O clamp `λ_B ≥ 0.2` viola `T_m` e `GD` — e o doc diz "sem violar nada"
§8 afirma: "λ_B clampa em 0.2, o azarão nunca fica sem chance) sem violar nada". Falso no tail. Com θ=0.45, κ=0.10, T_base=2.6:

| dr | GD definido | T_m definido | λ_A | λ_B (cru) | λ_B (clamp) | **total realizado** | **GD realizado** |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 900 | 4.050 | 3.500 | 3.775 | −0.275 | 0.200 | **3.975** (≠3.500) | **3.575** (≠4.050) |

O clamp adiciona massa de gols ao azarão (sobe o total) e comprime o saldo — os dois contratos (passos 3 e 4 da §8) deixam de valer exatamente no regime de goleada. O efeito é pequeno e até benigno (funciona como regularização), mas **não está documentado** e a afirmação "sem violar nada" precisa sair. Some de vez ao migrar para o gerador ATA/DEF (§11.2), onde `λ > 0` por construção (link exponencial) e o clamp é desnecessário. Correção em §5.3.

### 2.3 🟡 Contradição no papel do ATA/DEF (C3): gerador primário XOR membro independente
- §18.2: "avaliar 11.2 (ataque/defesa) **como gerador primário**".
- §9: "o upgrade C3 adiciona `P_ad` (ataque/defesa, não ancorado em W_e) como **3ª leitura genuinamente independente**", redistribuindo pesos para 0.35/0.25/0.20/0.20 (Poisson/Elo/AD/mercado).

Se ATA/DEF **vira** o gerador do Poisson, então `P_poisson` e `P_ad` são **o mesmo objeto** e não podem ambos contar como membros independentes do ensemble — a "diversidade real" que a C4 tanto defende seria fictícia de novo, só que com outro rótulo. A v2 quer as duas coisas. É preciso escolher no contrato: **(a)** manter GD/T_m como `P_poisson` e somar ATA/DEF como `P_ad` separado (duas fontes de λ distintas → diversidade genuína); **ou (b)** ATA/DEF substitui o Poisson e a 3ª leitura independente tem de vir de outro lugar (na prática, só mercado → o ensemble cai para 2 sinais reais). Correção em §5.5.

### 2.4 🟡 Confiança alta onde a confiabilidade é baixa (mismatch × rating de baixa amostra)
`separação = clamp((p_max − 1/3)/(2/3),0,1)` tem o **maior peso (0.35)** e cresce monotonicamente com p_max — que cresce com |dr|. Mas |dr| grande no formato de 48 times vem com frequência de **estreantes/minnows com rating provisório** (a própria v2 marca <30 jogos como provisório). O único contrapeso é 0.2×0.20 = 0.04 do checklist `dados` ("Elo maduro/não-estreante"). Líquido: **jogos de baixa informação recebem confiança ALTA.** Evidência no registro:

| Jogo | dr | Confiança | Observação da própria análise |
|---|---:|---:|---|
| ESP×CPV | 572 | **82** (a maior) | "o rating de Cabo Verde é o **menos confiável** do registro" |
| BEL×EGY | 213 | 67 | inputs razoáveis |
| CAN×BIH | 216 | 62 | "Canadá só joga amistoso há 2 anos" |

A v2 confunde **"quão definido é o jogo"** com **"quão confiável é a previsão"**. São conceitos diferentes e divergem exatamente nos mismatches que o torneio vai criar. Correção em §5.4 (tornar a maturidade do rating um portão multiplicativo e/ou amarrar a confiança à incerteza propagada do rating de §5.1).

### 2.5 🟡 Forma funcional do GD assumida (linear), não estimada
§8/§11.1 dizem que θ "sai de regressão `saldo_real ~ dr/100`". A regressão calibra a **inclinação**, não justifica a **forma**. A v2 fixou a forma como estritamente linear para matar a saturação da v1 — mas isso troca um viés por outro: no extremo (|dr|>500, onde os dados são mais escassos e mais ruidosos), saldo provavelmente cresce de forma **côncava** (favorito tira o pé, rodízio, placar é limitado superiormente). GD linear a dr=900 ⇒ 4.05 gols de margem como expectativa rotineira é agressivo. Não é "erro de conta", é **premissa de modelagem não declarada como tal**. Correção em §5.3 (deixar o backtest escolher entre linear / potência suave `θ·(dr/100)^p`, p<1 / saturação suave com teto alto, por Brier/RPS com IC; e sinalizar extrapolação além do suporte de dados).

### 2.6 ⚪ Itens menores (anotar)
- **§12 fixa "modal ~10–12%, ~88% de chance de NÃO ser ele"** como cópia de UX. A correção C1 quebra essa constante: em ESP×CPV o modal é **2x0 a 18.1%** (≈82% de não ser). A comunicação tem de ser **derivada da matriz por jogo**, não um número fixo — senão a §12 contradiz o regime de goleada que a v2 habilitou.
- **Ramo "sem odds" da confiança é ambíguo (§14):** o texto diz tanto "`corrob_ext` = 0.5 (neutro)" QUANTO "renormaliza-se o restante". São duas operações diferentes, com scores diferentes. Um dev não sabe qual implementar — quebra o critério "qualquer dev implementa lendo só o doc". Fixar **uma**.
- **Registro real diverge do contrato de validação:** §15 exige `hash_inputs` na linha imutável, mas `registro-previsoes.csv` **não tem essa coluna**; e mistura `v0.1-manual` (gerador saturado da v1!) com `v2.0-manual` sem dizer como a validação filtra por versão. Sem `hash_inputs`, a alegação "imutável e auditável" fica parcialmente vazia. Adicionar a coluna e o filtro por versão.
- **Linha StatsBomb desatualizada (favoravelmente):** a v2 lista cobertura "Copa 2018, Euro, WWC". O StatsBomb Open Data **já publica a Copa 2022** (com 360). Corrigir — amplia a base de backtest com xG (§4).

---

## 3. Dados e variáveis adicionais propostos

Critério mantido: **gratuito, local, derivável**; entra como diagnóstico e só vira termo do modelo se passar no portão de backtest (§16 da v2). Em ordem de valor.

### 3.1 Incerteza do rating como variável de primeira classe — **a maior lacuna recuperável da v2**
A v2 trata Elo como ponto. Toda execução escreve "±20–30" à mão e o problema do minnow (CPV) fica sem resposta estrutural — a v2 só oferece "flag de baixa confiança", que é metadado, não entra na probabilidade. Proposta: estimar um **erro-padrão por seleção `σ_R`**, função de (nº de jogos na janela efetiva, recência, **diversidade de oposição** — quem só jogou contra fracos tem σ alto), grande para provisórios (<30 jogos). Dois usos, ambos de graça (mesmo histórico): **(a)** propagar `σ_R` para V/E/D (§5.1) — encolhe probabilidades extremas de favoritos mal-medidos para perto de 1/3, que é a correção certa para o caso CPV; **(b)** alimentar a confiança de forma principiada (resolve 2.4). É a peça que falta para o sistema parar de fingir precisão pontual que ele não tem.

### 3.2 Flag de troca de técnico — grátis, ataca uma limitação declarada
A v2 lista "Elo reage devagar a troca de geração/técnico" como limitação e **não propõe nada**. Troca recente de comando é um choque de regime documentado. Derivável de graça (Wikipedia/notícias, manual como as convocações). Uso: **alargar `σ_R`** (alimenta 3.1) e/ou rebaixar confiança quando o técnico assumiu há poucos jogos. Custo baixo, valor real no recorte de ~16 seleções.

### 3.3 Valor de mercado / idade-caps como **prior** para regularizar rating de baixa amostra
A v2 já coleta idade do elenco, mas só como "proxy de volatilidade" (diagnóstico vago). Reenquadrar: para estreantes/provisórios (CPV), um **prior de talento** (valor agregado do elenco, ou idade/caps) é um regularizador que encolhe um Elo não-confiável na direção de uma âncora independente de resultados — exatamente a alavanca que falta para o minnow. Transfermarkt restringe scraping no ToS → manual, e **só** para o shortlist (a v2 já faz tiers manuais para essas seleções). Declarar o ToS honestamente; não automatizar.

### 3.4 Cenários de classificação determinísticos — não é "feature", é dado derivado grátis
O modelo **não consegue** capturar incentivo de última rodada (risco irredutível, declarado). Mas pode **enumerar deterministicamente** "o Time X avança se vencer; ou empatar e Y perder; ..." a partir do calendário + pontos atuais (fixturedownload, já em mãos). Transforma um risco não-modelável em **saída transparente**. Também é insight (§6.3).

### 3.5 Candidatos de baixa prioridade (atrás do mesmo portão, sem recomendação)
- **Defasagem de fuso/circadiana** para seleções intercontinentais em horários locais dos EUA (distinto de km de viagem da v2). Efeito pequeno, overfit fácil — só como candidato.
- **Histórico de disputas por pênaltis** para refinar o `ε=0.03` do mata-mata. Amostra ínfima; manter pênalti como moeda. Mencionado por completude.

### 3.6 Reafirmar o que **não** perseguir (honestidade, igual à v2)
Posse de bola e distância percorrida: sem fonte gratuita estruturada para seleções e preditores fracos. **Understat tem xG grátis, mas só de clubes europeus** — não serve para seleções a não ser como proxy indireto e manual do estado de forma dos jogadores; baixíssima prioridade. Odds históricas internacionais gratuitas: seguem inexistentes de forma confiável → comparação com mercado continua **prospectiva** em 2026.

---

## 4. Fontes de dados adicionais (tabela)

Mesmos critérios da §6 da v2. Verificadas em 2026-06-15; disponibilidade muda → **snapshot local é a defesa** (princípio já adotado). Foco no que é **novo ou corrigido** em relação à tabela da v2.

| Fonte | Dado | Grátis? | Key? | Limitações | Confiab. | Papel | Fallback |
|---|---|---|---|---|---|---|---|
| **StatsBomb Open Data** *(correção)* | eventos + **xG** + 360; agora inclui **Copa 2022** além de 2018/Euro/WWC | Sim | Não | ainda **sem 2014 nem Copa América**; não ao vivo; licença **não-comercial** | Alta | **backtest xG ampliado** (2018+2022) + prior de estilo | FBref visual |
| **RealGM — xG Tracker WC 2026** *(nova)* | xG por jogo da Copa 2026, pós-jogo | Sim | Não | **terceiro de fonte única**, não-API, copiar à mão; metodologia própria | Média (validar vs StatsBomb onde houver overlap) | xG **in-tournament** por captura manual (como as odds) | StatsBomb (só histórico) |
| **oddspapi.io** *(nova, a validar)* | odds 1X2 multi-casa, inclui histórico (alegado free tier) | **Alegado** | Sim | **autopromoção do vendor**; limites/cobertura de Copa não confirmados — testar antes de depender | A validar | candidato a odds gratuitas; **NÃO** assumir até teste | captura manual (plano base) |
| **Understat** *(nova, baixa prio.)* | xG/npxG — **só clubes europeus** | Sim | Não | não cobre seleções; útil só como proxy indireto de forma de jogador | Alta (clubes) | enriquecimento marginal | ignorar |
| **football-data.org** *(reafirmar)* | jogos/resultados WC no free tier | Sim | Sim (grátis) | 10 req/min; sem escalações no free | Alta | automação de resultados | martj42 + manual |
| **Open-Meteo (+Elevation/Geocoding)** *(reafirmar)* | temp/umidade kickoff; altitude; coords | Sim | **Não** | uso não-comercial; efeito pequeno | Alta | calor/altitude/viagem (diagnóstico) | Wikidata; hardcode |

**Reconfirmado, não inventar:** odds gratuitas via API continuam sem garantia (`oddspapi.io` é candidato a testar, não fato; o plano base segue captura manual com timestamp); lesões estruturadas para 48 seleções seguem JSON manual + RSS na Camada 3. **APIs pagas (Sportmonks, TheStatsAPI, iSports, API-Football) violam o custo-alvo R$ 0 — fora de escopo por definição.**

---

## 5. Modelos revisados (fórmulas / pseudocódigo)

### 5.1 Rating com incerteza + propagação para a probabilidade (resolve a lacuna 3.1, mitiga 2.4 e o problema do minnow)
Tratar Elo como `R ± σ_R` e integrar a expectativa sobre a incerteza do `dr`:

```
sigma_dr = sqrt(sigma_RA^2 + sigma_RB^2)          # erro-padrão da diferença
# E[W_e] sobre dr ~ Normal(dr0, sigma_dr): MC barato (10^4 amostras) ou correção de 2ª ordem:
#   E[W_e] ≈ W_e(dr0) + 0.5 * sigma_dr^2 * W_e''(dr0)     (puxa extremos p/ 0.5 — Jensen)
P(V), P(E), P(D)  derivados de E[W_e] (curva de empate), não de W_e(dr0)
```

Efeito verificado numericamente (dr0=572, como em ESP×CPV):

| σ_dr | E[W_e] | Δ vs pontual |
|---:|---:|---:|
| 0   | 0.9642 | — |
| 75  | 0.9612 | −0.0030 |
| 150 | 0.9511 | −0.0131 |
| 250 | 0.9259 | −0.0383 |

Ou seja: um favorito medido contra dois ratings provisórios (σ_dr alto) recebe **automaticamente** uma probabilidade menos extrema — a correção certa para CPV, **de graça** e principiada (não um band-aid de confiança). Entra atrás do portão de backtest como qualquer coisa, mas é a adição de maior retorno.

### 5.2 Curva de empate consistente + clamp por leitura (resolve 2.1)
Impor a restrição de validade como **hard constraint** no ajuste de `P(E|dr)` e clampar **antes** do ensemble:

```
P(E|dr)  :=  min( P(E_empirico|dr),  2*min(W_e, 1-W_e) - eps )   # garante P(V),P(D) >= 0
para CADA leitura k:  P_k(x) <- clamp(P_k(x), 0, 1); renormalizar      # nao so no ensemble final
```

Isto faz a leitura `P_elo` entrar **válida** na média ponderada, em vez de entrar negativa e ser salva por acidente pelo clamp final.

### 5.3 Forma funcional do GD escolhida por dados, não por decreto (resolve 2.5; ajuda 2.2)
Não assumir linear. Ajustar e comparar por Brier/RPS **com IC**, point-in-time:

```
candidatos:  GD = theta*(dr/100)                  # linear (v2 atual)
             GD = theta*(dr/100)^p,  0<p<=1        # potencia suave (concava se p<1)
             GD = G_max * tanh(theta*dr/(100*G_max))   # saturacao SUAVE, teto alto (≠ teto 1.5 da v1)
restricao: monotona crescente; |dr| alem do suporte de dados -> extrapolar com cautela + alargar sigma (5.1)
```

Migrar a geração de λ para ATA/DEF (§11.2) torna o clamp de 2.2 desnecessário (`λ = exp(...) > 0`), resolvendo 2.2 e 2.5 na mesma jogada.

### 5.4 Confiança que mede confiabilidade, não só "quão definido" (resolve 2.4)
Separar os dois conceitos e tornar a maturidade do rating um **portão multiplicativo**, não um item somado:

```
g_rating = 1 - clamp(sigma_dr / sigma_ref, 0, 0.6)        # rating incerto DERRUBA a confianca
score = 100 * (0.35*separacao + 0.15*consist_int + 0.15*corrob_ext + 0.20*dados + 0.15*robustez)
        * g_rating * (0.90 se mata-mata) * (0.85 se ultima rodada c/ incentivo)
# efeito desejado: ESP×CPV (sigma_dr alto p/ estreante) NAO termina como a maior confianca do registro
```

Alternativa mínima (se não implementar σ_R já): subir o peso de "Elo maduro/não-estreante" dentro de `dados` e transformá-lo em multiplicador. O ponto é: **mismatch contra minnow mal-medido não pode pontuar alto.**

### 5.5 Resolver o fork do ATA/DEF no contrato (resolve 2.3)
Decidir explicitamente e escrever no documento:

```
OPCAO A (recomendada p/ preservar diversidade do ensemble):
   P_poisson  := GD/T_m (5.3) OU ATA/DEF — UM deles é o gerador primario de lambda
   P_ad       := a OUTRA leitura, se e somente se for um gerador DISTINTO do primario
   -> se ATA/DEF vira primario, P_ad some e o 3o sinal independente = mercado (ensemble = 2 sinais reais)
OPCAO B: manter GD/T_m como primario e ATA/DEF como P_ad separado -> 3 sinais genuinos {Elo, AD, mercado}
```

Não dá para ATA/DEF ser primário **e** membro independente. Escolher e registrar.

---

## 6. Novos insights habilitados

Tudo abaixo é grátis e local, em cima dos dados atuais + adições de §3.

1. **Bandas de probabilidade por incerteza de rating** (sai de §5.1): publicar `P(V) = 62% [55–68]` em vez de um ponto. Serve diretamente ao requisito "probabilidades, nunca certezas" — e mostra honestamente que CPV-tipo tem banda larga.
2. **Índice de zebra / variância**: sinalizar jogos onde o favorito é forte mas a combinação (rating incerto + azarão defensivo + total baixo) torna a zebra **desproporcional ao P**. Já há um caso detectado à mão: ESP×CPV BTTS 22% (modelo) vs ~40% (mercado) — o modelo pode ser severo demais com o ataque do azarão. Formalizar como flag.
3. **Árvore de cenários de classificação** (§3.4): "o que cada time precisa para avançar", determinístico, grátis. Ataca o risco de incentivo de última rodada **por transparência** (o modelo não prevê motivação, mas enumera o que está em jogo).
4. **Relatório modelo-vs-mercado (divergência)** com aviso explícito de que **não é ferramenta de aposta**: formaliza o que as análises já fazem à mão (o gap de BTTS em ESP×CPV). Onde diverge muito do mercado de-vigado, é candidato a erro do modelo OU a leitura genuína — sempre rotulado como estudo.
5. **Manter os já promovidos na v2:** Monte Carlo do torneio, sensibilidade por previsão (já demonstrada nas 3 execuções), e regressão à média por xG (StatsBomb, agora com 2018+2022). Reafirmar — são os de maior valor percebido.

---

## 7. Riscos e limitações

**O maior risco é meta e novo nesta rodada:** **nada da v2 foi validado.** Zero backtest rodou; θ, κ, T_base, tiers, pesos e a curva `P(E|dr)` são todos [a calibrar]; as três execuções usam Elo de **fonte única ou estimado** (não o Elo próprio do martj42, que ainda não existe) e inputs de forma/estilo estimados de resumos. O perigo concreto é que a sofisticação **adicional** da v2 produza **falsa sensação de "melhorou"** sem uma única medida empírica. A v2 é um contrato melhor; não é um sistema melhor até o backtest dizer que é.

**Riscos estruturais remanescentes / introduzidos:**

- **Rating de minnow/estreante (CPV) é a fragilidade central** e o formato de 48 times a amplifica. §5.1 mitiga, mas a própria §5.1 é não-validada e depende de uma boa estimativa de `σ_R`.
- **Forma funcional do GD no tail** (2.5): risco de superprever margem — o erro oposto ao da v1, ainda não medido.
- **Confiança anti-correlacionada com confiabilidade** (2.4) até o portão de §5.4 entrar.
- **"Mercado" é um benchmark mais fraco do que o rótulo sugere:** as execuções usam **uma casa** (CBS, bet365), não fechamento nem consenso. `corrob_ext` superdimensiona a concordância com 1 book; o peso 0.20 no ensemble sobre uma linha possivelmente stale também.
- **xG por backtest cobre só uma fração:** StatsBomb ampliou para 2018+2022, mas segue **sem 2014 nem Copa América** — a validação por xG vale para parte do conjunto de ~400 jogos; licença não-comercial limita redistribuição.
- **Overfitting cresce com cada variável** (mantido da v2; σ_R, técnico, valor, fuso também passam pelo portão de IC-que-não-cruza-zero).
- **Incertezas irredutíveis declaradas:** `H_host2026`, tiers de desfalque, altitude/calor, México "quase-casa", incentivos de fim de grupo. §3.4 torna o último **transparente**, mas nenhuma some.
- **Apostas:** mantido — Brier ~0.60 não é edge sobre mercado com margem; corrigir saturação melhora placar, não vira lucro. Fica escrito na interface.

---

## 8. Próximos passos recomendados (a ordem importa)

1. **Antes de qualquer feature nova: rodar o 1º backtest do contrato v2 congelado** — Elo com `H_hist` → GD/T_m → Poisson 0..10, point-in-time, com IC bootstrap e teste pareado vs Elo público. Sem isto, tudo o mais é decoração (princípio do próprio documento). *Desbloqueia a decisão de tudo.*
2. **No mesmo backtest, decidir a FORMA FUNCIONAL do GD** (§5.3) — linear vs côncava vs saturação suave, por Brier/RPS com IC. Não assumir linear.
3. **Patches de coerência (baratos) antes de o backtest "valer":** restrição da curva de empate + clamp por leitura (§5.2); clamp simétrico/renormalizado ou migração para ATA/DEF (§5.3 resolve 2.2); resolver o fork ATA/DEF no contrato (§5.5); desambiguar o ramo "sem odds" da confiança (2.6); adicionar `hash_inputs` ao CSV e o filtro por `versao_modelo` (2.6); corrigir a linha StatsBomb (2.6/§4).
4. **Implementar a incerteza do rating** (§5.1): estimar `σ_R`, propagar para V/E/D, e **re-derivar a confiança** (§5.4) para que ela pare de premiar mismatch incerto.
5. **Atualizar a tabela de fontes:** StatsBomb 2022, RealGM xG tracker (manual, in-tournament), `oddspapi.io` (a validar com teste real de rate limit/cobertura antes de qualquer dependência).
6. **Flag de troca de técnico + prior de valor/idade** (§3.2/§3.3) como diagnóstico, sempre atrás do portão.
7. **Construir os cenários de classificação determinísticos** (§3.4/§6.3) — alto valor percebido, custo quase nulo, e ataca o risco de incentivo por transparência.
8. **Só então** pesos finos do ensemble (≥30 jogos) e a leitura `P_ad`, conforme a opção escolhida em §5.5.

**Milestone de aceite (atualiza o da v2):** backtest com Elo corrigido por mando, pipeline congelado e point-in-time, **Brier < uniforme com IC que não cruze o baseline** e ≈ Elo público — **e mais dois invariantes novos desta auditoria:** (i) `P(D) ≥ 0` e `P(V) ≥ 0` em **todo** |dr| do backtest (§5.2); (ii) a confiança **não cresce** com a incerteza do rating (§5.4). Sem isso, o resto é decoração.

---
*Auditoria de 2ª rodada — sem código de implementação, por escopo. A v2 corrigiu bem os 🔴 da v1; esta revisão trata o que a v2 introduziu (clamp/contrato no tail, confiança invertida, fork do ATA/DEF) ou deixou aberto (P(D) negativo, incerteza do rating como variável). Toda afirmação numérica foi reconferida em código. Fontes verificadas em 2026-06-15; snapshot local é a defesa contra mudança de disponibilidade. Probabilidades, nunca certezas — inclusive sobre o próprio modelo, que segue não-validado até o primeiro backtest.*
