---
tags: [dev, refatoracao, audit, decisoes]
status: atual
tipo: decisoes
data: 2026-06-20
aliases: ["Refatoração audit 2026-06-20", "D-53..D-59"]
---

# Refatoração pós-auditoria — SCM Analytics (2026-06-20)

Implementa as correções e melhorias da [[Auditoria tecnica (Claude, 2026-06-20)|auditoria de 2026-06-20]] nas quatro frentes pedidas: **correções de bug + consistência**, **faxina**, **refatoração arquitetural** e **melhorias de modelo atrás do portão**. Princípio mantido: nada entra em λ/dr (mudando o modelo validado) sem passar o portão — por isso as melhorias de modelo entram **atrás de flags, OFF por padrão**.

> **Verificação.** O sandbox **não roda o pytest nem o pipeline completo** (FS do mount corrompe `.py` recém-escritos — quirk D-16; e o `features_pit` de 49k jogos estoura o tempo). Verifiquei a **lógica** com harness próprio (resultados abaixo) e o **grafo de imports** estaticamente. **Rode `python -m pytest -q` na sua máquina** após o pull — ver §Comandos.

---

## Decisões (D-53 … D-59)

### D-53 — Desfalque de ataque: canal δ_ata multiplicativo (corrige audit N-A) 🟡→✅
**Problema:** o ataque desfalcado era roteado pelo **canal de GD** (`gd_alt`), que é **soma-zero em λ** — logo **SUBIA o λ do adversário** quando um atacante do mandante saía, o oposto do que o contrato manda ("ATAQUE fora → corta λ próprio, NÃO infla o rival").
**Correção:** novo canal `δ_ata` **multiplicativo** em `predictor.lambdas` (`λ_T·(1−δ_ata_T)`, contrato §8 passo 6). `desfalques.match_deltas` agora devolve `(dr_delta, datk_home, datk_away)`; `predict_match` passa `datk_a/datk_b` a `predict`. **Default `datk=0` → modelo inalterado** (sem regressão).
**Arquivos:** `predictor.py` (`lambdas`/`predict` ganham `datk_a/datk_b`), `desfalques.py`, `predict_match.py`, `web.py`, `templates/index.html` (explicador), `tests/test_desfalques.py` (asserts novos).
**[verificado]** atacante-chave do mandante fora: `λ_A 1,850→1,388 (−25%)`; **`λ_B do rival 0,950→0,950` (não sobe)**. Antes subia p/ 1,075.

### D-54 — Consistência (audit N-B, N-C, N-E)
- **N-C:** `from typing import Optional` em `altitude.py` (era usado em `confederation_of` sem import — bug latente mascarado por `from __future__ import annotations`).
- **N-E:** comentário do `k_factor` corrigido — K=50 vale p/ TODAS as fases continentais (é o que o contrato §3.1 manda; o martj42 não codifica fase). Era "finais continentais 50".
- **N-B:** `build_draw_curve(..., before_date=)` permite construir a curva de empate **só com o treino** (PIT honesto); caveat **declarado** no código (a `DRAW_CURVE` congelada é in-sample — vazamento de 2ª ordem na componente P(E)).

### D-55 — Faxina (audit P-I, P-J, P-K, N-D)
- **`db.session(path)`** — context manager que **fecha sempre** (mesmo em erro). Aplicado nas 3 rotas de `web.py` (eram `connect/.../close`, vazavam em exceção).
- **N-D:** `factors.seed_team_altitudes(conn)` popula `teams.home_altitude_m` (coluna existia no schema e **nunca era preenchida**); CLI `python -m scm.altitude --seed-db`.
- **P-J/P-K:** `requirements.txt` ganha instrução de **lock exato** (`pip freeze`); `TECH_STACK` corrigido ("faixas com teto de major", não "pinadas"); contagem de testes no `README` do pacote atualizada (25 arquivos/128 casos).

### D-56 — Arquitetura: `factors.py` + `config.py` + schema-alvo (audit acoplamento, P-H)
- **`scm/factors.py` (novo):** termos PUROS de λ/dr (altitude `gd_alt` + tabelas + `confederation_of` + `seed_team_altitudes`). **Quebra o ciclo `predictor↔altitude`**: `predictor` agora importa `gd_alt` de `factors` (sem o "import tardio"); `altitude.py` ficou só com os **portões** e **reexporta** os nomes puros (compatibilidade: `from .altitude import gd_alt` segue funcionando). `predict_match`/`simulate` também passam a importar de `factors` (não puxam mais o `backtest_harness` por transitividade).
- **`scm/config.py` (novo):** **fonte única** dos coeficientes escalares fora de dataclass (`THETA_ALT`, `SIGMA_R_REF`, `SIGMA_AJUSTE_DEFAULT` já importam daqui) + espelho documentado dos defaults das dataclasses, p/ calibração coordenada. Módulo-folha (sem imports de `scm`).
- **P-H:** tabelas `venues` e `context` adicionadas ao `db.SCHEMA` (ADITIVO, `IF NOT EXISTS`) — aproxima o schema-alvo do design sem migração.
- **[verificado]** grafo de imports **acíclico**; `config` é folha; `factors→config`; `predictor→factors`; `altitude→{factors,predictor,backtest_harness}`. Sem referências órfãs (grep de `THETA_ALT`/`SIGMA_R_REF`/`gd_desf`).

### D-57 — Forma saturante de GD (candidato P-D, OFF) 🔵
`PredictParams.gd_form ∈ {"linear" (default), "sat"}`; `"sat"` usa `GD_max·tanh(dr/escala)` (`gd_max=3,0`, `gd_scale=667`). Resolve o `λ_B<0` no tail. Portão: **`python -m scm.calibrate_form`** (ΔBrier sat vs linear, IC). **Default linear → modelo inalterado.**
**[verificado]** `λ_B`: linear vira negativo (−0,275 em dr=900); saturante fica positiva (0,44); inclinação em 0 casa a linear (0,0045/Elo).

### D-58 — Adoção de σ-Glicko atrás do portão de banda (candidato P-B, OFF) 🔵
`features_pit.run(..., use_glicko=True)` / CLI `--glicko` usa o **RD de Glicko-1 PIT** (`sigma_glicko.run_pit`) como base de σ_R, em vez de `sigma_r(n)·vol_mult` (que satura ~40). Adoção exige o portão de cobertura de banda: **`python -m scm.sigma_glicko --gate`** (medição anterior: a banda atual **sobre-cobre** ~92%; avaliar com cuidado). **Default OFF.**

### D-59 — Recalibração do favorito por faixa (candidato P-C, OFF) 🔵
`scm/calibrate_binned.py`: ajusta só a prob do **top pick por faixa de p_max** (isotônica do treino), mantendo soma 1 — **diferente** da recalibração GLOBAL já rejeitada (D-40). Alvo: a superconfiança medida em [0,8–0,9]. Portão: **`python -m scm.calibrate_binned --major`**.
**[verificado]** soma 1; preserva a classe top; puxa o favorito superconfiante p/ baixo.

---

## Comandos (rodar na sua máquina, após o pull)

```bash
cd scm_analytics
rm -rf scm/__pycache__ tests/__pycache__        # limpa bytecode antigo (quirk do sandbox)
pip install -r requirements.txt
python -m pytest -q                              # suíte (deve passar; test_desfalques atualizado)

# rebuild do pipeline (a base não muda de resultado; as flags abaixo são OPCIONAIS)
python -m scm.ingest && python -m scm.elo_engine && python -m scm.features_pit && python -m scm.predictor
python -m scm.altitude --seed-db                # popula teams.home_altitude_m (N-D)

# PORTÕES dos candidatos (decidem adoção; nada entra sem IC>0):
python -m scm.calibrate_form --major            # D-57 forma saturante (P-D)
python -m scm.sigma_glicko --gate               # D-58 σ-Glicko (P-B)
python -m scm.calibrate_binned --major          # D-59 recal por faixa (P-C)
```

**Mensagem de commit sugerida:**
```
refactor(audit 2026-06-20): corrige N-A (desfalque-ataque não infla rival),
quebra ciclo predictor↔altitude (factors.py), config.py único, schema venues/context,
db.session, candidatos atrás do portão (forma saturante, σ-Glicko, recal por faixa).
Default do modelo inalterado; portões a rodar na máquina.
```

## Relacionado
[[Auditoria tecnica (Claude, 2026-06-20)]] · [[Decisoes tecnicas]] · [[MODELO_FINAL]] · [[camada1-apendice-formas-v5]] · [[Backtest baseline (resultados)]]
