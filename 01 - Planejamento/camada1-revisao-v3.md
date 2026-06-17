---
tags: [camada1, auditoria, historico]
status: historico
tipo: auditoria
data: 2026-06-15
aliases: ["Auditoria 3"]
---

# Camada 1 — Revisão Crítica v3 (Auditoria de 3ª rodada)
**Projeto:** Sistema de previsão de partidas — Copa do Mundo 2026
**Documento auditado:** [[camada1-planejamento-v3]] (v3.0, 2026-06-15)
**Base de comparação:** [[camada1-revisao]] (1ª rodada → v2) · [[camada1-revisao-v2]] (2ª rodada → v3) · [[camada1-planejamento-v1]]/v2.md` · 8 execuções em `analises/` · `dados/registro-previsoes.csv`
**Data da revisão:** 2026-06-15 · **Status:** auditoria de planejamento · **Custo-alvo:** R$ 0

> Convenções herdadas (V/E/D, λ, dr, W_e, σ_R, σ_dr, **[a calibrar]**). Severidade: 🔴 estrutural (corrigir antes de o backtest valer) · 🟡 relevante (corrigir junto do backtest) · ⚪ menor (anotar). Esta é a **3ª rodada**: a v1→v2 corrigiu saturação e mando; a v2→v3 corrigiu coerência [0,1] e introduziu incerteza de rating. O objetivo aqui é achar **o que a v3 introduziu ou deixou aberto** — não repetir o que já foi resolvido. **Toda afirmação numérica abaixo foi reconferida em código** (propagação E[W_e], cap da curva de empate, GD/T_m no tail, aritmética das 8 análises) — ver §2 e §5. IDs novos: **A1–A11**.

---

## 1. Resumo da revisão

**O que está sólido na v3 (manter sem mexer):**

- **A aritmética continua exata — agora confirmada uma 3ª vez, em código.** Reproduzi o pipeline das execuções e ele bate com o CSV a menos de arredondamento de λ: ESP×CPV over 2.5 = 0.599 (CSV 0.599), BTTS = 0.216 (CSV 0.218); URU×KSA P(V)_poisson = 0.662 (CSV/análise 0.662), over 2.5 = 0.479 (CSV 0.477). As diferenças (≤0.002) vêm de λ tabelado com 2 casas, não de erro de fórmula. **A tabela de propagação de §3.12 está correta** (E[W_e] para dr0=300/σ=150 → 0.819 calculado = 0.819 do doc; idem nas 12 células, MC 2×10⁶). O documento é implementável e auditável como promete.
- As três correções de coerência da 2ª rodada estão **bem integradas ao contrato**: cap da curva de empate (C1) garante P(D)≥0 no mismatch alto, clamp por leitura (C2), e incerteza de rating como variável de 1ª classe (C3). A `g_rating` (C4) de fato inverte o problema da confiança alta no minnow (URU×KSA 67→57; o registro mostra ESP×CPV ainda em 82 porque é `v2.0-manual`, anterior ao gate — correto).
- A disciplina anti-autoengano permanece madura e é o coração do projeto: snapshot local, registro pré-jogo imutável, portão de backtest para variável nova, IC bootstrap, teste pareado vs mercado, recusa em inventar fontes. **Não mexer.**

**O que NÃO está sólido e precisa mudar (todos novos desta rodada):**

- 🟡 **A propagação da incerteza (C3) está aplicada pela metade.** A v3 integra `W_e` sobre σ_dr (encolhe a vitória — Jensen), mas mantém a curva de empate `P(E|dr)` e o **cap** congelados no ponto `dr0`. Resultado: no regime que a C3 foi feita para tratar (minnow), o empate é **sub-propagado**. Quantifiquei (dr0=572, σ_dr=250): P(E) "correto" = 0.091 vs 0.072 congelado (**+1,9 p.p.**), e o P(D) sai 0.029 em vez de 0.038. Pequeno, mas é incoerência interna dentro da **mesma leitura** Elo-direto (A1).
- 🟡 **A lição da C5 foi aplicada ao GD mas não ao `T_m`.** A v3 libertou a forma de `GD` do "linear por decreto", mas `T_m = (T_base + κ·|dr|/100)·estilo` segue **linear em |dr| por decreto** — exatamente a crítica que a C5 fez ao GD. Em código, GD linear + T_m linear produz **λ_B = −0,27 em dr=900** (negativo!), o que só não aparece por causa do clamp 0.2 que a própria C7 admite violar `T_m`/`GD`. O tail do *total* tem o mesmo risco não-declarado do tail do *saldo* (A2).
- 🟡 **`σ_dr` ignora a incerteza dos ajustes (forma e desfalques) — e a prática já corrige isso à mão.** §3.12 define `σ_R` só a partir de propriedades do *rating* (nº de jogos, diversidade, regime). Mas `R' = R + ΔE_forma + ΔE_desfalques`, e ΔE_desfalques chega a **−57** com escalação **não confirmada** (URU×KSA). A execução então **infla σ_URU para 45 "porque o ajuste é incerto"** — ou seja, contrabandeia incerteza de ajuste para dentro de σ_R sem o contrato pedir. O contrato subdimensiona a incerteza total dos inputs (A3).
- 🟡 **A porta única de desfalque (ΔE simétrico) tem o sinal errado para ausência ofensiva.** Tirar um zagueiro reduz dr → reduz GD → sobe λ_B (adversário marca mais): **correto**. Mas tirar um **atacante** roda a *mesma* fórmula e **também sobe λ_B** — um centroavante lesionado não deveria ajudar o ataque do rival. A v3 entrega o split direcional como "refinamento" (§13) e embarca a versão simétrica como baseline; ela acerta o caso URU (duas ausências defensivas) e erraria o sinal num desfalque de artilheiro (A4).
- 🟡 **A âncora-Elo do gerador AD (§11.2) reintroduz a correlação que o AD deveria quebrar.** A v3 resolveu o fork (C6: AD é primário XOR leitura independente). Mas, para "preservar a espinha dorsal", §11.2 ancora `ATA_T/DEF_T` num prior ∝ R_T (Elo). Se o AD vira a 3ª leitura "genuinamente independente" do ensemble enquanto seu prior **é o Elo**, a independência é parcial — o mesmo defeito de diversidade fictícia que a C4 combate, com outro rótulo (A5).

**Erro de texto (não de conta):** §3.12 diz que a propagação "encolhe extremos **para 1/3**". Em código, com σ→∞ o E[W_e]→**0,5** (não 1/3). `W_e` é expectativa de 2 resultados (neutro = ½); o 1/3 é da V/E/D *a jusante*, depois do split de empate. A tabela está certa; a frase pode fazer um dev encolher para o alvo errado (A6, ⚪).

**Lacuna nº 1 (gratuita, já em uso, ainda fora do contrato):** as execuções citam **mercado de previsão (Kalshi 68% em URU×KSA)**, mas a tabela de fontes da v3 não lista mercados de previsão. A própria v3 declara que "odd de **uma casa** é benchmark fraco" (§3.7) — e Kalshi/Polymarket são justamente o benchmark **multiagente, público e grátis** que resolve essa fraqueza. Está na prática, falta no contrato (§4).

**Veredito de tech lead:** a v3 é a **especificação mais coerente até aqui** e a aritmética está limpa pela 3ª vez — mas continua **não-validada** (zero backtest) e agora carrega **correções pela metade** (A1 propagação, A2 T_m, A4 desfalque) e **lacunas contrato↔prática** (A3 σ dos ajustes, Kalshi). Nenhuma é 🔴 — a coerência [0,1] está garantida. Aprovar para implementação **mantendo** o princípio do próprio doc: rodar o 1º backtest do contrato congelado **antes** de qualquer feature, e fechar os patches baratos A1–A6 junto (são de coerência, não de acurácia). A sofisticação acumulada das três versões aumenta o risco de **falsa confiança**: muita estrutura, nenhuma medida.

---

## 2. Erros e inconsistências encontrados

### A1 🟡 Propagação de incerteza aplicada só ao `W_e`, não ao empate (C3 pela metade)
§9 escreve, na mesma leitura Elo-direto:
```
P(E|dr) := min( P(E_empírico|dr),  2·min(W_e, 1−W_e) − ε )   # avaliado em dr0 (PONTO)
P(V) = E[W_e] − P(E)/2                                       # E[W_e] PROPAGADO (C3)
P(D) = 1 − P(V) − P(E)
```
`E[W_e]` integra sobre `dr ~ N(dr0, σ_dr)`; `P(E)` e o cap **não**. É inconsistente propagar metade da leitura. O efeito é real e localizado no minnow (verificado, MC 2×10⁶):

| σ_dr (dr0=572) | E[W_e] | P(E) congelado → P(D) | P(E) propagado → P(D) | Δ P(E) |
|---:|---:|---:|---:|---:|
| 0 | 0.964 | 0.072 → 0.000 | 0.072 → 0.000 | — |
| 150 | 0.951 | 0.072 → 0.013 | 0.083 → 0.007 | +0.012 |
| 250 | 0.926 | 0.072 → 0.038 | 0.091 → 0.029 | +0.019 |

A coerência [0,1] **não** é violada (encolher `W_e` sem mexer no cap só afrouxa P(D)≥0 — é seguro). O problema é de **honestidade da incerteza**: a C3 encolhe a vitória do favorito mal-medido mas **rota quase tudo para P(D)**, quando parte deveria virar **empate**. Correção barata em §5.1 (propagar a leitura inteira no mesmo MC que já roda).

### A2 🟡 `T_m` continua "linear por decreto" — a C5 só consertou metade
A C5 (acertada) tirou o GD da linearidade imposta e mandou o backtest escolher a forma. Mas o **total** ficou `T_m = T_base + κ·|dr|/100`, linear em |dr|. É a mesma premissa não-declarada que a C5 condenou no GD. Em código (θ=0.45, κ=0.10, T_base=2.6):

| dr | GD_lin | GD_tanh(G_max=4) | T_m (linear) | λ_A | λ_B (cru) |
|---:|---:|---:|---:|---:|---:|
| 300 | 1.35 | 1.30 | 2.90 | 2.12 | 0.77 |
| 600 | 2.70 | 2.35 | 3.20 | 2.95 | 0.25 |
| 900 | 4.05 | 3.07 | 3.50 | 3.77 | **−0.27** |

O λ_B negativo em dr=900 é a C7 em ação (clamp 0.2 "regulariza mas viola T_m/GD", já admitido) — mas a **raiz** é o par GD-linear × T_m-linear extrapolado num tail sem dados. Se a goleada real tem o favorito tirando o pé, o *total* talvez **não** suba linearmente com o mismatch. A C5 deve valer para `T_m` também: deixar o backtest escolher (linear / côncava / saturação suave), com a mesma restrição de extrapolação cautelosa. Correção em §5.2.

### A3 🟡 `σ_dr` não inclui a variância de `ΔE_forma` e `ΔE_desfalques`
§3.12 deriva `σ_R` de nº de jogos efetivos, recência, diversidade de oposição e flags de regime — tudo propriedade do **rating**. Mas a entrada do Poisson é `R' = R + ΔE_forma + ΔE_desfalques`, e esses ajustes:
- são **grandes** (ΔE_desfalques chega a −57 em URU×KSA; cap −120);
- são **incertos** (a escalação real sai ~1h antes; "dúvida" = meio-tier);
- têm tiers **[a calibrar]** "no olho" (a própria §16 admite).

A execução URU×KSA **já compensa isso à mão** ("σ_URU ≈ 45, elevado porque o ajuste de −57 é ele próprio incerto pré-escalação"). Ou seja: a prática injeta incerteza de ajuste dentro de σ_R, mas o **contrato não tem esse termo**. Consequência: `σ_dr = sqrt(σ_A²+σ_B²)` subdimensiona a incerteza real dos inputs, e a banda/`g_rating` que dependem dele saem estreitas demais justamente nos jogos de escalação volátil. Correção em §5.3 (adicionar `σ_ajuste` à composição de σ_dr).

### A4 🟡 Desfalque por porta única (ΔE simétrico) erra o sinal da ausência ofensiva
`λ_A=(T_m+GD)/2`, `λ_B=(T_m−GD)/2`. Um ΔE negativo em A baixa dr → baixa GD → **sobe λ_B**. Para ausência **defensiva** (zagueiro/goleiro) isso é certo (o rival marca mais). Para ausência **ofensiva** é o sinal errado: tirar o artilheiro de A deveria baixar **λ_A** (A marca menos) sem inflar o ataque de B. A v3 trata o split direcional como "refinamento junto do 11.2" e embarca a versão simétrica como baseline (§13). Funciona em URU×KSA (Araújo + Giménez são ambos zagueiros) e erraria num desfalque de centroavante. Não é detalhe: no formato de 48 times, desfalque de craque ofensivo (estrela única de seleção média) é comum. Correção em §5.4 (split direcional já no baseline, não como upgrade).

### A5 🟡 Independência declarada do AD vs. âncora-Elo do AD (contradição latente, herdeira do fork)
A C6 resolveu o fork no papel. Mas §11.2 mantém `ATA_T/DEF_T` com "âncora-Elo (prior ∝ R_T)" para preservar a espinha dorsal. Se, no ramo "AD = leitura independente", `P_ad` entra como o **3º sinal genuíno** do ensemble (pesos ~0.35/0.25/0.20/0.20), mas seu **prior é o próprio Elo**, então P_ad e P_elo compartilham backbone — a "diversidade real" volta a ser parcial, que é exatamente o que a C4 combate. A v3 não reconcilia "independente" com "ancorado no Elo". Decisão de contrato em §5.5: ou o prior do AD é independente do Elo (ex.: prior de gols/xG histórico, não R_T) quando ele for membro do ensemble, ou aceita-se que o ensemble tem ~2 sinais reais e a `consist_int` é rotulada como tal.

### A6 ⚪ "Encolhe extremos para 1/3" (§3.12) — alvo errado para `W_e`
Verificado: σ→∞ ⇒ E[W_e] → **0,5**, não 1/3 (com σ=5000 já dá 0.54 e caindo). `W_e` é binário (neutro ½); o 1/3 é o ponto neutro da V/E/D depois do split de empate. A tabela de §3.12 está correta; só a **frase** confunde. Trocar "para 1/3" por "para ½ (e a V/E/D resultante para ~1/3)". Um dev que implemente "shrink para 1/3" no `W_e` erra a propagação.

### A7 ⚪ Banda de probabilidade por dois métodos que não são garantidamente consistentes
§10 publica a banda como `[P(x|dr0−σ_dr), P(x|dr0+σ_dr)]` (re-rodando o ensemble nas pontas), enquanto o **ponto central** usa `E[W_e]` (média sobre a distribuição). São dois resumos diferentes da **mesma** σ_dr: um pushforward ±1σ (pelo mapa não-linear `W_e`, que dá banda assimétrica) e uma média. Por construção o ponto não é o meio da banda, e nada garante coerência entre os dois cálculos. Como o MC de C3 **já amostra** `W_e` sobre σ_dr, a banda sai de graça como **percentis (16/84)** do mesmo sample — um cálculo, não dois. Correção em §5.1.

### A8 ⚪ Duas probabilidades de empate na mesma arquitetura, não reconciliadas — e a DC vai piorar
`P(E)` existe em dois lugares: (i) diagonal da matriz Poisson (`P_poisson`) e (ii) curva empírica `P(E|dr)` com cap C1 (`P_elo`). São leituras distintas — ok por design. Mas quando a Dixon-Coles entrar (11.2), o termo τ com ρ<0 **sobe 0×0 e 1×1** (ambos empates) → a `P(E)` da matriz **aumenta**, divergindo mais da curva empírica e do cap C1. §3.2 manda "recomputar over 2.5 e BTTS" da matriz corrigida, mas **omite que a V/E/D e a P(E) também mudam** — e que isso reinterage com a restrição C1. Anotar a reconciliação como pré-requisito da entrada da DC.

### A9 ⚪ `σ_dr = √(σ_A²+σ_B²)` assume erros de rating independentes
Num grafo de resultados conexo (sobretudo **intra-confederação**, onde A e B jogaram muito entre si e contra os mesmos adversários), `Cov(R_A, R_B) ≠ 0`. A RSS ignora essa covariância. **Direção e magnitude são incertas** (compartilhar adversários tende a correlacionar positivamente os erros → RSS superestima σ_dr, conservador; jogar muito *um contra o outro* tende a anticorrelacionar → RSS subestima). Para adversários cross-confederação (maioria dos jogos de Copa) a independência é aproximadamente ok; para grupos com vizinhos de confederação, não. Declarar como aproximação; possível mitigação só com a matriz de covariância do ajuste de rating (Camada 2). Não inventar um número agora.

### A10 ⚪ σ_dr usado três vezes (ponto, banda, confiança) → diagnósticos correlacionados, não independentes
A mesma `σ_dr` encolhe o ponto (C3), abre a banda (§10) e derruba a `g_rating` (§14). Se `σ_R` for superestimado, os três se movem juntos e **parecem três confirmações independentes** ("probabilidade humilde + banda larga + confiança baixa") quando são **um** erro propagado três vezes. Parcialmente reconhecido em §16 ("σ_R e σ_ref são, eles próprios, estimados"). Anotar explicitamente que não são sinais independentes.

### A11 ⚪ Repo/refator — itens de higiene (não-bloqueantes)
- **Nome deste arquivo:** o enunciado sugeriu `camada1_revisao.md` (underscore), mas a convenção do repo (README §"Padrão de nomes") é `camadaN-<tipo>[-vX].md` com **hífen**. Segui a convenção → `camada1-revisao-v3.md`. Underscore quebraria o padrão e a ordenação.
- **CSV vs contrato:** `registro-previsoes.csv` ainda **não tem** `sigma_dr`, `banda_pv` nem `hash_inputs` (esquema-alvo v3, §15). Aceitável como tarefa da C2 (e a imutabilidade impede reescrever linhas antigas), mas **enquanto a coluna não existir, a alegação "imutável e auditável" e a validação por banda ficam parciais** — as linhas `v3.0-prelim` guardam banda no texto de `top5/leitura`, não em coluna. Migrar no início da C2.
- **Versão nos cabeçalhos das análises:** os arquivos congelados dizem `v2.0/v2.1-manual` no topo enquanto o modelo é `v3.0`; o README reconcilia ("números idênticos aos da v3"), mas quem abre só a análise não vê isso. Uma linha de tag em cada análise congelada evitaria leitura errada. ⚪.
- **`registro-previsoes.csv` mistura `versao_modelo` distintas** (v0.1 → v3.0-prelim) num só arquivo: correto por imutabilidade, mas a validação **tem** de filtrar por versão (C9) — e os 4 `v3.0-prelim` são previsões antecipadas que **não** podem entrar na validação morning-of. Já está documentado no README; reforçar no código da C2 (não é só convenção, é um filtro obrigatório).

---

## 3. Dados e variáveis adicionais propostos

Critério mantido: **gratuito, local, derivável**; entra como diagnóstico e só vira termo do modelo atrás do portão de backtest (IC que não cruza zero). A v3 já cobre bem xG, fadiga/viagem, altitude, calor, idade, regime/técnico. Foco no que **ainda falta** e ataca uma fragilidade concreta já observada.

### 3.1 `σ_ajuste` — incerteza dos ajustes como termo de σ_dr (resolve A3) — **maior retorno desta rodada**
A v3 promoveu a incerteza do *rating* a 1ª classe mas deixou a incerteza do *ajuste* (forma, desfalques) fora. Propor um termo explícito, derivável de graça do próprio JSON de desfalques e da janela de forma:
```
σ_ajuste(T) = f( Σ |ΔE_i| sobre desfalques em status "dúvida",   # escalação não confirmada
                  nº de "meio-tier",
                  dispersão da forma na janela )
σ_dr = sqrt( σ_R(A)² + σ_R(B)² + σ_ajuste(A)² + σ_ajuste(B)² )
```
Custo zero (usa dados já coletados); fecha o gap contrato↔prática que a URU×KSA expõe. Atrás do portão como tudo, mas é a adição de maior valor/custo.

### 3.2 Fonte dos gols / dependência de bola parada (StatsBomb) — ataca o gap BTTS do minnow
A divergência mais concreta já detectada à mão é **ESP×CPV: BTTS modelo 22% vs mercado ~40%** — "o modelo é severo demais com o ataque do azarão". Seleções fracas marcam **desproporcionalmente em bola parada** (escanteio/falta/pênalti), que independe do equilíbrio de força em jogo aberto. A % de gols de bola parada por seleção é derivável do **StatsBomb Open Data** (eventos com tipo de jogada), grátis e já no escopo. Uso: um **piso de λ do azarão** (ou um ajuste de BTTS) calibrado por propensão de bola parada — em vez de o λ_B baixo do mismatch zerar a chance de gol. Diagnóstico primeiro; termo só com evidência.

### 3.3 Disciplina / cartões vermelhos como diagnóstico de variância
Expulsão muda λ no meio do jogo e o modelo não vê estado de jogo (limitação declarada). A **taxa histórica de vermelhos** por seleção é derivável de graça (StatsBomb; ou contagem nos resultados estendidos). Não vira termo de λ (sem modelo de estado de jogo confiável), mas é um bom **modificador de confiança/variância**: seleção indisciplinada = cauda mais gorda. Baixa prioridade, custo baixo.

### 3.4 Data de nomeação do técnico (sistematizar o flag de regime da C11)
A v3 usa "técnico novo" para alargar σ_R, mas a coleta é "manual via Wikipedia/notícias". Isso é **consultável de forma estruturada** via Wikidata (propriedade de "head coach" com qualificador de data) ou pela infobox da Wikipedia — vira um número (`semanas_no_cargo`) em vez de um flag no olho. Alimenta `σ_R` e `g_rating` de forma reproduzível. Fonte em §4.

### 3.5 Reafirmar o que **não** perseguir (honestidade, igual às rodadas anteriores)
Posse de bola e distância percorrida: sem fonte gratuita estruturada para seleções, preditores fracos. **Understat** tem xG grátis mas só clubes — proxy indireto, baixíssima prioridade. Defasagem circadiana/fuso: efeito pequeno, overfit fácil — candidato, não recomendação. Odds históricas internacionais gratuitas: seguem inexistentes de forma confiável → comparação com mercado continua **prospectiva** em 2026.

---

## 4. Fontes de dados adicionais (tabela)

Mesmos critérios da v3 (§6). Verificadas em 2026-06-15; disponibilidade muda → **snapshot local é a defesa**. Foco no que é **novo** em relação à tabela da v3.

| Fonte | Dado | Grátis? | Key? | Limitações | Confiab. | Papel | Fallback |
|---|---|---|---|---|---|---|---|
| **Kalshi / Polymarket** *(nova — já usada à mão)* | preço-mercado de previsão (prob. implícita) 1X2 / avanço | Sim (leitura pública) | Não p/ ler | Cobertura por jogo varia; liquidez desigual; ToS restringe scraping → **captura manual** com timestamp, como as odds | Média-alta (multiagente) | **benchmark de mercado mais forte que 1 casa** (resolve a fraqueza que a v3 declara em §3.7); entra como `P_mercado` ou 2ª linha de corroboração | odd de 1 casa (plano atual) |
| **Wikidata (SPARQL) — `head coach` + data** *(nova)* | data de nomeação do técnico por seleção | Sim | Não | semiestruturado; nem toda seleção atualizada | Média | sistematiza `semanas_no_cargo` → `σ_R`/`g_rating` (3.4) | infobox Wikipedia; manual |
| **StatsBomb Open Data — tipo de jogada** *(papel novo da fonte já listada)* | % de gols de bola parada / pênalti por seleção; vermelhos | Sim | Não | mesmos limites (sem 2014/Copa América; não-comercial; histórico) | Alta | piso de λ do azarão / BTTS (3.2); variância por disciplina (3.3) | FBref visual; ignorar |
| **ClubElo (clubelo.com)** *(nova, baixa prio.)* | Elo de **clubes** (CSV/endpoint grátis) | Sim | Não | só clubes; útil como **prior de talento** via clube dos convocados, não p/ seleção direta | Média (clubes) | regularizador indireto do minnow (alternativa a valor de mercado, sem ToS de scraping) | tiers manuais; ignorar |
| **openfootball / football.json (GitHub)** *(reafirmar como redundância)* | resultados/calendário em JSON | Sim | Não | cobertura/atualização variam | Média | **redundância de snapshot** do martj42/fixturedownload | martj42 |

**Reconfirmado, não inventar:** odds gratuitas via API seguem sem garantia (`oddspapi.io` ainda **a validar**, não fato; mercados de previsão Kalshi/Polymarket entram por **captura manual**, não API livre); lesões estruturadas para 48 seleções seguem JSON manual + RSS na Camada 3. **APIs pagas (Sportmonks, API-Football, iSports, TheStatsAPI) violam o custo-alvo R$ 0 — fora de escopo.** A FIFA/Coca-Cola World Ranking **não** serve como 2º sinal "independente": desde 2018 é, ela própria, baseada em Elo → correlacionada com o nosso backbone.

---

## 5. Modelos revisados (fórmulas / pseudocódigo)

### 5.1 Propagar a leitura Elo-direto **inteira** + banda por percentis (resolve A1, A7)
Um único MC sobre `dr ~ N(dr0, σ_dr)` resolve os dois:
```
amostrar dr_s ~ Normal(dr0, sigma_dr), s=1..S         # S=10^4, barato; é o MC que C3 já roda
para cada s:
    we_s  = W_e(dr_s)
    pe_s  = min( P_E_empirico(dr_s),  2*min(we_s, 1-we_s) - eps )   # cap por amostra
    pv_s  = we_s - pe_s/2 ;  pd_s = 1 - pv_s - pe_s
P_elo(V) = mean(pv_s) ; P_elo(E) = mean(pe_s) ; P_elo(D) = mean(pd_s)   # leitura inteira propagada
banda(x) = [ percentil_16(p{x}_s), percentil_84(p{x}_s) ]              # banda de graça, mesma amostra
```
Ganho: P(E) deixa de ficar congelado (corrige o +1,9 p.p. medido em A1), e a banda passa a ser **um** cálculo consistente com o ponto (corrige A7), não um pushforward ±σ separado.

### 5.2 Forma de `T_m` escolhida por dados, igual ao GD (resolve A2)
Aplicar a C5 ao total:
```
candidatos T_m(dr):
    T_base + kappa*|dr|/100                         # linear (v3 atual)
    T_base + kappa*(|dr|/100)^q,  0<q<=1            # concava (favorito tira o pe no tail)
    T_base + (T_extra)*tanh(kappa*|dr|/(100*T_extra))   # saturacao suave do total
restricao: monotona; |dr| alem do suporte -> extrapolar com cautela + alargar sigma_dr (5.3)
escolher por Brier/RPS com IC, point-in-time, JUNTO com a forma do GD (sao acopladas em lambda)
```
Migrar a geração de λ para o AD (11.2, `λ=exp(...)>0`) torna o clamp 0.2 desnecessário e dissolve o λ_B<0 de A2 — mas a **forma** do total ainda deve ser estimada, não imposta.

### 5.3 σ_dr com incerteza de ajuste (resolve A3)
```
sigma_ajuste(T) = sqrt(  (a * soma_|dE| de desfalques em DUVIDA)^2     # escalacao nao confirmada
                       + (b * n_meio_tier)^2
                       + (c * desvio_forma_na_janela)^2 )              # a,b,c [a calibrar]
sigma_dr = sqrt( sigma_R(A)^2 + sigma_R(B)^2 + sigma_ajuste(A)^2 + sigma_ajuste(B)^2 )
```
Faz a banda/g_rating refletirem a volatilidade de escalação **pelo contrato**, não por ajuste manual de σ_R como hoje. (Idealmente, somar também a covariância de A9 quando a Camada 2 tiver a matriz de incerteza do rating; até lá, RSS declarada como aproximação.)

### 5.4 Split direcional de desfalque já no baseline (resolve A4)
Não esperar o 11.2: separar a porta única em duas, mantendo o cap:
```
dE_def(T)  -> entra como hoje (via dr) : ausencia defensiva sobe lambda_contra, desce lambda_pro
dE_ata(T)  -> aplica direto em lambda_pro(T) (corta o ataque) SEM inflar lambda_contra do rival
# tier e setor JA estao no JSON: {"tier":1,"setor":"ataque"|"defesa"|"goleiro"}
# regra: setor ataque -> lambda_pro ; setor defesa/goleiro -> lambda_contra (comportamento atual)
```
Custo baixo (o `setor` já existe no schema de §13); corrige o sinal no caso de craque ofensivo.

### 5.5 Tornar o AD genuinamente independente quando for membro do ensemble (resolve A5)
```
SE o AD entra como leitura independente P_ad (fork: baseline GD/T_m gera lambda):
    prior de ATA/DEF NAO pode ser ∝ R_Elo  -> usar prior de gols/xG historico (StatsBomb)
    -> P_ad fica de fato descorrelacionado do backbone Elo -> diversidade real (3 sinais)
SE o AD vira gerador primario de lambda (substitui GD/T_m):
    nao existe P_ad; 3o sinal = mercado; rotular consist_int como consistencia interna (peso menor)
# escolher e registrar no contrato; nao manter "independente E ancorado no Elo" ao mesmo tempo
```

---

## 6. Novos insights habilitados

Tudo grátis e local, sobre os dados atuais + adições de §3.

1. **Empate honesto no minnow (de 5.1):** ao propagar a leitura inteira, jogos de favorito mal-medido passam a mostrar **empate** maior, não só "vitória menos extrema + P(D) residual". Comunica melhor a real chance de tropeço (ex.: CPV segurando 0×0 cedo). É a correção certa para o "índice de zebra" que as análises já calculam à mão.
2. **Flag "ataque do azarão subprecificado" (de 3.2):** formalizar o gap BTTS modelo-vs-mercado (ESP×CPV 22% vs 40%) como alerta automático, ligado à propensão de bola parada do azarão. Vira um insight reproduzível, não uma nota manual.
3. **Corroboração de mercado multiagente (de §4, Kalshi):** substituir/duplicar a odd de 1 casa por preço de mercado de previsão dá uma `corrob_ext` mais honesta e um relatório **modelo-vs-mercado** mais defensável — sempre rotulado "estudo, não aposta".
4. **`semanas_no_cargo` como eixo de incerteza (de 3.4):** reportar, por jogo, quanto da banda larga vem de **regime novo** (técnico recente) vs **amostra rasa** (estreante) vs **escalação volátil** (σ_ajuste). Decompõe a incerteza em causas — útil e barato.
5. **Mantidos da v3 (reafirmar — maior valor percebido):** Monte Carlo do torneio + **cenários de classificação determinísticos** (transformam o risco de incentivo de última rodada em saída transparente), sensibilidade por previsão (já demonstrada nas execuções) e regressão à média por xG (StatsBomb 2018+2022).

---

## 7. Riscos e limitações

**O maior risco é o mesmo das duas rodadas anteriores e não mudou: nada foi backtestado.** θ, κ, T_base, tiers, pesos, `σ_R`, `σ_ref`, a curva `P(E|dr)` e agora `σ_ajuste`/`a,b,c` são todos **[a calibrar]**. As 8 execuções usam Elo de **fonte única** (eloratings.net), sem o Elo próprio do martj42 com `H_hist`. A cada versão a estrutura cresce (incerteza de rating, gates, bandas) e com ela o risco de **falsa sensação de "melhorou"** sem uma única medida empírica. **A v3 é a especificação mais coerente; não é um sistema melhor até o backtest dizer que é** — e a sofisticação acumulada torna esse aviso mais urgente, não menos.

**Riscos específicos desta rodada:**
- **Correções pela metade dão falsa garantia:** propagar `W_e` mas não `P(E)` (A1), libertar `GD` mas não `T_m` (A2), e o `σ_R` que silenciosamente absorve incerteza de ajuste (A3) fazem o sistema **parecer** mais honesto do que o contrato garante. Os patches são baratos — o risco é deixá-los abertos e confiar na banda/g_rating como se estivessem completos.
- **`σ_ajuste`, `σ_R` e `σ_ref` são estimativas de estimativas:** A propagação (e a banda, e a confiança) só ajuda se a incerteza estiver razoavelmente calibrada. E os três usam a mesma σ_dr (A10) — um erro de calibração se manifesta como três "confirmações" correlacionadas. Calibrar σ contra a **variância empírica dos erros de previsão por faixa** no backtest, ou a humildade vira teatro.
- **AD ancorado no Elo (A5)** pode anular a única fonte de diversidade nova do ensemble; decidir antes de pesar.
- **Mercado de previsão não é onisciente:** Kalshi/Polymarket são melhores que 1 casa, mas têm liquidez desigual e podem ecoar o mesmo Elo público; peso ≤0.20 e rótulo "estudo" continuam valendo.
- **StatsBomb:** cobertura 2018+2022 (sem 2014/Copa América), licença não-comercial, histórico — ativo de backtest, não feed ao vivo das 48 seleções. O piso-de-bola-parada (3.2) depende dele e herda esses limites.
- **σ_dr via RSS (A9)** ignora covariância de rating intra-confederação; magnitude e sinal **incertos** — declarado, não corrigível sem a matriz de covariância da Camada 2.

**Incerto mesmo após estas correções (declarado):** `H_host2026`, tiers de desfalque, `σ_ref`, efeito de altitude/calor, México "quase-casa", incentivos de fim de grupo (a v3 os torna **transparentes** via cenários, não os elimina), e a forma funcional de GD/T_m no tail |dr|>500, onde há pouquíssimos dados e os ratings de minnow são mais ruidosos. **Apostas:** Brier ~0.60 não é edge — não é ferramenta de lucro, e isso fica na interface.

---

## 8. Próximos passos recomendados (a ordem importa)

1. **Antes de qualquer feature: 1º backtest do contrato v3 congelado** — Elo com `H_hist` + `σ_R` → GD/T_m → Poisson 0..10, point-in-time, IC bootstrap, teste pareado vs Elo público. É o princípio do próprio doc; sem isto o resto é decoração. *Desbloqueia tudo.*
2. **Patches de coerência baratos (fechar as correções pela metade), junto do backtest:**
   - propagar a **leitura Elo-direto inteira** + banda por percentis do mesmo MC (§5.1 → A1, A7);
   - corrigir a frase "para 1/3" → "para ½" (§3.12 → A6);
   - **split direcional de desfalque no baseline** (§5.4 → A4, usa o `setor` que já existe no JSON);
   - **`σ_ajuste`** somado a σ_dr (§5.3 → A3), tirando o ajuste manual de σ_R das execuções;
   - anotar a reconciliação de `P(E)` matriz-vs-curva como pré-requisito da DC (A8) e a RSS como aproximação (A9).
3. **Decidir a forma de GD *e* de T_m por Brier/RPS com IC** (§5.2 → A2) — as duas são acopladas em λ; não libertar uma e impor a outra.
4. **Resolver o AD no contrato** (§5.5 → A5): prior independente do Elo se for membro do ensemble, ou rótulo honesto de 2 sinais.
5. **Adicionar Kalshi/Polymarket e Wikidata (técnico) à tabela de fontes e ao schema do registro** (§4) — captura manual com timestamp; sistematiza o flag de regime (3.4).
6. **Migração do CSV no início da C2:** colunas `sigma_dr`, `banda_pv`, `hash_inputs`; filtro obrigatório por `versao_modelo` (excluir `*-prelim` da validação morning-of). (A11)
7. **StatsBomb para xG + % bola parada** (3.2) → piso de λ do azarão atrás do portão; ataca o gap BTTS já observado.
8. **Só então** pesos finos do ensemble (≥30 jogos), `P_ad` conforme o fork, e contexto físico/regime promovido a λ só com IC que não cruza zero.

**Milestone de aceite (mantém o da v3 + 3 invariantes novos):** backtest com Elo corrigido por mando e σ_R, pipeline congelado e point-in-time, **Brier < uniforme com IC que não cruze o baseline** e ≈ Elo público; **P(V),P(D) ∈ [0,1] em todo |dr|**; **confiança não-crescente com σ_dr**; **e agora:** (i) a leitura Elo-direto propagada inteira (P(E) não congelado); (ii) forma de GD **e** T_m escolhida por dados, não imposta; (iii) σ_dr inclui a incerteza de ajuste quando a escalação não está confirmada. Sem isso, o resto é decoração.

---
*Auditoria de 3ª rodada — sem código de implementação, por escopo. A v3 fechou bem a coerência [0,1] e introduziu incerteza de rating; esta rodada trata o que ela deixou **pela metade** (propagação só do W_e, T_m ainda linear, desfalque simétrico, σ sem o termo de ajuste) e o que está na **prática mas fora do contrato** (Kalshi, σ de escalação). Aritmética reconferida em código pela 3ª vez — está limpa; os problemas são de modelagem e de contrato↔prática, não de conta. Fontes verificadas em 2026-06-15; snapshot local é a defesa. Probabilidades, nunca certezas — inclusive sobre o próprio modelo, não-validado até o primeiro backtest.*
