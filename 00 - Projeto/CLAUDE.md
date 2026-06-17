---
tags: [projeto, contexto, onboarding]
status: atual
tipo: contexto
data: 2026-06-15
aliases: ["Contexto do projeto", "Onboarding"]
---

# CLAUDE.md — contexto do projeto (leia isto primeiro)

## Objetivo (3 linhas)
Sistema **local e gratuito** que prevê partidas da Copa 2026 entregando **probabilidades V/E/D, gols esperados e confiança** — nunca certezas.
Motor matemático auditável (Elo → Poisson → ensemble), validado por **backtest histórico** antes de qualquer uso.
**Não é ferramenta de aposta**; Brier ~0.60 não é vantagem.

## Estado atual
**Planejamento (congelado):** contrato matemático **v5.0** ([[camada1-planejamento-v5]]), auditado ([[camada1-revisao-v5]]) e autocontido ([[camada1-apendice-formas-v5]]); design do backtest ([[camada2-planejamento-v1]]); plano de build ([[camada2-baseline-plano-v1]]); 9 execuções manuais ([[06 - Analises]]); registro imutável ([[Registro de previsoes]]).
**Código (Camada 2):** **baseline COMPLETO — 6/6 módulos** (`ingest`, `elo_engine`, `features_pit`, `predictor`, `backtest_harness`, `report`), **42 testes**, pipeline E2E rodando — ver [[Codigo (estrutura)]].
**✅ Baseline VALIDADO** (torneios n=2241 Brier 0,562 bate uniforme com IC; ECE 0,023). Modelo atual: **`baseline-v0.2-altitude`**. **Portão C2.5 (decididos):** altitude (E1) **✅ adotada** (+0,049, D-18) · calor (E3) **✗** (D-19) · calibração de coeficientes **✗** (D-17). Candidatos restantes **opcionais**: bola parada (E4, StatsBomb) e descanso (E6, σ). Ver [[Backtest baseline (resultados)]].

## Decisões tomadas (resumo — detalhe em [[Decisoes tecnicas]])
- Contrato congelado v5.0; mudar fórmula = nova versão.
- **Sem ML/bayes hierárquico** (auditabilidade/overfit). **Custo R$ 0, roda local.**
- **Portão de backtest:** nada entra em λ/dr sem IC que não cruza zero.
- **Baseline primeiro** (Elo+mando+σ_R→Poisson), depois fatores ambientais atrás do portão.
- Stack: Python + NumPy/pandas + SQLite + pytest ([[TECH_STACK]]).

## Restrições não negociáveis
1. **Zero custo** — sem APIs/bases/hospedagem pagas.
2. **Roda local** — nada lê a internet no cálculo (snapshot em disco).
3. **Probabilidades, nunca certezas** — inclusive sobre o próprio modelo.
4. **Registro pré-jogo imutável** — nunca reescrever linha gravada ([[Registro de previsoes]]).
5. **Não inventar dados/fontes** — lacunas declaradas ficam declaradas.

## Mapa das notas-chave
- Visão: [[Indice]] · este [[CLAUDE]] · [[MODELO_FINAL]] · [[TECH_STACK]] · [[BACKLOG]] · [[Plugins recomendados]]
- Contrato: [[camada1-planejamento-v5]] · [[camada1-apendice-formas-v5]] · [[camada1-revisao-v5]]
- Modelos: [[Elo]] · [[Poisson]] · [[Incerteza e propagacao]] · [[Ensemble]] · [[Mando de campo]] · [[Ajustes ambientais]] · [[Confianca]]
- Execução: [[camada2-planejamento-v1]] · [[camada2-baseline-plano-v1]] · [[Decisoes tecnicas]]
- Dados: [[Fontes gratuitas]] · [[Esquema SQLite]] · [[Registro de previsoes]]

## Como rodar e testar
Código em `scm_analytics/` (ver [[Codigo (estrutura)]]). Pipeline `ingest → elo_engine → features_pit → predictor` funcionando:
```
cd scm_analytics
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m scm.ingest --download     # baixa snapshot martj42 (1x, na sua máquina)
python -m scm.ingest                # -> dados/scm.sqlite (offline)
python -m scm.elo_engine            # reconstrói o Elo
python -m scm.features_pit          # features point-in-time
python -m scm.predictor             # previsões -> tabela predictions
python -m pytest -q                 # 62 testes
```
**Prever um jogo específico** (porta da frente — usa o Elo atual):
```
python -m scm.predict_match "Brazil" "Argentina"               # sede neutra
python -m scm.predict_match "Mexico" "Germany" --city "Mexico City"   # altitude
python -m scm.predict_match "United States" "England" --mando 40      # anfitrião 2026
```
**Interface gráfica** (local, no navegador):
```
pip install -r requirements.txt   # inclui flask
python -m scm.web                 # abre http://127.0.0.1:5000
```
Nomes em inglês (padrão martj42); se errar, ele sugere. Detalhe: [[Codigo (estrutura)]].

## ▶ Estado: CONSOLIDADO
**C2.5 fechado** nos fatores de bom custo-benefício. Modelo atual e recomendado: **`baseline-v0.2-altitude`** (validado + altitude). **Sem tarefa ativa.** Futuro **opcional** (retorno decrescente): bola parada (E4, StatsBomb), descanso (E6, σ), xG/Dixon-Coles, afinação de pesos. Para **previsões de 2026**: rodar o pipeline e **registrar antes do kickoff** ([[Registro de previsoes]], imutável).

## 🔄 Retomada rápida (para um novo chat / após perda de contexto)
Se você é um agente novo pegando o projeto, faça nesta ordem:
1. Leia: este `CLAUDE.md` → [[Indice]] → [[BACKLOG]] (estado dos cards) → [[Codigo (estrutura)]] (status dos módulos).
2. **Estado em 1 linha:** **CONSOLIDADO** em `baseline-v0.2-altitude` — baseline validado (torneios Brier 0,562 bate uniforme com IC) + altitude adotada; calor/calibração barrados pelo portão; **62 testes**; tags `v1.0`/`v1.1` no GitHub.
3. **Valide o ambiente:** `cd scm_analytics && pip install -r requirements.txt && python -m pytest -q` → esperar **62 passed**. Se uma edição `.py` não refletir, `rm -rf scm/__pycache__ tests/__pycache__` (quirk do sandbox).
4. **Próxima tarefa:** seção acima (**C2.5**).
5. **Regras de trabalho:** atualizar a documentação a cada etapa; escrever código de sistema pelo executor (bash) e rodar pytest; nada pago; probabilidades, nunca certezas. Detalhe em [[Decisoes tecnicas]].

## Git / GitHub
O versionamento roda **na máquina do usuário** — o sandbox não mantém `.git` na pasta montada (o FS do mount corrompe o config do git; ver [[Decisoes tecnicas]] D-14). `.gitignore` (raiz) já cobre cache, `.venv`, `*.sqlite`, snapshots e o workspace volátil do Obsidian.

**Setup inicial (1x, no PC, dentro da pasta do vault):**
```
git init -b main
git add -A
git commit -m "Projeto Copa 2026: vault + baseline Camada 2"
```
Criar o repo no GitHub e publicar **pelo terminal** com a GitHub CLI (`gh`):
```
gh auth login                                               # 1x, autentica via navegador
gh repo create <repo> --private --source=. --remote=origin --push
```
Sem `gh`: crie um repo **vazio** em github.com/new e rode `git remote add origin <URL>` + `git push -u origin main`.

**Sincronizar a cada etapa de código:**
```
git add -A && git commit -m "<mensagem>" && git push
```
O agente mantém o projeto **commit-ready** e fornece a **mensagem de commit** ao fim de cada etapa; o `push` é executado pelo usuário (auth própria, persistente).
