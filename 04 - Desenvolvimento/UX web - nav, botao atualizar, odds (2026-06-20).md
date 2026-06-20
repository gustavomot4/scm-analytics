---
tags: [dev, web, ux, decisoes]
status: atual
tipo: decisoes
data: 2026-06-20
aliases: ["UX web 2026-06-20", "D-69", "D-70"]
---

# UX da interface web — navegação, botão Atualizar e odds (2026-06-20)

Três ajustes pedidos na interface (`scm/web.py` + `scm/templates/`): consistência visual + navegação completa, um botão para atualizar a base, e tornar o efeito das odds visível.

## D-69 — Consistência visual + navegação completa ✅

**Problema:** o `prospectivo.html` (criado no D-66) usava um tema ESCURO e nav no topo, destoando das outras três telas (`index`/`simulacao`/`bracket`), que compartilham um design system claro com **sidebar**. Além disso, **nenhuma tela linkava para `/prospectivo`**.

**Correção:** `prospectivo.html` reescrito no MESMO padrão (tema claro, `:root` igual, `.app/.sidebar/.sb-nav/.sb-foot`). A sidebar das **4 telas** agora tem os **4 links** (Prever · Simular · Chaveamento · Prospectivo), com o item ativo destacado. [verificado] grep: 4/4 telas com os 4 links.

## D-70 — Botão "Atualizar dados" (refresh do pipeline pela web) ✅

Botão no rodapé da sidebar (em todas as telas) que dispara o refresh completo SEM terminal:
**snapshot martj42 → ingest → Elo → features (PIT) → previsões**. Reusa os `run()` dos módulos (mesma lógica da CLI).

- Backend (`web.py`): `POST /api/update` roda o pipeline em **thread** (`_run_pipeline`); `GET /api/update/status` devolve o passo atual; `app.run(threaded=True)` permite o polling. Um job por vez (lock).
- Front: confirma (~1–2 min), faz polling a cada 1,5 s mostrando o passo ("Reconstruindo o Elo…", "Montando features…"), e recarrega a tela ao concluir. Erros (ex.: sem rede) aparecem no painel.
- É a **única** parte que toca a rede (o snapshot), coerente com "nada lê a internet no cálculo".
- *Ressalva:* evite prever/simular enquanto a atualização roda (a base está sendo reescrita).

## Odds — respondendo "não vi diferença" (e o que mudei) ✅

**As odds JÁ funcionavam** — não era bug. O que acontecia:

1. O efeito é **só no 1X2 (V/E/D)** e com **peso 20%** (contrato §3.8). Tudo o mais na tela — **λ, over/under, ambos-marcam, placares, confiança** — vem do **modelo (Poisson)** e **NÃO muda** com as odds (por design: o mercado é benchmark, não gera novo modelo). Como ~90% da tela é igual, parecia "sem diferença".
2. Só aplica se as **três** odds (casa/empate/fora) estiverem preenchidas.
3. Quando modelo e mercado concordam, o deslocamento é pequeno (~1–3 pp).

**O que mudei (UX, D-70):** o `predict_match` agora devolve o 1X2 **do modelo** (antes da mistura, campo `p_model`), e a tela mostra explicitamente **Modelo → Mercado → Misturado** com a variação em **pontos percentuais** e a nota de que só o 1X2 muda. Assim o efeito (mesmo pequeno) fica **visível**.

## Verificação

`web.py` compila ([verificado] `ast.parse`). Telas: 4 links + botão em todas ([verificado] grep). O servidor Flask e o refresh rodam **na sua máquina** (`python -m scm.web`) — o sandbox não serve Flask.

**Commit sugerido:**
```
feat(web): nav completa (+/prospectivo) e design unificado; botão "Atualizar dados"
(/api/update em thread + status); efeito das odds explícito (modelo→mercado→misturado).
```

## Relacionado
[[Evolução Nível 3]] · [[Como rodar o sistema]] · [[Registro de previsoes]]
