---
tags: [camada1, auditoria, atual]
status: atual
tipo: auditoria
data: 2026-06-15
aliases: ["Auditoria v5"]
---

# Camada 1 — Revisão / Auditoria do contrato v5 (4ª rodada)
**Projeto:** Sistema de previsão de partidas — Copa do Mundo 2026
**Contrato sob auditoria:** [[camada1-planejamento-v5]] (v5.0, 2026-06-15)
**Data:** 2026-06-15 · **Status:** auditoria (sem código de sistema) · **Custo-alvo:** R$ 0
**Convenção de nome:** sufixo = versão auditada (como [[camada1-revisao-v3]] auditou a v3). Esta é a **4ª rodada** de auditoria; a v5 veio de [[camada1-lacunas]] (pesquisa), não de uma revisão, por isso não há `-v4`.

> Convenções herdadas (V/E/D, λ, dr, σ_R, σ_ajuste, σ_dr, T_m, GD, W_e, **[a calibrar]**). Esta auditoria **não altera nenhuma fórmula** — ela (a) **verifica em código** os números do contrato v5 e da execução v5.0, (b) lista achados separando **erro** de **lacuna de especificação** de **risco de calibração**, e (c) registra uma **autocorreção** de um achado preliminar. Todos os números abaixo foram reproduzidos em Python (sementes/contas no §1). Princípio mantido: probabilidades, nunca certezas; nada entra em λ/dr sem o portão de backtest.

---

## 0. Resumo executivo

**A aritmética da v5 está limpa.** Reproduzi de forma independente, em código, todas as tabelas e a única execução em v5.0 (IRN×NZL): altitude (`GD_alt`), piso de bola parada (ESP×CPV), Poisson (V/E/D, over 2.5, BTTS, top-5 placares), aritmética do ensemble e o RSS de `σ_dr`. **Tudo bate até o arredondamento** (4ª verificação independente do projeto, agora cobrindo os termos novos da v5). A coerência [0,1] se sustenta sob a curva de empate restrita; a propagação encolhe o favorito na direção certa (Jensen), e a banda 16/84 é internamente plausível.

**Não há nenhum erro de conta.** Os achados são de duas naturezas:
- **Lacunas de especificação / consistência de relato** — sobretudo: a v5.md **não é autocontida** (delega a v4 as formas de λ e da curva de empate, enquanto se declara "contrato congelado / fonte da verdade"); e os mercados derivados (over/BTTS/placares) são **só-Poisson**, não consistentes com o V/E/D do ensemble.
- **Armadilhas de calibração já declaradas pela v5** — reforçadas aqui com **magnitude** (dupla contagem altitude×mando; piso de bola parada inflando o total; σ_dr único acoplando ponto/banda/confiança).

**Autocorreção (§3):** um achado preliminar afirmou que `f(dr)`, `g(dr)` e a curva C1 "não estão pinadas no contrato". Após ler a v4, isso está **errado/forte demais**: as **famílias** estão especificadas na v4 (§8, §9, §11.1); o que falta é a v5 **restabelecê-las no próprio escopo** e congelar a tabela empírica + coeficientes (que são, corretamente, [a calibrar]). Patch: o apêndice [[camada1-apendice-formas-v5]] consolida as formas no escopo da v5, **sem mudar fórmula**.

**Conclusão de aceite:** a v5 é mais **coerente e fundamentada em evidência** que a v4 — **não** mais **acurada** até o backtest. E, como adiciona variáveis (θ_alt, κ_heat, piso_setpiece, banda_mando, d/e de σ_ajuste), o portão de IC-que-não-cruza-zero fica **mais** crítico, não menos.

---

## 1. Verificação numérica em código (o que foi reproduzido)

Reprodução independente em Python (Poisson 0..10 com resíduo na borda; MC com S=2×10⁵). **PASS** = bate com o doc/execução até o arredondamento publicado.

| # | Item verificado | Fonte | Resultado |
|---|---|---|---|
| V1 | Tabela de altitude `GD_alt = θ_alt·(pen_B−pen_A)/1000`, 4 casos | v5 §3.13 | **PASS** (0.00 / 0.00 / +1.12 / −0.78); sinal correto |
| V2 | Piso de bola parada ESP×CPV (λ_A=2.84; λ_B∈{.26,.40,.50,.60}) | v5 §3.13 | **PASS** (P(V), P(E), P(D), over, BTTS; BTTS 0.216→0.425) |
| V3 | Execução IRN×NZL Poisson (λ_A=1.40, λ_B=0.78) | análise v5.0 | **PASS** (P 51.7/27.5/20.9, over 37.2%, BTTS 40.8%, top-5 placares) |
| V4 | Ensemble .45/.35/.20 (IRN×NZL) | análise v5.0 | **PASS** (54.2/25.3/20.6, soma 100.0) |
| V5 | `σ_dr = √(90²+80²+20²+20²)` | análise v5.0 | **PASS** (123.7 ≈ 124) |
| V6 | Propagação MC: encolhe favorito 0.597→~0.58; banda 16/84 ≈ [0.37,0.77] | v5 §3.12 / análise | **PASS qualitativo** (direção por Jensen; magnitude ≈ doc 0.581 e 0.42–0.74) |
| V7 | Coerência [0,1] em dr∈[−800,800] com C1 restrita | v5 §3.12 (herda v3) | **PASS** (min P observada ≈ 0.006 ≥ 0) |
| V8 | Placeholders lineares θ=0.45, T_base=2.6, κ=0.10 reproduzem a tabela v4 §8 e a execução | v4 §8/§11.1 | **PASS**; confirma λ_B<0 no tail (dr≥900) — motiva forma saturante |

**Nota de método (V6):** a curva de empate exata (C1) não está na v5.md; usei como *proxy* `P(E)=2k·min(W_e,1−W_e)` com k≈0.371, que reproduz a leitura pré-propagação a 3 casas. **Esse proxy NÃO é a forma do contrato** — a forma real (empírica + cap por amostra) está na v4 §9/§3.12 e foi consolidada no apêndice. O proxy serviu só para confirmar **direção e magnitude** da propagação, que conferem.

---

## 2. Achados

| ID | Achado | Natureza | Severidade | Já na v5? |
|---|---|---|---|---|
| A1 | Mercados derivados (over/BTTS/placares) são só-Poisson; não batem com o P(E) do ensemble | consistência de relato | 🟡 | Não |
| A2 | Banda do ensemble **sub-cobre** por construção (perna de mercado com variância propagada zero) | desenho de aceite | 🟡 | Parcial (estreitamento citado; risco de sub-cobertura não) |
| A3 | Piso de bola parada **infla o total**, não redistribui — interage com o calor (sinais opostos) | modelagem | ⚪ | Não |
| B1 | v5.md **não é autocontida**: delega f(dr)/g(dr)/C1 à v4 sendo "fonte da verdade" | especificação | 🟡 | Implícito ("por backtest") |
| B2 | Dupla contagem altitude×mando é **grande** (México em CDMX: GD_alt +1.12 *e* mando +40) | calibração | 🟡 (declarado) | Sim — reforço de magnitude |
| B3 | Penalidade de altitude assimétrica (`max(0,·)`) é premissa **além de McSharry** | premissa | ⚪ (declarado) | Sim — torno explícito |
| B4 | σ_dr único acopla ponto + banda + confiança (ponto único de falha) | calibração | ⚪ (declarado) | Sim — reforço |

### Achados novos (a v5 não flagra)

**A1 — Mercados derivados são só-Poisson; incoerentes com o V/E/D do ensemble.** 🟡
A manchete da execução reporta `P(E)` **ensemble = 25.3%**, mas a tabela de placares vem da matriz Poisson, cuja **diagonal soma 27.5%**. Ou seja, "P(E)=25.3%" e placares que (na diagonal) somam 27.5% coexistem lado a lado. Idem para over 2.5 e BTTS: são derivados de λ (Poisson), não do ponto do ensemble. **Não existe matriz de placares do ensemble** — Elo-direto e mercado não geram placares. *Recomendação:* declarar no contrato (e na saída) que **over/BTTS/placares são condicionais à leitura Poisson (λ)**, não ao V/E/D do ensemble — e nunca somar a diagonal Poisson esperando o P(E) do ensemble. Custo zero; é rótulo, não fórmula.

**A2 — A banda do ensemble sub-cobre por construção.** 🟡
A banda é a leitura propagada (percentis 16/84 sobre `dr~N(dr,σ_dr)`). A perna de mercado (peso 0.20) **não se move com dr** (a v5 diz isso, e usa para justificar que a banda do ensemble é mais estreita que a do Elo-direto). O ponto não-óbvio: 20% do peso entra com **variância propagada zero**, então a banda do ensemble **subestima** a incerteza total — pior ainda porque o mercado tem incerteza real (odds se movem, de-vig é aproximado). **Consequência para o backtest:** o invariante "banda com cobertura nominal" provavelmente **falha na banda do ensemble** e deve ser medido na leitura cuja banda se quer calibrar (**Elo-direto propagada**), não na do ensemble. Caça a um falso "fail" de cobertura no aceite da Camada 2.

**A3 — O piso de bola parada infla o total, não redistribui.** ⚪
`λ_azarão = max(λ, piso_setpiece)` sobe λ_B **sem baixar λ_A** → o total cresce (ESP×CPV: 3.10→3.34; over 0.599→0.648, verificado). Como o calor (E3) **reduz** o total, os dois termos novos da v5 empurram o total do azarão em **direções opostas**. É defensável (azarão de bola parada de fato eleva o total), mas é um **termo aditivo ao total**, não uma transferência de massa — então deve ser calibrado **junto** com κ_heat e com a forma de T_m, senão um cancela o outro sem evidência. Alternativa principiada a considerar no C2.5: capturar a dependência via **Dixon-Coles (τ)** em vez de (ou além de) pisar λ_B — o problema-raiz do BTTS-do-azarão é de **correlação/cauda baixa**, território da DC; o piso e a DC podem **dupla-corrigir** se entrarem sem calibração conjunta.

### Achados declarados pela v5 — reforço

**B1 — v5.md não é autocontida (corrigido em §3).** 🟡
O critério de pronto da v4 era "qualquer dev implementa a Camada 4 lendo só este documento". A v5 quebra isso para os blocos centrais de λ e empate: diz "f por backtest", "g por backtest", "curva de empate restrita (C1) propagada", **sem restabelecer as formas** — que existem na v4 (§8, §9, §11.1). Um leitor só da v5.md não as tem. *Patch aplicado:* [[camada1-apendice-formas-v5]] consolida f/g/C1 no escopo da v5 (sem mudar fórmula). Residual legítimo: os **coeficientes** (θ, κ, T_base) e a **tabela empírica de P(E|dr)** seguem [a calibrar] — isso é correto, não é lacuna.

**B2 — Dupla contagem altitude×mando é grande.** 🟡 (declarado em v5 §16/§4)
México em CDMX vs seleção de planície: `GD_alt = +1.12 gol` **e** `H_host2026 = +40 Elo`. +1.12 de saldo é enorme — desloca λ ~0.56 de cada lado **antes** de qualquer mando. A v5 manda calibrar os dois juntos; só sublinho que esta é **a maior armadilha de calibração da v5**, não um detalhe de tail, e que o sinal físico se sobrepõe (altitude É parte de por que o anfitrião de altitude vence). No backtest, **identificar separadamente** (jogos do México na altitude isolam o cruzamento) ou aceitar que θ_alt e H_host2026 ficam parcialmente confundidos.

**B3 — Penalidade de altitude assimétrica é premissa além da fonte.** ⚪ (declarado)
`pen(T)=max(0, alt_sede − alt_casa_T)` assume que **só subir machuca** e que seleção de altitude ao nível do mar tem vantagem **zero**. McSharry mede o **diferencial** (1460 jogos CONMEBOL); a assimetria é escolha de modelagem conservadora, não resultado do paper. Registrar como premissa explícita e alargar σ fora da CONMEBOL (a v5 já pede cautela na extrapolação).

**B4 — σ_dr único é ponto único de falha.** ⚪ (declarado em v5 §14)
Ponto, banda e `g_rating` usam a **mesma** σ_dr — a v5 declara que não são três sinais independentes. Reforço operacional: o backtest precisa de um **teste de calibração de σ_dr isolado** (cobertura da banda + variância empírica dos erros por faixa), não só Brier do ponto. Se σ_dr está mal calibrado, "probabilidade humilde + banda larga + confiança baixa" são **um** erro disfarçado de três confirmações.

---

## 3. Autocorreção (honestidade de auditoria)

O achado preliminar B1 dizia: *"f(dr), g(dr) e a curva de empate C1 não estão pinadas no contrato congelado."* Após ler [[camada1-planejamento-v4]], isso é **forte demais e parcialmente incorreto**:

- **f(dr):** a v4 §8 dá a família ({linear `θ·dr/100`} ou {tanh-saturante}) e a tabela com `θ_lin=0.45` (GD=1.35 em dr=300). **Especificada.**
- **g(dr):** a v4 §8/§11.1 dá a família ({linear `T_base+κ·|dr|/100`} ou côncava ou saturação suave), `T_base≈2.6` (Copas 2018/2022), `κ_lin=0.10`. **Especificada.**
- **C1 (empate):** a v4 §9/§3.12 dá a construção completa — curva empírica `P_E(dr)` do martj42 por faixas de |dr| (~0.26 em |dr|<50 → ~0.15 em |dr|>300), **truncada por amostra** por `pe_s = min(P_E(dr_s), 2·min(we_s,1−we_s) − ε)`, com `pv_s = we_s − pe_s/2`, `pd_s = 1 − pv_s − pe_s`. **Especificada** (e é o que garante a coerência [0,1]).

O erro real não é "não pinado", e sim **"não restabelecido na v5.md, que se declara fonte da verdade"** (B1 reclassificado como lacuna de **autocontenção**, não de existência). Deixo registrado porque o projeto preza separar "o que verifiquei" de "o que assumi" — e eu assumi antes de verificar.

---

## 4. Recomendações (o que vira o quê)

**Aplicar agora (sem bump de versão — não mudam fórmula):**
1. **Apêndice de formas** ([[camada1-apendice-formas-v5]]) — consolida f/g/C1 no escopo da v5. *Feito.*
2. **Rótulo de relato (A1):** declarar que over/BTTS/placares são leitura **Poisson-condicional**, não ensemble. Uma frase no contrato + na saída das análises.

**Levar ao desenho do backtest (Camada 2), não decidir agora:**
3. **A2 — medir cobertura da banda na leitura Elo-direto**, não na do ensemble (evita falso fail).
4. **B2 — identificar θ_alt e H_host2026 separadamente** (jogos do México na altitude); aceitar confusão residual se a amostra não separar.
5. **A3 — calibrar piso_setpiece junto com κ_heat e a forma de T_m**; avaliar se a Dixon-Coles (τ) torna o piso redundante para o BTTS-do-azarão.
6. **B4 — incluir um teste de calibração de σ_dr isolado** nos invariantes de aceite.

**Só o backtest decide (portão de IC):** θ_alt fora da CONMEBOL, κ_heat, piso_setpiece, banda_mando, d/e de σ_ajuste, e a escolha das formas de GD/T_m (linear vs saturante — a linear dá λ_B<0 em dr≥900, V8).

**Candidato a v6 (se e quando):** nenhuma fórmula precisa mudar hoje. Um v6 só se justifica se o backtest **rejeitar** uma forma (ex.: exigir saturação no tail) ou **remover** um termo ambiental por IC que cruza zero — aí sim, nova `versao_modelo` + atualização do README.

---

## 5. Invariantes de aceite (reforçados por esta auditoria)

O backtest da Camada 2 (congelado, point-in-time, IC bootstrap B=10⁴) deve mostrar, e agora com os reforços acima:
- **Brier < uniforme** (IC que não cruza o baseline) e **≈ Elo público**.
- **P(V), P(D) ∈ [0,1]** em todo |dr| (V7 confirma a construção; medir no fit real).
- **Confiança não-crescente com σ_dr** (monotonicidade de `g_rating`).
- **Banda com cobertura nominal — medida na leitura Elo-direto** (A2), não na do ensemble.
- **Calibração de σ_dr isolada** (B4): variância empírica dos erros por faixa bate com σ_R/σ_ajuste.
- **Cada termo ambiental novo** (altitude, calor, piso, banda de mando) **só sobrevive se melhorar Brier/RPS com IC que não cruza zero**; altitude e mando **calibrados juntos** (B2); piso e calor **juntos** (A3).

---
*Auditoria da v5.0 — 4ª rodada, sem código de sistema. Não altera nenhuma fórmula; verifica os números em código (todos PASS), registra achados (3 novos, 4 reforçados/declarados) e uma autocorreção. Acompanha o apêndice [[camada1-apendice-formas-v5]]. Verificado em 2026-06-15. Probabilidades, nunca certezas — e a coerência confirmada não é acurácia até o backtest.*
