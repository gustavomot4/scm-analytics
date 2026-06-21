---
tags: [dev, xg, statsbomb, modelo, turnkey]
status: atual
tipo: guia
data: 2026-06-20
aliases: ["Como usar xG", "xG turnkey", "prior de elenco"]
---

# Como usar o xG (prior de elenco na perna AD) — turnkey

**Por quê:** a comparação com Opta/EA ([[Comparacao com mercado, Opta e EA (2026-06-20)]]) mostrou
que os erros do modelo (Colômbia inflada, Portugal afundado, anfitrião super-rateado) são todos
**cegueira de elenco**. O **xG** é o proxy gratuito/auditável mais próximo de "qualidade de elenco"
e alimenta a **perna ataque/defesa** como *prior* (encolhimento rumo ao xG em vez de rumo a 0).
É a **maior alavanca permitida** pelas regras (R$0, local, sem ML opaco) — e o que mais aproxima do EA.

**Disciplina:** o xG **NÃO entra no modelo sem passar o portão**. Fica OFF por padrão
(`config.USE_XG_PRIOR = False`). Ligar só depois que `--gate-xg` der IC>0.

## Passo a passo (roda tudo na SUA máquina; nada lê a internet no cálculo)

```
# 1) DADOS — clone gratuito do StatsBomb open-data (1x, ~alguns GB)
git clone --depth 1 https://github.com/statsbomb/open-data

# 2) CONSTRUIR o xG por seleção -> team_xg (+ CSV auditável)
python -m scm.xg build /caminho/open-data --csv dados/xg.csv
#   (alternativa manual: monte dados/xg.csv com colunas team,xg_for,xg_against,n_games
#    — médias por jogo, nomes padrão martj42 — e rode: python -m scm.xg ingest dados/xg.csv)

# 3) PORTÃO — o xG ACRESCENTA sobre a perna AD atual? (ΔBrier pareado, IC)
python -m scm.attack_defense --gate-xg
#   -> "ADOTAR xG ✓ (IC>0)"  ou  "NÃO adotar (IC cruza/≤0)"

# 4a) SE PASSOU: liga o prior, reconstrói e versiona
#   - edite scm/config.py:  USE_XG_PRIOR = True
#   - (opcional) bump em scm/predictor.py: MODEL_VERSION = "baseline-v0.5-xg"
rm -rf scm/__pycache__ tests/__pycache__
python -m scm.features_pit && python -m scm.predictor
python -m scm.backtest_harness --major     # confirma o ganho
python -m pytest -q                          # inclui o teste de skill

# 4b) SE NÃO PASSOU: deixe USE_XG_PRIOR=False (o portão rejeitou — honesto). Fim.
```

## O que já está pronto (este commit)
- **Interruptor `config.USE_XG_PRIOR`** (default **False**) — quando True, `predictor.run` e
  `predict_match` passam `attack_defense.xg_priors(conn)` à perna AD. Off = idêntico ao v0.4 (sem risco).
- **Portão `scm.attack_defense --gate-xg`** (`gate_xg_increment`): compara o ensemble com a perna AD
  **com xG** vs **sem xG**, jogo a jogo, IC bootstrap. É o portão certo (mede o **incremento** do xG,
  não "AD vs nada").
- **Construtor `scm.xg build <repo>`**: lê o clone do StatsBomb, soma `shot.statsbomb_xg` por seleção
  (pró/contra) nas competições de seleções masculinas e grava `team_xg` + CSV. *Valide o CSV — o
  layout do StatsBomb pode variar entre versões; se falhar, use o CSV manual.*

## Limitações honestas (declaradas)
- **Cobertura parcial:** o StatsBomb Open Data cobre WC 2018/2022, Euro 2020/2024 e poucas mais —
  **não as 48 seleções nem ao vivo**. Seleções sem xG caem no comportamento atual (encolhe rumo a 0).
  Por isso o portão e a adoção valem sobretudo onde há cobertura; declare a lacuna.
- **Não vira o EA:** o EA usa rating por jogador; o xG é por seleção. Fecha parte do gap, não todo.
- xG ainda é candidato até o `--gate-xg` no SEU dado dizer IC>0. Probabilidade, nunca certeza.

---

## RESULTADO REAL (2026-06-21) — rodei no StatsBomb de verdade

O clone do StatsBomb foi feito e **rodei o pipeline inteiro no dado real** (não sintético):
- **Construtor funcionou:** `scm.xg build` gerou **73 seleções** de 6 competições (WC 2018/2022,
  Euro 2020/2024, Copa América 2024, AFCON 2023). Cobertura da Copa 2026: **37/48** (os 11 sem xG
  são minnows + 1-2 nomes divergentes, ex.: Ivory Coast↔Côte d'Ivoire). xG salvo em `dados/xg.csv`.
- **Portão (`gate_xg_increment`) com xG real:**
  - **Major (torneios), n=2253:** ΔBrier **+0,00022**, IC95 **[+0,00001, +0,00044]** → tecnicamente >0.
  - **Todos, n=49435:** ΔBrier **+0,00002**, IC95 **[−0,00001, +0,00005]** → **cruza zero** (nulo).

**Veredito: NÃO adotar (mantido `USE_XG_PRIOR=False`).** No major passa por um fio, mas é **~6× menor**
que o ganho que o próprio projeto já rejeitou como "praticamente nulo" (D-17, +0,0013), e é **zero no
geral**. É nível de ruído.

**Por que tão pequeno (a parte interessante):**
1. **A perna AD já extrai o sinal de gols.** O xG é gols "suavizados"; sobre uma perna que já é
   ajustada nos gols reais (PIT), ele é **quase redundante**. O ganho marginal confirma isso.
2. **A simulação do título NÃO usa a perna AD/xG.** `simulate` amostra placares de `lambdas(dr)` —
   **Elo puro**. Logo o xG **não toca** os números de campeão; os erros da comparação (Colômbia
   inflada, Portugal afundado) são **do Elo**, e o xG, do jeito que está plugado (só na perna AD do
   ensemble de **1 jogo**), **não os corrige**.

**O que isso ensina (honesto):** a maior alavanca hipotética foi **testada no dado real e barrada
pelo portão**. Para o xG (ou qualquer sinal de elenco) de fato mudar o favoritismo da Copa, ele
precisaria entrar **no λ que a simulação usa** (no `dr`/Elo), não só na perna AD de jogo único — e
isso é uma mudança maior, com portão próprio. O pipeline/dado ficam prontos para esse experimento.
