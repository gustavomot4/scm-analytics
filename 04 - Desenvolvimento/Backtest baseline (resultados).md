---
tags: [dev, backtest, resultados, baseline]
status: validado
tipo: resultados
data: 2026-06-17
---
# Backtest baseline (resultados) — v0.1

Primeiro backtest com **dados reais** (martj42, 49.423 jogos), **point-in-time**, com coeficientes **placeholder não-fitados** (θ=0,45; κ=0,10; curva de empate proxy). Portanto, calibração **fora de amostra** — não overfit.

## Todos os jogos (n=49.423)
- **Brier 0,538** (uniforme 0,667) · LogLoss 0,912 · RPS 0,183
- ganho vs uniforme **+0,129**, IC95 **[+0,125, +0,132]** → bate o uniforme com IC ✅
- **ECE 0,012**; reliability ~diagonal perfeita; banda dentro

## Torneios — WC/Euro/Copa América (n=2.241) — **recorte do aceite (C2 §2.2)**
- **Brier 0,562** (uniforme 0,667) · LogLoss 0,951 · RPS 0,194
- ganho vs uniforme **+0,104**, IC95 **[+0,089, +0,120]** → bate o uniforme com IC ✅
- **ECE 0,023**; banda dentro (obs 0,466 em [0,389, 0,557])
- reliability boa; leves desvios em faixas de n pequeno (0,8–0,9 superprediz, n=84)

## Veredito
Baseline **VALIDADO** nos invariantes centrais (bate uniforme com IC que não cruza zero; bem calibrado; banda com cobertura nominal) — inclusive no recorte de torneios, que é o mais difícil/comparável a 2026.

## Ressalvas / pendências
- **Não** comparado vs **Elo-público** (só vs uniforme).
- Benchmark eloratings: top-30 plausível, mas com artefatos (Iugoslávia extinta, Colômbia alta, sem recência) → comparar snapshot atual de ativos.
- **C2.5:** fatores ambientais (altitude/calor/bola parada) um a um **atrás do portão** (`compare()` — IC do ΔBrier não cruza zero); calibrar coeficientes num split de treino.

[[BACKLOG]] · [[Codigo (estrutura)]] · [[camada2-planejamento-v1]] · [[MODELO_FINAL]]

## Calibração (C2.5, passo 1) — NÃO adotada
Split treino/teste por torneios (cutoff 2018-01-01; treino n=1905, teste n=336), grid de 243 combos.
- Melhores coeficientes ≈ placeholders (θ=0,45 e draw_base=0,27 **não mudaram**; κ 0,10→0,15, T_base 2,6→2,4, w_poisson 0,56→0,65).
- Brier teste: placeholder 0,5857 → calibrado 0,5844. **Ganho +0,0013, IC95 [+0,0001, +0,0025]** — passa o portão por um fio, mas é **praticamente nulo**.
- **Decisão (ver D-17): manter v0.1.** Os placeholders da v5 estão confirmados como quase ótimos; não vale churn de versão por +0,0013. `calibrate.py` fica como ferramenta para re-checar quando a base crescer.


## Fatores ambientais (C2.5) — pelo portão
- **Altitude (E1): ADOTADA.** `python -m scm.altitude` → ganho de Brier **+0,0491**, IC95 [+0,028, +0,070] nos **554 jogos de altitude** (La Paz/Quito/Bogotá/CDMX), θ=0,5 (McSharry). Forte e robusto mesmo após o Elo. Modelo passa a **`baseline-v0.2-altitude`** (gd_alt ativo; =0 fora de altitude).
- **Calor (E3), bola parada (E4):** próximos, cada um atrás do portão.

- **Calor (E3): NÃO adotada.** Portão no Brier de **over/under** (jogos com WBGT>28°C via climatologia mensal Open-Meteo, n=15.378): ganho **+0,0007**, IC [−0,0008, +0,0022] (cruza zero). Proxy de climatologia é grosseiro e o efeito é sutil → o portão rejeita (D-19). Contraste honesto com a altitude (que passou forte): a disciplina distingue um efeito real de um marginal.

## Atualização v0.3 (2026-06-18) — correções do audit externo

Modelo **`baseline-v0.3-altitude`** (curva de empate empírica C1 + σ informativo + cobertura de altitude 2026). Reconstrução completa (martj42 49.423, point-in-time). Ver [[Auditoria tecnica externa (2026-06-18)]] e [[Decisoes tecnicas]] D-26..D-30.

**Todos os jogos (n=49.423)**
- Brier **0,5366** (v0.2.1 era 0,5375 — leve melhora, sem regressão) · LogLoss 0,9094 · RPS 0,1823
- ganho vs uniforme **+0,1301** IC95 [+0,1267, +0,1336] ✅
- **vs baseline ELO PÚBLICO** (novo, D-27): Brier modelo 0,5366 vs Elo 0,5393 → ganho **+0,0028** IC95 **[+0,0023, +0,0033]** → **bate o Elo com IC > 0** ✅

**Torneios — WC/Euro/Copa América (n=2.241)**
- Brier **0,5595** (v0.2.1 era 0,5598) · ECE 0,0254 · banda agregada dentro
- ganho vs uniforme **+0,1072** IC95 [+0,0922, +0,1227] ✅
- **vs ELO PÚBLICO**: Brier modelo 0,5595 vs Elo 0,5631 → ganho **+0,0037** IC95 **[+0,0009, +0,0066]** → **bate o Elo com IC > 0** ✅
- **Cobertura por faixa (novo, D-30):** 8/10 faixas de p_v dentro da banda; as 2 fora são [0,0–0,1] e **[0,8–0,9] (obs 0,74 vs banda [0,84–0,92] → superconfiança em favoritos fortes, agora medida)**.

**Veredito v0.3.** O motor agora tem um comparador **não-trivial** (Elo público) e **o supera com IC que não cruza zero** — o critério de aceite central que faltava (camada2 §5.1). Edge sobre o Elo é **pequeno mas real** (+0,003 de Brier), coerente com a literatura. Mando do anfitrião (P04) e Dixon-Coles seguem no backlog.
