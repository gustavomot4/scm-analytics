---
tags: [dev, audit, ux, web]
status: atual
tipo: auditoria
data: 2026-06-21
aliases: ["Auditoria UX web", "UX web 2026-06-21"]
---

# Auditoria de UX / Web — interface (2026-06-21)

Análise rigorosa do que dá para aprimorar na **interface** (`scm/web.py` + `templates/`), focada na
experiência do **usuário final**. **Método (honesto):** li todo o HTML/CSS/JS das 4 telas
(`index`, `simulacao`, `bracket`, `prospectivo`) + o pop-up; **não** rodei o Flask ao vivo (sem o
pacote/rede no ambiente da auditoria), nem Lighthouse/leitor de tela — então os achados são do
**código**, não de medição em runtime. Cada um cita `arquivo:linha`.

## Veredito em 1 parágrafo
A interface é **boa para o porte**: layout limpo, responsiva (media queries), autocomplete por
`datalist`, estados de carregamento nos botões, `aria-live`/`role=alert` no resultado, e a tela
**Prospectivo** tem um fluxo 1-2-3 exemplar. Os problemas são **(a) um erro factual de texto**,
**(b) performance percebida** numa tela que roda Monte Carlo no load, **(c) dívida de template**
(CSS/sidebar duplicados nas 4 telas, sem base), e **(d) atrito de idioma** (UI em PT, nomes de time
em inglês). Nada estrutural quebrado; são melhorias de acabamento e de processo de front.

## Achados priorizados (impacto ÷ esforço)

### 🔴 P1 — Texto ERRADO confunde o usuário (trivial de corrigir)
`simulacao.html:66` diz *"Chaveamento por **sorteio aleatório** (não modela a tabela posicional…)"*.
**Está stale/errado:** o simulador usa o **chaveamento OFICIAL da FIFA** (R32 fixos, 3ºs pelo Anexo C)
— como a própria `bracket.html:82` afirma corretamente, e como está em `simulate.py` (R32/LATER).
A tela diz ao usuário o oposto do que o sistema faz. **Corrigir o texto.** Esforço: trivial.

### 🟠 P2 — Atrito de idioma: nomes de time em inglês, UI em PT
`index.html:140` (`placeholder "ex.: Brazil"`) e o `datalist` usam os nomes do martj42 em **inglês**.
Um usuário BR digita "Brasil"/"Alemanha" → erro (mitigado por sugestões via `difflib`, mas é atrito).
**Impacto alto** para o público-alvo. **Fix:** mapa de apelidos PT→EN no autocomplete e/ou aceitar
PT em `predict_match._team` (normalizar + alias). Esforço: baixo-médio.

### 🟠 P3 — `bracket` roda 5.000 sims NO CARREGAMENTO (perf percebida)
`bracket.html:139` chama `load()` no load → `GET /api/bracket` → `most_likely_bracket` **+** `run(5000)`
(`web.py:121-141`). São **5.000 torneios Monte Carlo a cada visita**, agora **mais pesados** (o blend
AD chama `attack_defense.fit` a cada `build_ad_lambdas`), **síncrono**, com só um "Calculando…".
`simulacao` tem o mesmo custo no clique. **Fix:** (1) **cachear** o último resultado no servidor (o
sorteio quase não muda); (2) default menor (ex.: 2.000) e deixar 20.000 como opção; (3) **barra de
progresso** real (igual ao pop-up de update — o MC pode publicar i/n). Esforço: médio.

### 🟡 P4 — Acessibilidade (correções rápidas)
- Inputs de **odds** sem `<label>` (só placeholder): `index.html:166-168`. Add `<label>`/`aria-label`.
- **Abas** do bracket sem semântica: `bracket.html:85-86` usam `onclick` inline e não têm
  `role="tab"`/`aria-selected`/teclado. Add ARIA + foco.
- `sims` é `type="text"` (`simulacao.html:58`, `bracket.html:88`) — deveria ser `type="number"`
  (min/max) ou `inputmode="numeric"`; hoje aceita lixo.
- Barra de probabilidade (`index.html:181`) é só cor; a **legenda** dá o texto (ok), mas um
  `aria-label` no `.bar` ajudaria leitor de tela. Esforço: baixo.

### 🟡 P5 — Fluxo do usuário (valor, baixo esforço)
- **Sem "registrar esta previsão"** na tela Prever: a API `/api/registrar/register` existe e a
  Prospectivo usa, mas o lugar natural (após prever um jogo) não oferece. Surfacing de 1 botão.
- **Sem rolar para o resultado** no mobile após "Prever" (`index.html` render): o resultado nasce
  abaixo da dobra. Add `scrollIntoView`.
- **Sem botão trocar mandante↔visitante** (swap) — comum em previsores.
- **Venue incompleto** (`index.html:148-155`): falta **Guadalajara** (sede REAL de 2026, 1566 m, que
  o modelo suporta) e cidade/mando **custom**. Esforço: baixo.

### 🟠 P6 — Dívida de template (raiz de divergências futuras)
As 4 telas **duplicam** head + sidebar + ~40 linhas de CSS idênticas (`.app/.sidebar/.sb-nav/…`):
`index.html:91-104`, `simulacao.html:24-37`, `bracket.html:13-25,61`, `prospectivo.html:13-22,37`.
Não há **base template**. Consequências: manutenção em 4 lugares, **risco de divergência** (já há
pequenas: `simulacao` tem menos `:root` vars; larguras de `main` diferentes), e **CSS morto**
(`.sb-update`/`.sb-updmsg` em todas — sobra do botão antigo, hoje substituído pelo pop-up).
**Fix:** `templates/_layout.html` com `{% extends %}` + `{% block %}` (ou `static/app.css` único) e
remover o CSS morto. Esforço: médio; paga em consistência e peso.

### ⚪ P7 — Acabamento (polish)
- **Separador decimal:** percentuais com ponto ("51.7%"), mas PT-BR e o resto do projeto usam
  **vírgula** ("0,562"). Inconsistência de locale.
- **Pop-up no mobile:** `position:fixed` canto inferior direito pode **sobrepor** conteúdo/scroll em
  telas estreitas; considerar minimizar por padrão em viewport pequena.
- **Sem favicon** (aba genérica). **Sem dark mode** (as `--vars` existem; faltam `prefers-color-scheme`).

## O que JÁ está bom (não mexer)
Responsividade real (3 breakpoints); `datalist` p/ 336 seleções; `aria-live=polite` no resultado e
`role=alert` no erro; estados "Calculando…/Simulando…" nos botões; o **explicador do `dr`** (chips
Elo/forma/mando/desfalque) em `index.html:281-290` é didático; a tela **Prospectivo** (fluxo 1-2-3,
empty states, registro avulso) é o melhor exemplo de UX do app; o **pop-up de atualização** novo já
resolve o problema de persistência entre telas.

## Sugestão de ordem
1. P1 (texto) + P4 (a11y) + P5 (scroll/registrar/Guadalajara) — rápidos, alto retorno percebido.
2. P2 (nomes PT) — tira o maior atrito do usuário BR.
3. P3 (perf do bracket: cache + progresso) — tela mais lenta.
4. P6 (base template + CSS único) — saúde do front; destrava os demais sem duplicar.
5. P7 (polish) — quando sobrar.

---

## ✅ Implementado — Lote 1 (2026-06-21)
- **P1** corrigido: `simulacao.html` agora diz "chaveamento OFICIAL da FIFA (Anexo C)" (era "sorteio aleatório").
- **P2**: `predict_match._team` aceita **nomes em PT** (mapa de apelidos PT→EN normalizado: Brasil→Brazil, México→Mexico, EUA→United States, Coreia do Sul→South Korea, Países Baixos→Netherlands… — verificado). Vale p/ a tela Prever, a porta da frente e o registro.
- **P4** (a11y): `aria-label` nos 3 inputs de odds; `sims` virou `type="number"` (min/max) em simulacao e bracket; abas do bracket com `role="tab"`/`aria-selected`; `aria-label` na barra de probabilidade.
- **P5** (fluxo): **Guadalajara** no dropdown de sede (+venueMap); botão **⇄ trocar lados**; **scroll até o resultado** após prever (mobile); link **"Registrar no painel Prospectivo →"** no resultado, com **handoff** (`?home&away` pré-preenche e abre o registro avulso no Prospectivo).
- Verificado: 32/32 módulos compilam; as 4 telas renderizam (Jinja); alias PT testado como função pura.

**Pendente (lotes seguintes):** P3 (bracket roda 5.000 sims no load → cache + progresso), P6 (base template + CSS único, remover CSS morto), P7 (polish: vírgula decimal, favicon, dark mode, pop-up no mobile).

---

## ✅ Implementado — Lote 2 (2026-06-21)
- **P3 — performance do Chaveamento/Simulação:**
  - **Cache no servidor** (`web.py`: `_SIM_CACHE` por `tipo|sims|impressão-digital(n_jogos|max_data|versão)`):
    o sorteio+Elo só mudam após "Atualizar", então visitas/abas seguintes são **instantâneas**.
  - **Job em background com % real** (`_run_sim_job` + `simulate.run(progress=...)`): a 1ª vez roda em
    thread publicando o progresso; o front faz **poll** e mostra **barra de %** (igual ao "Atualizar").
  - **Default mais leve**: 5.000 → **2.000** sims (input e API). A barra fica em `bracket`/`simulacao`.
- **P6 — saúde do front:**
  - **Sidebar única** em `templates/_sidebar.html` (`{% set active %}` + `{% include %}`) — antes a nav
    era copiada (e divergia) nas 4 telas. Render verificado: nav e link ativo corretos nas 4.
  - **CSS morto removido** (`.sb-update`/`.sb-updmsg`, 3 linhas × 4 telas) — sobra do botão antigo.
- Verificado: 32/32 módulos compilam; as 4 telas renderizam (Jinja) com sidebar/partial + pop-up.
  **Ressalva:** o poll/% do job e o cache não foram testados no Flask ao vivo (sem o pacote no
  ambiente da auditoria) — backend revisado/compila; **teste no navegador na sua máquina**.

**Pendente:** P7 (vírgula decimal, favicon, dark mode, pop-up no mobile) e o dedup do bloco de CSS
comum (a sidebar já saiu; o resto do CSS ainda é por-página — baixo risco deixar assim).

---

## ✅ Implementado — Lote 3 / P7 (2026-06-21)
- **Favicon** (data-URI SVG, "S" azul) nas 4 telas — aba do navegador deixa de ser genérica.
- **Dark mode** `@media (prefers-color-scheme: dark)` nas 4 telas + no pop-up: **aditivo** (só ativa
  no modo escuro do SO; **não afeta o claro**). Sobrescreve as `--vars` e as superfícies que eram
  brancas fixas (cards, inputs, sidebar, popup).
- **Pop-up no mobile** (`_update_widget.html`): largura responsiva `calc(100vw − 20px)` e
  reposicionamento em telas ≤560px (não estoura a viewport).
- Verificado: as 4 telas renderizam com favicon + bloco dark + popup responsivo.

### Deixado de fora DE PROPÓSITO — separador decimal (vírgula)
Converter "51.7%" → "51,7%" globalmente é **arriscado e de baixo valor**: o mesmo `toFixed()`
alimenta **larguras CSS** (`width:${x*100}%` — vírgula quebraria o CSS) e uma troca por regex
corromperia refs como "**§3.8**"/"v0.4". Fazer certo exige um helper por ponto de exibição (~30
locais, sem tocar os de estilo). Fica como melhoria opcional; o `.` é aceitável e consistente hoje.
**Status da auditoria UX: P1–P7 concluídos (menos a vírgula decimal, deferida com justificativa).**
