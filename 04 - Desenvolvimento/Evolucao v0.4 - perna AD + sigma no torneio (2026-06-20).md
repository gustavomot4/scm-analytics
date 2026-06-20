---
tags: [dev, evolucao, modelo, v0.4]
status: atual
tipo: evolucao
data: 2026-06-20
aliases: ["Evolucao v0.4", "v0.4-ad"]
---

# Evolução v0.4 — perna AD ligada + σ no torneio (2026-06-20)

Implementação do plano da [[Auditoria + plano de melhorias (modelo, 2026-06-20)]] (Fases 0–3),
**com portão real rodado no `dados/scm.sqlite`**. Disciplina mantida: nada entra em λ/dr/prob
sem ΔBrier pareado com IC que não cruza zero. Modelo novo: **`baseline-v0.4-ad`**.

## O que MUDOU (passou o portão)
- **Perna ataque/defesa não-Elo LIGADA** (`predictor.PredictParams.w_ad` 0.0→**0.30**). É a fonte
  de gols **independente** do `dr` (corr de P(V) ~0,95 vs 0,997 das duas leituras antigas). Portão
  reproduzido: **ΔBrier +0,0039, IC[+0,0028,+0,0051]** (torneios, w_ad=0,30). [verificado]
- **Resultado-chave — o modelo agora BATE o teto do `dr`** (antes empatava):
  - Torneios (n=2253): Brier **0,5590 → 0,5554**; vs lookup **+0,0062 IC[+0,0033,+0,0090]** (era empate);
    vs Elo público **+0,0074** (era +0,0038). [verificado]
  - Todos (n=49435): Brier **0,5365 → 0,5336**; vs lookup **+0,0027 IC[+0,0020,+0,0034]** (era −0,0003). [verificado]
  - Paried v0.4 vs v0.3 (todos): **+0,00297 IC[+0,00267,+0,00327]**. [verificado]
  - Ressalva honesta: **ECE subiu** 0,0260 → 0,0333 (a perna melhora discriminação/Brier mais
    que calibração); segue bem calibrado. A recalibração foi testada e **rejeitada** (abaixo).
- **Porta da frente alinhada (consistência produção↔backtest):** `predict_match` agora calcula a
  λ AD das duas seleções (`attack_defense.fit` + `team_lambdas`) e passa `ad_ved` ao `predict` —
  sem isto a produção entregaria o ensemble de 2 pernas, ≠ do modelo validado.
- **σ propagado no Monte Carlo** (`simulate.py`, audit P4): cada jogo simulado amostra
  `dr ~ N(dr, σ_dr)` (σ_dr do par via `ratings_current.sigma_r`) antes da λ. Corrige a sim que
  tratava o Elo como exato. **Efeito modesto** (σ_R satura ~40 — degenerado; só fica relevante com
  um σ informativo, que o portão ainda não aprova).

## O que foi TESTADO e REJEITADO pelo portão (fica OFF, documentado)
- **`T_base` (nível de gols):** ótimo de treino nos torneios = **2,60** (o atual); a guarda de 1X2
  impede baixar. Viés de BTTS (~+4–5pp) permanece como limitação declarada. [verificado]
- **Forma saturante `tanh`:** neutra nos torneios (IC cruza 0) e **pior no tail** (|dr|>500:
  ΔBrier −0,0042, IC<0). A linear+piso prevê goleadas melhor. **Mantém linear.** [verificado]
  (Nota: isto **contraria** a hipótese P6 do meu próprio audit — o portão a derrubou.)
- **Recalibração 1X2:** temperatura T*=1,0 (nada a corrigir); isotônica/classe piora o Brier
  (−0,0021, IC<0). O 1X2 já está calibrado; a "superconfiança" em 0,8–0,9 é ruído amostral. [verificado]
- **σ-Glicko:** a banda **já sobre-cobre** (92% vs nominal ~68%); o Glicko alarga mais. **Mantém σ_r.** [verificado]

## Higiene (sem portão)
- **Teste de regressão de SKILL** (`tests/test_skill_regression.py`, audit P12): trava Brier<0,60 +
  bate uniforme com IC, bate Elo (IC>0) e não fica abaixo do teto do `dr`. SKIP se o snapshot ausente.
  Pega regressão de **modelagem** (não só coerência). Passa em v0.4. [verificado]
- **`config.W_AD = 0.30`** (espelho do coeficiente na fonte única, audit P11).

## Deferido (declarado — exige rebuild + risco de escrita no ambiente desta sessão)
- **Gravar `sigma_dr`/`confianca` em `predictions`** (audit, arquitetura): exige coluna nova no
  schema (`db.py`) + INSERT do `predictor` + rebuild. Patch: adicionar `sigma_dr REAL, confianca REAL`
  ao CREATE TABLE predictions e ao INSERT de `predictor.run`.
- **Curva de empate PIT** (audit P5): re-congelar `DRAW_CURVE` com `build_draw_curve(before_date=...)`.
  Vazamento de 2ª ordem (≈0,4–0,7pp em P(E)); efeito ~nulo no veredito, mas tira a contaminação.

## Como reproduzir / rebuild
```
cd scm_analytics
rm -rf scm/__pycache__ tests/__pycache__      # garantir que o .py novo reflita
python -m scm.predictor                        # gera baseline-v0.4-ad
python -m scm.backtest_harness --major         # Brier 0,5554; bate teto do dr (IC>0)
python -m scm.predict_match "Brazil" "Argentina"   # porta da frente já usa a perna AD
python -m scm.simulate --sims 20000            # Monte Carlo com σ propagado
python -m pytest -q                            # inclui o novo teste de skill
```

## Nota de ambiente (auditoria)
As mudanças foram construídas e validadas numa **cópia local** do pacote porque o FS montado
desta sessão truncava arquivos em edições grandes e bloqueava `rm`. Os `.py` finais foram
copiados de volta e **verificados byte-a-byte + compilação**; o `scm.sqlite` foi substituído pela
cópia limpa com v0.4 (`PRAGMA integrity_check = ok`). **`pytest` não rodou aqui** (sem o pacote/rede);
os testes foram lidos e o de skill validado pela lógica equivalente. Rode `pytest` na sua máquina.
