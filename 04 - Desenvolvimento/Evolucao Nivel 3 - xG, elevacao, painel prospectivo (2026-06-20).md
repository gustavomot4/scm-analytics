---
tags: [dev, evolucao, dados, produto, decisoes, nivel3]
status: atual
tipo: decisoes
data: 2026-06-20
aliases: ["Evolução Nível 3", "D-66..D-68", "Painel prospectivo"]
---

# Evolução Nível 3 — xG, elevação e painel prospectivo (2026-06-20)

Implementa o **Nível 3** (dados e produto) da [[Auditoria tecnica (Claude, 2026-06-20)|auditoria]] — o caminho que o Nível 2 mostrou ser o certo (o núcleo está no teto do `dr`; o ganho vem de **informação nova** e de **medir a Copa**). Três entregas: (#8) painel prospectivo, (#7a) xG alimentando o ataque/defesa, (#7b) elevação por dado, não por dict.

> **Verificação.** O painel e o no-regression do xG foram **verificados** (lógica self-contained no sandbox). O *ganho* do xG depende de dados do StatsBomb que não estão na base — o **portão roda na sua máquina** após ingerir o xG. `pytest` na sua máquina (quirk D-16).

---

## D-66 — Painel prospectivo `/prospectivo` (audit #8) ✅ — operacionaliza o laço da Copa

Página local que mede o **Brier real da Copa**, jogo a jogo, a partir do registro imutável do `registrar` (Nível 1/D-62). Rota `/prospectivo` + API `/api/prospectivo` em `web.py` (reusa `db.session`), template `templates/prospectivo.html`, e `registrar.dashboard_data(conn)` (resumo + previsão **vs RESULTADO vs MERCADO**, reusando `report` e `odds.market_read`).

Mostra: Brier prospectivo acumulado vs uniforme, nº de jogos medidos/abertos, e a tabela por confronto (modelo V/E/D · mercado V/E/D · placar real · Brier do jogo, com cor). [verificado] (sintético): 2 jogos fechados → Brier 0,376 vs uniforme 0,667 (ganho +0,29); ESP 3-0 previsto 0,90 → Brier 0,017; jogos abertos aparecem como "em aberto". Teste novo: `tests/test_registrar.test_dashboard_data`.

**Uso:** `python -m scm.web` → `http://127.0.0.1:5000/prospectivo`. Encha com `registrar register-batch` antes dos jogos e `settle-from-db` depois. **É o produto que faltava** para usar o sistema na Copa que está acontecendo.

## D-67 — xG histórico alimentando o ataque/defesa (audit #7a) 🔵 — a melhor alavanca de dado novo

A perna ataque/defesa (Nível 1/D-60) usa **gols**, que são ruidosos. O **xG** é menos ruidoso. Agora o `attack_defense` aceita um **prior** `{team_id: (atk_log, def_log)}` que serve de alvo de **inicialização e de shrinkage** (em vez de 0), vindo do `team_xg` via `attack_defense.xg_priors(conn)` (que usa `xg.xg_factor`). Onde há cobertura de xG, os ratings ficam menos ruidosos; onde não há, caem para 0 (neutro) — **comportamento idêntico ao atual sem xG**.

- `attack_defense._pass/run_pit/fit/gate_ad` ganham `priors=` (default None → IDÊNTICO). [verificado] no-regression: `priors={}` == sem priors (update bit a bit igual). Teste: `test_xg_priors_empty_and_noop`.
- CLI: `python -m scm.attack_defense --xg-prior` (avisa se `team_xg` vazio).

**Estado: candidato, NÃO verificado** (não há xG na base). Para medir: ingira o xG (`python -m scm.xg ingest <csv>` derivado do StatsBomb 2018/2022/Euro) e rode `python -m scm.attack_defense --xg-prior` — o portão decide se o xG-prior bate a versão só-gols. **Honestidade:** pode ser marginal (como estilo/calor); é o portão que decide.

## D-68 — Elevação por dado, não por dict (audit #7b / N-D) ✅

`factors.load_elevations(conn, csv)` (CLI `python -m scm.altitude --load-elevations <csv>`) ingere elevações de um CSV (`type,name,elevation_m`) para **`venues`** e **`teams.home_altitude_m`** — fazendo da elevação um dado em **banco**, auditável e extensível, gerado uma vez via Open-Meteo Elevation/Wikidata (snapshot; nada lê a internet no cálculo). Exemplo: `dados/elevations.csv.example`.

*Ressalva declarada:* o **runtime** (`factors.gd_alt`) ainda usa `CITY_ALT`/`TEAM_HOME_ALT` no código por velocidade (o `gd_alt` não recebe `conn`); o DB passa a ser o store de referência/expansão. Migrar o `gd_alt` para ler do DB exige passar `conn` por toda a cadeia (predict_match/simulate/predictor) — follow-up de baixa prioridade.

---

## Síntese do Nível 3

O **painel** (#8) é a entrega de produto que torna o sistema **utilizável na Copa** — fecha de verdade o laço prospectivo. O **xG** (#7a) é a alavanca de dado novo mais promissora, montada e pronta para o portão (decisão honesta: medir, não assumir). A **elevação por dado** (#7b) tira o último dado hardcoded da posição de "fonte da verdade".

## Comandos (na sua máquina, após o pull)

```bash
cd scm_analytics && rm -rf scm/__pycache__ tests/__pycache__ && pip install -r requirements.txt
python -m pytest -q

# painel prospectivo (a Copa está acontecendo — use já):
python -m scm.web      # -> http://127.0.0.1:5000/prospectivo
python -m scm.registrar register-batch        # registra a rodada (dados/fixtures.json)
#   ...após os jogos:
python -m scm.ingest --download && python -m scm.registrar settle-from-db

# xG -> ataque/defesa (precisa do CSV de xG do StatsBomb):
python -m scm.xg ingest dados/xg.csv
python -m scm.attack_defense --xg-prior        # portão: xG-prior vs só-gols

# elevação por dado:
python -m scm.altitude --load-elevations dados/elevations.csv
```

**Mensagem de commit sugerida:**
```
feat(dados+produto): painel prospectivo /prospectivo (Brier real da Copa, modelo vs resultado
vs mercado); xG como prior do ataque/defesa (attack_defense --xg-prior, OFF/gated); elevação
por CSV->venues/teams (altitude --load-elevations). Default do modelo inalterado.
```

## Relacionado
[[Auditoria tecnica (Claude, 2026-06-20)]] · [[Evolução Nível 1]] · [[Evolução Nível 2]] · [[xG preditivo]] · [[Forca ofensiva-defensiva]] · [[Registro de previsoes]]
