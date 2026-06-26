---
tags: [dev, evolucao, mercados, statsbomb, tempo-do-gol, cartoes, escanteios]
status: atual
tipo: evolucao
data: 2026-06-25
aliases: ["Tempo do gol", "Cartões e escanteios", "D-71", "D-72"]
---

# Tempo do gol + cartões/escanteios (StatsBomb local, 2026-06-25)

Dois mercados de "dado externo" a **R$ 0**, usando o clone LOCAL do StatsBomb open-data (~18 GB, já no disco do xG) — **nada lê a internet no cálculo** (D-03). Cumpre a promessa pendente da **D-21** ("'tempo do gol' fica fora até ingerir o minuto"). Disciplina mantida: **portão antes de publicar como previsão**.

> **Resumo:** **tempo do gol PASSOU** (Poisson não-homogêneo; calibração ±1,2 pp) e está no ar. **Cartões/escanteios por seleção REPROVARAM** o portão (sem sinal fora de amostra) → publicados só como **histórico descritivo + baseline da competição**, rotulados na tela como **não-previsão**.

## D-71 — Tempo do gol ✅ (aprovado, no ar)
**O que é.** "Quando sai o gol" não sai da matriz de placar (que só vê o total). Modelamos o minuto do gol como **processo de Poisson não-homogêneo**: com Λ = λ_a+λ_b e F(t) = fração empírica de gols até o minuto t,
- gols em [0,t] ~ Poisson(Λ·F(t));
- P(1º gol até X) = 1 − exp(−Λ·F(X));  P(gol no 1ºT) = 1 − exp(−Λ·F(45));  P(2ºT) = 1 − exp(−Λ·(1−F(45)));
- P(gol nos dois tempos) = P(≥1 1ºT)·P(≥1 2ºT)  (incrementos disjuntos ⇒ independentes);
- Resultado no intervalo (HT): gols por time no 1ºT ~ Poisson(λ_i·F(45)).

Não toca em λ nem no 1X2 — é **releitura** (como os mercados da D-21), zero grau de liberdade novo no núcleo.

**Curva (fonte).** StatsBomb local: **314 jogos, 771 gols, f45 = 0,401** (40% dos gols no 1ºT, 60% no 2º — padrão conhecido). Snapshot em `dados/goal_timing.json`. Amostra AMPLA (você roda 1×, requer rede): `python -m scm.timing download` + `python -m scm.timing build-csv dados/goalscorers.csv` (martj42).

**Portão — calibração do pressuposto de Poisson** (previsto com Λ̄=2,46 × observado, StatsBomb): [verificado]

| mercado | previsto | observado | Δ |
|---|---|---|---|
| gol no 1ºT | 62,6% | 63,7% | −1,1 pp |
| gol no 2ºT | 77,0% | 75,8% | +1,2 pp |
| gol nos 2 tempos | 48,2% | 48,7% | −0,5 pp |
| 0 gols | 8,6% | 9,2% | −0,7 pp |

Tudo em **±1,2 pp** → o modelo de tempo **passa** (a independência entre tempos vale dentro de ~0,5 pp). Ressalva honesta: estabilidade do f45 entre metades aleatórias **0,43 vs 0,37** (ruído da amostra de ~800 gols); o goalscorers.csv do martj42 aperta isso.

**Entregue.** `scm/timing.py` (curva + `timing_markets`); `predict_match` anexa `mk["timing"]`; seção **"Tempo do gol"** na tela de previsão: gol 1ºT/2ºT, gol nos dois tempos, 1º gol até 15/30 min, faixa do 1º gol, sem gols e **resultado no intervalo (HT)**. Reproduzir a curva: `python -m scm.timing build-sb open-data`.

## D-72 — Cartões/escanteios ⚠ (reprovado como previsão; publicado como histórico + baseline)
**O que tentamos.** Taxas por seleção do StatsBomb (cartão = eventos "Bad Behaviour"/"Foul Committed" com `card`; escanteio = passe tipo "Corner"), modelo Maher (λ = μ·ataque_i·defesa_j) e formas alternativas (aditiva "own-rate"; "for + against").

**Dados.** 314 jogos, **73 seleções** (n≥3, casadas com nomes do banco); médias realistas: **3,63 cartões** e **9,07 escanteios** por jogo. Snapshot em `dados/setpiece.csv`.

**Portão — leave-one-out, MAE do total (modelo-por-time vs média-global):** [verificado]

| mercado | melhor forma vs média global | veredito |
|---|---|---|
| cartões | **+0,3%** (Maher −4,1%) | **sem sinal** |
| escanteios | **+1,7%** (Maher +0,3%) | **dentro do ruído** |

Cartão é ditado por árbitro/jogo, não pela seleção; escanteio tem sinal fraco demais com amostras pequenas (muitos times 3–7 jogos). **Reprovado como preditor por seleção** — mesma régua que barrou xG/DC/σ-Glicko (D-50/D-39/D-40/D-42).

**O que a média global ACERTA (baseline calibrado):** over 3,5 cartões prev 48,1% × obs 49,4%; over 9,5 escanteios prev 41,6% × obs 40,8%. [verificado]

**Entregue (honesto).** `scm/setpiece.py`; seção **"Cartões & escanteios (histórico)"** na previsão, com (a) **histórico descritivo** de cada seleção (cartões/escanteios por jogo + nº de jogos) e (b) **over/under pela média da competição** (cartões 2,5–5,5; escanteios 7,5–11,5), **rotulado na tela** como baseline, não previsão por time. Não há flag de "ligar como preditor" — a decisão é **não prever por time**. Reproduzir: `python -m scm.setpiece build-sb open-data`.

**Limite a R$ 0.** Cartão/escanteio de **seleção** só sai do StatsBomb (cobertura parcial: 6 competições 2018–2024); football-data.co.uk tem isso só de **clubes**. É o teto a custo zero.

## Arquivos
- **Novos:** `scm/timing.py`, `scm/setpiece.py`, `dados/goal_timing.json`, `dados/setpiece.csv`.
- **Tocados:** `scm/predict_match.py` (anexa `mk["timing"]` e `mk["setpiece"]`, com curva/taxas carregadas 1×), `scm/templates/index.html` (2 seções novas).
- **Verificação:** módulos compilam; curva/taxas conferidas com dados reais; `index.html` renderiza (Jinja); `predict_match('Brazil','Argentina')` devolve os dois blocos. **Flask não roda no sandbox da sessão — teste o servidor na sua máquina** (abra pelo `Abrir SCM (Copa 2026).bat`).
