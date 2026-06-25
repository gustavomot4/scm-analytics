---
tags: [projeto, guia, uso]
status: atual
tipo: guia
data: 2026-06-17
aliases: ["Como rodar", "Guia de uso", "Manual"]
---
# Como rodar o sistema (do zero ao resultado)

Guia completo e prático. Tudo roda **local e offline** (a única coisa que usa a internet é baixar a base, 1×). Código em `scm_analytics/`. Detalhe dos módulos: [[Codigo (estrutura)]].

## 0. Pré-requisitos (instalar 1×)
- **Python 3.11+** — Windows: `winget install Python.Python.3.12`. **Feche e reabra o terminal** depois (o PATH só atualiza em janela nova). Confirme com `python --version` (ou `py --version`).
- **Git** (opcional, para versionar) — já configurado se você clonou de `gustavomot4/scm-analytics`.

## 1. Ambiente
Na pasta `scm_analytics`:
```
cd scm_analytics
python -m venv .venv
.venv\Scripts\Activate.ps1          # Windows PowerShell  (Linux/Mac: source .venv/bin/activate)
pip install -r requirements.txt     # numpy, pandas, matplotlib, requests, flask, pytest
```
> Se o PowerShell bloquear o Activate: `Set-ExecutionPolicy -Scope Process RemoteSigned` (vale só nessa janela), ou use `.venv\Scripts\python` no lugar de `python`.

## 2. Construir a base (pipeline)
Cada comando é **idempotente** (pode repetir):
```
python -m scm.ingest --download     # baixa o histórico do martj42 (~49k jogos) -> dados/results.csv  [requer rede, 1x]
python -m scm.ingest                # normaliza -> dados/scm.sqlite
python -m scm.elo_engine --top 30   # reconstrói o Elo cronológico + mostra o top-30
python -m scm.features_pit          # features point-in-time (forma, dr_adj, σ_dr)
python -m scm.predictor             # gera as previsões (modelo baseline-v0.4-ad)
```
Pronto — a base e as previsões estão no `dados/scm.sqlite`.

## 3. Validar (opcional, mostra que o modelo tem skill)
```
python -m scm.backtest_harness --major   # Brier vs uniforme com IC (jogos de torneio)
python -m scm.report --major             # calibração (reliability) + cobertura de banda
python -m scm.calibrate_confidence       # ancora a confiança na confiabilidade medida (grava em meta)
python -m scm.report --btts --major      # diagnóstico do 'ambos marcam' (previsto vs real)
python -m scm.estilo                      # PORTÃO do estilo (tendência de gols) na Brier de BTTS
```
Esperado: Brier ~0,56 **< uniforme 0,667 com IC que não cruza zero**, bem calibrado. O `calibrate_confidence` imprime a curva de acerto por faixa e mostra que **confiança alta = mais acerto**.

## 4. Prever um jogo
**No terminal:**
```
python -m scm.predict_match "Brazil" "Argentina"               # sede neutra
python -m scm.predict_match "Mexico" "Germany" --city "Mexico City"   # aplica altitude (E1)
python -m scm.predict_match "United States" "England" --mando 40      # vantagem de anfitrião 2026
```
Nomes em inglês (padrão martj42); se errar, o programa sugere ("Brasil" → "Brazil").

A saída traz P(V/E/D)+banda, **over/under 0.5–4.5**, ambos marcam, **não sofrer gol**, **quem marca primeiro**, dupla chance, handicap, placares prováveis e a **confiança** (0–100). Tudo sai do mesmo Poisson — ver [[MODELO_FINAL]] §4.

**Na interface gráfica (navegador):**
```
python -m scm.web                   # abre http://127.0.0.1:5000
```
Digite as duas seleções (autocompleta), escolha a sede e clique em Prever. Ctrl+C para sair.

## 5. Atualizar com jogos recentes
O sistema usa um **snapshot** (não se atualiza sozinho — ver [[Decisoes tecnicas]] D-03). Para pegar jogos novos, re-rode 3 comandos (idempotente, só adiciona o que é novo):
```
python -m scm.ingest --download ; python -m scm.ingest ; python -m scm.elo_engine ; python -m scm.features_pit ; python -m scm.predictor
```
Depois, `predict_match`/`web` já usam o Elo atualizado. (Para automatizar, agende no Agendador de Tarefas do Windows.)

## 6. Testes
```
python -m pytest -q                 # 137 testes
```
> Quirk de sandbox: se uma edição `.py` não refletir, `rm -rf scm/__pycache__ tests/__pycache__`.

## Resumo dos comandos
| Objetivo | Comando |
|---|---|
| Instalar deps | `pip install -r requirements.txt` |
| Construir base | `ingest --download` → `ingest` → `elo_engine` → `features_pit` → `predictor` |
| Validar | `backtest_harness --major` · `report --major` · `calibrate_confidence` |
| Prever (terminal) | `predict_match "TimeA" "TimeB" [--city ... | --mando N]` |
| Prever (interface) | `web` → http://127.0.0.1:5000 |
| Atualizar | `ingest --download` → `ingest` → `elo_engine` |
| Testar | `pytest -q` |

## Opcional — re-testar fatores (C2.5)
- Coeficientes: `python -m scm.calibrate --cutoff 2018-01-01` (mantido v0.1 — D-17).
- Altitude: `python -m scm.altitude` (**adotada** — D-18).
- Calor: `python -m scm.heat --build-climatology` (lento) → `python -m scm.heat` (**rejeitado** — D-19).
- **Estilo (tendência de gols):** `python -m scm.estilo` — **rejeitado** pelo portão (D-23: corrige a média do BTTS mas não a previsão por jogo). Preview: `python -m scm.predict_match "A" "B" --estilo`.
- **Nível de gols (T_base):** `python -m scm.calibrate_total` calibra o T_base na Brier de BTTS/over (o lugar certo) com guarda de 1X2 — o jeito principiado de corrigir o BTTS ~4pp alto (D-25).
- **BTTS enviesado?** `python -m scm.report --btts --major` compara o 'ambos marcam' previsto com o real.
- Confiança: `python -m scm.calibrate_confidence` ancora a confiança no backtest (**adotado** — D-20).

## Problemas comuns
- **"Python não encontrado"** → não instalado ou terminal não reaberto após o `winget install`.
- **`ModuleNotFoundError`** (numpy/flask/requests) → faltou `pip install -r requirements.txt`.
- **"snapshot não encontrado"** / **"SQLite não existe"** → rode o passo 2 na ordem.
- **`gh`/`python` não reconhecido logo após instalar** → reabra o terminal.

Ver também: [[MODELO_FINAL]] (o que o sistema calcula) · [[Backtest baseline (resultados)]] (validação) · [[CLAUDE]] (contexto).

## 7. Simular a Copa inteira (quem tem mais chance de ser campeão)
1. **Preencha o sorteio** em `scm_analytics/dados/copa2026.json` — os 12 grupos (A–L) com 4 seleções cada, **nomes em inglês** (padrão martj42; cheque com `python -m scm.elo_engine --top 60`). Os grupos **G e H já vêm preenchidos**; substitua os `TODO_*`. As dicas no próprio arquivo (`_dicas_pares_mesma_chave_round1`) dizem quais duplas já se enfrentaram (mesmo grupo).
2. **Rode:**
```
python -m scm.simulate --sims 20000          # tabela de P(campeão/final/semi/passar)
python -m scm.web   ->  http://127.0.0.1:5000/simulacao   # versão visual
```
Os jogos já disputados são **travados** automaticamente da base. É **insight**, não previsão validada — probabilidade, não certeza.

> **Atualização 2026-06-18:** o `copa2026.json` já vem com o **sorteio oficial completo** da Copa 2026 (obtido por busca web e **cruzado 100%** com os jogos já disputados no martj42). Não precisa preencher — só rode `python -m scm.simulate`. Edite apenas se a FIFA alterar algo. Snapshot atual do favoritismo: Argentina ~18,6%, Espanha ~15%, França ~11%.

> **Chaveamento oficial + ε (2026-06-18):** a simulação já usa o **chaveamento real da FIFA** (não mais sorteio aleatório). Para calibrar o ε do mata-mata com dados de pênaltis (opcional, melhora a fidelidade): `python -m scm.calibrate_ko --download` (baixa o `shootouts.csv` 1x) — ele mede quanto o time mais forte de fato vence na disputa e sugere o ε. Até lá, ε=0,03 (pênalti ~moeda, como a literatura indica).


## ▶ Atualização 2026-06-21 — v0.4 e comandos novos
Modelo atual: **`baseline-v0.4-ad`** (perna ataque/defesa ligada, w_ad=0,50). A **simulação** agora
mistura o sinal de gols no λ (`config.SIM_AD_BLEND=0,50`, portão major +0,0071). Testes: **137** (rode `pytest -q`).
Comandos novos:
```
python -m scm.odds ingest dados/odds_copa_disputados.csv   # odds reais (de-vig) -> odds_hist
python -m scm.odds bench --major                           # Brier do modelo vs MERCADO (juiz honesto)
python -m scm.xg build open-data --csv dados/xg.csv        # xG por seleção (clone do StatsBomb)
python -m scm.attack_defense --gate-xg                     # PORTÃO: xG acrescenta? (OFF até passar)
```
Detalhe: [[Evolucao v0.4 - perna AD + sigma no torneio (2026-06-20)]] · [[Como usar xG (prior de elenco) — turnkey (2026-06-20)]].

## ▶ Atualização 2026-06-21 (b) — abrir com 1 clique + pop-up de atualização
**Abrir sem terminal:** **duplo-clique em `scm_analytics/Abrir SCM (Copa 2026).bat`**. Na 1ª vez ele
cria o ambiente, instala as dependências e constrói a base (baixa os dados); nas próximas, só sobe o
servidor e abre o navegador. Para sair, feche a janela.

**Atualizar os dados (1 botão):** na interface, o **pop-up flutuante** (canto inferior direito) tem o
botão **"Atualizar tudo"** — baixa o snapshot novo, reconstrói o Elo, monta as features e gera as
previsões. Ele mostra **barra de %, etapa e logs ao vivo**, **persiste ao trocar de tela** (o estado
vive no servidor), e pode ser **minimizado** (vira uma pílula com a %; lembra a preferência). Ao
terminar, clique em **Recarregar página** para ver os números novos.

## ▶ Atualização 2026-06-21 (c) — "Atualizar tudo" agora é rápido (incremental)
O botão **"Atualizar tudo"** passou a reprocessar **apenas os jogos novos** (os antigos não mudam —
features point-in-time). Resultado idêntico ao rebuild completo, mas em **segundos** em vez de ~12 min.
Ressalva: pressupõe que os jogos novos são os mais recentes (append-only — o caso normal). Se o
snapshot **corrigir um jogo antigo** ou se você **mudar o código** das features, faça um rebuild
completo uma vez: `python -m scm.features_pit && python -m scm.predictor` (ou apague `match_features`
e clique em Atualizar).
