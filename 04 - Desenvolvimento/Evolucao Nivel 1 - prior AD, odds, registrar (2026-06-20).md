---
tags: [dev, evolucao, modelo, decisoes, nivel1]
status: atual
tipo: decisoes
data: 2026-06-20
aliases: ["Evolução Nível 1", "D-60..D-62", "Prior ataque-defesa"]
---

# Evolução Nível 1 — prior ataque/defesa, odds, registrar (2026-06-20)

Implementa o **Nível 1** das melhorias recomendadas na [[Auditoria tecnica (Claude, 2026-06-20)|auditoria]]: (1) **diversidade real do ensemble** via um prior ataque/defesa não-Elo, (2) **odds** na porta da frente, (3) **laço prospectivo** operacional. O item (1) é o de maior impacto — e o **único com evidência de backtest reproduzida** — então respeita a disciplina do portão: entra atrás de `w_ad` (peso), **OFF por padrão**.

> **Verificação.** Reproduzi o backtest de torneios (n=2.249) reconstruindo a base do `results.csv` no sandbox (o mesmo método da auditoria). Números marcados **[verificado]**. O `pytest` completo deve rodar **na sua máquina** (quirk D-16 do mount).

---

## D-60 — Prior ATAQUE/DEFESA não-Elo: diversidade REAL do ensemble (audit P-A) ⭐

**Problema.** Poisson e Elo-direto saem do **mesmo escalar `dr`** → são duas leituras quase idênticas (corr P(V) **0,997** [verificado]); o "ensemble" é redundante e o edge sobre o Elo é minúsculo (+0,0038).

**Solução (`scm/attack_defense.py`).** Um gerador **independente** de (λ_A, λ_B): ratings de **ataque** e **defesa** por seleção, estimados dos **gols** (modelo Poisson/Maher, **online e point-in-time**, paramétrico/auditável — sem ML, respeita D-02):
```
λ_home = exp(μ + atk[h] − def[a] + mando_log·não_neutro)
λ_away = exp(μ + atk[a] − def[h])
```
Atualização online por jogo (gradiente da NLL de Poisson, erro = λ−gols) com shrinkage L2; o λ **pré-jogo** é gravado antes de atualizar (anti look-ahead, como o `match_ratings`). Entra como **3ª perna do ensemble** em `predictor.predict` (`ad_ved` + peso `PredictParams.w_ad`).

**Evidência [verificado] (torneios, n=2.249):**

| Métrica | Valor |
|---|---|
| Diversidade: corr P(V) **Poisson–AD** | **0,947** (vs Poisson–Elo 0,997) — sinal genuinamente independente |
| AD sozinho (Brier) | **0,5535** < ensemble base 0,5617 (o AD **sozinho** já bate o ensemble) |
| Portão w_ad=0,20 | ΔBrier **+0,00295** IC[+0,00209, +0,00380] ✅ |
| Portão w_ad=0,30 | ΔBrier **+0,00392** IC[+0,00273, +0,00509] ✅ |
| Portão w_ad=0,40 | ΔBrier **+0,00467** IC[+0,00320, +0,00612] ✅ |
| Pipeline w_ad=0,40 | Brier **0,5617 → 0,5571** (melhora +0,0047) |

**O ganho da perna AD (+0,0047) é MAIOR que todo o edge prévio do modelo sobre o Elo (+0,0038) — praticamente dobra o sinal de skill.** É a melhoria mais impactante feita até aqui.

**Estado: OFF por padrão** (`w_ad=0.0` → ensemble IDÊNTICO ao validado, [verificado] no-regression). Adoção (após reproduzir o portão na sua máquina):
1. `predictor.py`: `w_ad: float = 0.40` e `MODEL_VERSION = "baseline-v0.4-ad"` (mudança de modelo = nova versão, por contrato).
2. `python -m scm.predictor` (regrava `predictions` com a perna AD; `predictor.run` chama `attack_defense.run_pit` quando `w_ad>0`).
3. `python -m scm.backtest_harness --major` (confirma o Brier menor).

**Ressalvas honestas:** o peso `w_ad` foi avaliado **na própria amostra de teste** (não num split treino/teste) — para um peso "oficial", faça grid-search de `w_ad` no treino e valide no teste (o portão IC>0 já é robusto mesmo no peso conservador 0,20). Os hiperparâmetros do AD (μ, lr, reg) são defaults sensatos [a calibrar], não ajustados. Teste novo: `tests/test_attack_defense.py`.

## D-61 — Odds na porta da frente (audit #2, 3ª perna de mercado)
A infra de odds já existia (`scm/odds.py`: de-vig, blend 0,20, `odds_hist`, `market_read`; o `registrar` já auto-carrega). **Faltava a porta da frente usar o mercado gravado.** Agora `predict_match(..., date=...)` (CLI `--date`) **auto-carrega** as odds do `odds_hist` para o confronto quando nenhuma `--odds` é passada — igual ao registrar. Sem `date`/sem dado, segue sem mercado (inalterado).

Workflow:
```
python -m scm.odds ingest dados/odds.csv                      # de-vig + grava (ver odds.csv.example)
python -m scm.predict_match "Spain" "Uruguay" --date 2026-06-26   # usa o mercado gravado (mistura 20%)
```
*Sem odds históricas gratuitas (lacuna declarada), a perna de mercado não tem backtest — é benchmark prospectivo, não validação.*

## D-62 — Registrar operacional (audit #3 / P-G, fecha o laço prospectivo)
O `registrar.py` (register/settle/report/register-batch/settle-from-db, imutável, hash-carimbado) já estava completo — **só não era o caminho default.** Agora `register-batch` usa **`dados/fixtures.json` por padrão** (sem precisar passar o caminho) e avisa se faltar. Substitui o `registro-previsoes.csv` manual (que fica histórico) pelo `registro-auto.csv` gerado por código.

Workflow por rodada (a Copa está acontecendo — comece já):
```
cp dados/fixtures.json.example dados/fixtures.json     # preencha os jogos da rodada
python -m scm.registrar register-batch                # registra todos (imutável, pré-jogo)
# depois dos jogos:
python -m scm.ingest --download && python -m scm.registrar settle-from-db
python -m scm.registrar report                        # Brier PROSPECTIVO real vs uniforme
```

---

## Comandos (rodar na sua máquina, após o pull)

```bash
cd scm_analytics
rm -rf scm/__pycache__ tests/__pycache__
pip install -r requirements.txt
python -m pytest -q                          # inclui test_attack_defense (novo)

# pipeline (base inalterada por padrão):
python -m scm.ingest && python -m scm.elo_engine && python -m scm.features_pit && python -m scm.predictor

# PORTÃO do prior AD (reproduz +0,0039 IC>0) e ratings:
python -m scm.attack_defense
```

**Mensagem de commit sugerida:**
```
feat(modelo): prior ataque/defesa não-Elo como 3ª perna do ensemble (P-A) — diversidade
real (corr 0,95 vs 0,997); portão +0,0047 de Brier (dobra o edge sobre o Elo), OFF por
padrão (w_ad). Odds auto na porta da frente (predict_match --date); register-batch
default p/ fixtures.json. Default do modelo inalterado.
```

## Relacionado
[[Auditoria tecnica (Claude, 2026-06-20)]] · [[Refatoração audit 2026-06-20]] · [[Ensemble]] · [[Forca ofensiva-defensiva]] · [[MODELO_FINAL]] · [[Backtest baseline (resultados)]]
