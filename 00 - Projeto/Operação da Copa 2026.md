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
