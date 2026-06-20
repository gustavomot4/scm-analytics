---
tags: [dev, evolucao, modelo, decisoes, nivel2]
status: atual
tipo: decisoes
data: 2026-06-20
aliases: ["Evolução Nível 2", "D-63..D-65"]
---

# Evolução Nível 2 — recência no Elo, mando, benchmark (2026-06-20)

Implementa o **Nível 2** da [[Auditoria tecnica (Claude, 2026-06-20)|auditoria]]: (#4) recência/reversão no Elo, (#5) mando empírico + anfitrião, (#6) benchmark mais forte. Dois dos três são **medições/diagnósticos** que *confirmam* o que já existe — e isso é resultado, não fracasso: a disciplina do portão **rejeitou** a reversão (como rejeitou calor/estilo/DC). Verifiquei tudo reconstruindo a base do `results.csv` no sandbox.

> O grande insight do Nível 2: **o modelo já está no "teto de informação do dr"** (#6) — ou seja, mais ajuste no núcleo não ajuda (reversão piora, #4; mando já bem calibrado, #5). O caminho para mais acurácia é **informação além do dr**, que é exatamente o que a perna ataque/defesa do Nível 1 entrega.

---

## D-63 — Recência/reversão à média no Elo (P-M): TESTADA e REJEITADA 🔴

**Hipótese (auditoria):** o Elo nunca regride (Colômbia>Brasil; valores ~70–210 acima do eloratings) — reverter à média daria recência e corrigiria a inflação.

**Implementação:** `EloParams.revert_half_life_months` (default **0 = OFF**): antes de cada jogo, `R ← init + (R−init)·0.5^(meses_parado/half_life)` (PIT, em `elo_engine._revert`). Portão reproduzível: `scm/calibrate_recency.py`.

**Resultado [verificado] (torneios n=2.249):** a reversão **PIORA** o Brier em todos os half-lives:

| half-life | Brier | ΔBrier (rev−base) | veredito |
|---:|---:|---:|---|
| base (OFF) | 0,5617 | — | — |
| 24 m | 0,5844 | **−0,0226** IC[−0,0297,−0,0154] | rejeita |
| 48 m | 0,5764 | −0,0147 IC[−0,0201,−0,0091] | rejeita |
| 96 m | 0,5702 | −0,0085 IC[−0,0123,−0,0044] | rejeita |
| 144 m | 0,5675 | −0,0058 IC[−0,0088,−0,0026] | rejeita |

**Conclusão:** a inflação ABSOLUTA do Elo é **cosmética** (afeta o display vs eloratings, não o `dr` RELATIVO que prevê). Reverter joga fora sinal real. **Mantido OFF.** Fica como capacidade re-testável (`EloParams.revert_half_life_months`) + portão (`calibrate_recency`).

## D-64 — Mando empírico medido + sensibilidade do anfitrião (P-E) ✅ (confirma o contrato)

**`scm/calibrate_homeadv.py`** mede a vantagem de casa nos jogos não-neutros (grid de H pós-hoc, ratings fixos, por Brier).

**Resultado [verificado] (n=36.350):** taxa real de pontos do mandante **0,622** vs E[we] do modelo (com +100) **0,613** → o mando está **levemente subestimado**. Grid: **H ótimo ≈ 110** (Brier 0,5338), com **100 praticamente empatado** (0,5342). Confirma o D-47 e que o **`h_hist=100` do contrato é bem escolhido** (conservador por ~10 Elo, diferença de Brier ínfima).

**Bônus do anfitrião 2026 (`+40`):** continua **juízo declarado**, não validável (não há precedente de Copa em co-sede; a vantagem de casa é majoritariamente árbitro/torcida — jogos-fantasma COVID — que pode não transferir p/ público de Copa mais neutro). Por isso é **menor** que os ~110 medidos e entra em **banda/σ**. O módulo mostra a sensibilidade: `python -m scm.calibrate_homeadv --host "Mexico" --away "Germany" --city "Mexico City"` imprime V/E/D e avanço a mando 0/20/40/60.

## D-65 — Benchmark mais forte: teto não-paramétrico do `dr` (#6) ✅

**`backtest_harness.evaluate_vs_lookup`** compara o modelo contra o **melhor previsor possível que usa só o `dr`**: as frequências empíricas de V/E/D por faixa de `dr` (lookup, com Laplace). Aparece no `python -m scm.backtest_harness --major`.

**Resultado [verificado] (torneios):** modelo **0,5617** vs lookup **0,5618** → **EMPATA** (ganho +0,00005, IC[−0,0024,+0,0026]). **O modelo já extrai ~todo o sinal do `dr`** — a forma paramétrica não deixa nada na mesa. Diagnóstico-chave: para melhorar, é preciso **informação além do dr** (a perna ataque/defesa do Nível 1, que bate este teto porque usa os GOLS, não o dr).

*Comparador EXTERNO (Opta/FiveThirtyEight) como teto: exige captura manual das previsões públicas (sem fonte histórica gratuita estruturada + nada lê a internet no cálculo) → **lacuna declarada**, fora do custo-zero/local. O `evaluate_vs_lookup` é o teto interno mais forte disponível.*

---

## Síntese do Nível 2

Os três itens **confirmam que o núcleo Elo→Poisson está bem ajustado**: reversão piora (#4), o mando 100 é ~ótimo (#5), e o modelo está no teto de informação do dr (#6). Isso **não** é retorno nulo — é a evidência que faltava de que o caminho certo é **dado novo**, validando a prioridade do Nível 1 (perna AD) e dos próximos (odds, desfalques reais, xG). "Pare de ajustar o núcleo; traga informação nova" — agora medido.

## Comandos (na sua máquina, após o pull)

```bash
cd scm_analytics && rm -rf scm/__pycache__ tests/__pycache__ && python -m pytest -q
python -m scm.backtest_harness --major        # agora mostra tb. o TETO (lookup)
python -m scm.calibrate_homeadv               # vantagem de casa empírica (~110; 100 ok)
python -m scm.calibrate_recency               # reversão: REJEITADA (piora o Brier)
```

**Mensagem de commit sugerida:**
```
feat(validação): benchmark do teto não-paramétrico do dr (evaluate_vs_lookup) — modelo
empata (já no teto do dr); mando empírico medido (~110, confirma h_hist=100, calibrate_homeadv);
reversão à média no Elo testada e REJEITADA (piora Brier, calibrate_recency, OFF). Núcleo
inalterado.
```

## Relacionado
[[Auditoria tecnica (Claude, 2026-06-20)]] · [[Evolução Nível 1]] · [[Refatoração audit 2026-06-20]] · [[Elo]] · [[Mando de campo]] · [[Backtest baseline (resultados)]]
