---
tags: [projeto, operacao, copa, runbook]
status: atual
tipo: runbook
data: 2026-06-19
aliases: ["Operação da Copa", "Runbook da Copa"]
---

# Operação da Copa 2026 — medir a cada rodada

> **Princípio (fechamento honesto):** o motor está no **teto** com os dados atuais — Dixon-Coles, recalibração, σ-Glicko e σ_dr-scaling foram **todos barrados pelo portão** (ver [[Decisoes tecnicas]] D-39/D-40/D-42/D-47). O ganho agora **não vem de mais fórmula**: vem de **medir** (registro prospectivo) e de **alimentar dados** (desfalques/odds/xG). O código pra isso já está todo no lugar.

Tudo roda local (`cd scm_analytics`). Nomes de seleção no padrão **martj42 (inglês)**: `Brazil`, `Saudi Arabia`, `Cape Verde`…

## Loop de cada rodada

### 1. Antes dos jogos — registrar a previsão (imutável)
1. Copie o template e edite com os jogos da rodada (data real, sede/altitude e mando do anfitrião se houver):
   `cp dados/fixtures.json.example dados/fixtures.json`  → edite.
2. *(Opcional)* desfalques: `cp dados/desfalques.json.example dados/desfalques.json` → edite (lesões/suspensões por jogo).
3. *(Opcional)* odds de mercado: `cp dados/odds.csv.example dados/odds.csv` → edite e ingira:
   `python -m scm.odds ingest dados/odds.csv`
4. **Registre a rodada** (puxa desfalques + odds automaticamente):
   `python -m scm.registrar register-batch dados/fixtures.json`
   - registro é **imutável**: rodar de novo não duplica.

### 2. Depois dos jogos — preencher e medir
5. Atualize o snapshot de resultados (na sua máquina, requer rede):
   `python -m scm.ingest --download && python -m scm.ingest`
6. Preencha os resultados automaticamente pelo snapshot:
   `python -m scm.registrar settle-from-db`
7. Veja o **Brier prospectivo real** acumulado:
   `python -m scm.registrar report`

### 3. Ver os insights
- `python -m scm.web` → `/` (prever jogo, com explicador do `dr` + mercado), `/simulacao` (probabilidades), `/bracket` (chaveamento).
- Reconstruir após novos resultados: `python -m scm.elo_engine && python -m scm.features_pit && python -m scm.predictor`.

## Alimentar dados (onde a precisão cresce)
| Dado | Como | Efeito | Status |
|---|---|---|---|
| **Desfalques** | `dados/desfalques.json` (setor/tier por jogo) | corta λ do ataque / mexe no dr (D-41) | **ativo** quando preenchido |
| **Odds** | `python -m scm.odds ingest dados/odds.csv` | 3ª perna do ensemble, peso 0,20 (D-44) | **ativo** quando há odds |
| **xG (StatsBomb)** | `python -m scm.xg ingest dados/xg.csv` | prior de estilo (`team_xg`) | **esqueleto/OFF** — só entra em λ após o **portão** (D-50) |

## Lembretes
- **Probabilidade, nunca certeza.** O bracket é *uma* história; o número rigoroso é o Monte Carlo (`/simulacao`).
- Validação real = **Brier prospectivo** (passo 7), não o histórico.
- Rodar `python -m pytest -q` após cada `git pull`.

## Relacionado
[[Como rodar o sistema]] · [[MODELO_FINAL]] · [[Decisoes tecnicas]] · [[Registro de previsoes]] · [[BACKLOG]]

---

## ▶ Operar e medir a Copa — runbook + placar (2026-06-21)

**O ponto:** backtest bom ≠ previsor provado. O juiz real é o **Brier da Copa medido jogo a jogo**.
Comando novo (repetível, a cada rodada):
```
python -m scm.report --copa     # Brier do modelo na Copa 2026 vs uniforme (IC) e vs mercado
```

**Medição REAL até agora (36 jogos disputados, v0.4):**
- Brier modelo **0,5868** vs uniforme **0,6667** — melhor na média (+0,080), mas **IC95 [-0,067, +0,219] CRUZA ZERO**.
- vs mercado (12 jogos com odds): modelo **0,640** vs mercado **0,566** (mercado à frente).
- **Leitura honesta:** com 36 jogos **ainda não dá para afirmar** que bate nem o uniforme nesta Copa
  (o backtest de 2.253 jogos dizia que sim — mas 1 torneio é ruído). O IC fecha conforme a Copa
  avança. É exatamente o "desconhecido" que só a operação revela.

**Loop por rodada (na sua máquina):**
1. **ANTES dos jogos:** registre a rodada (Prospectivo → "Registrar rodada" / "Registrar um jogo")
   e, se tiver, ingira as odds de fechamento (`dados/odds_copa_disputados.csv` → `scm.odds ingest`).
2. **DEPOIS dos jogos:** botão **"Atualizar tudo"** (baixa placares) → Prospectivo → **"Buscar
   resultados"** (settle) → veja o Brier do registro; e rode **`python -m scm.report --copa`** +
   **`python -m scm.odds bench --major`** p/ o placar modelo vs mercado.
3. **Critério:** o modelo "se prova" quando, com a Copa avançada, o ganho vs uniforme tiver **IC>0**
   e o gap pro mercado encolher. Até lá: probabilidade, não certeza.
