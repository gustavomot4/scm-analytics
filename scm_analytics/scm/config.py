"""config — fonte ÚNICA e legível dos coeficientes escalares do modelo [a calibrar].

Audit (arquitetura): os coeficientes viviam espalhados — dataclasses por módulo
(`PredictParams`, `EloParams`, `FeatureParams`) MAIS constantes soltas (`THETA_ALT`,
`SIGMA_R_REF`, `DRAW_CURVE`…). Este módulo-FOLHA (não importa nada de `scm`, p/ evitar ciclos)
reúne os números mágicos num só lugar, p/ uma calibração coerente e versionada.

Política: as dataclasses `frozen=True` mantêm seus defaults (imutabilidade em runtime), mas os
valores canônicos são ESTES. Ao recalibrar, mude aqui e propague p/ as dataclasses, e gere uma
nova `versao_modelo` (mudança de fórmula/coeficiente = nova versão, por contrato). Hoje os
escalares fora de dataclass (`THETA_ALT`, `SIGMA_R_REF`, `SIGMA_AJUSTE_DEFAULT`) JÁ importam
daqui; os demais estão espelhados p/ referência da calibração.
"""
from __future__ import annotations

# --- Fatores ambientais ---
THETA_ALT = 0.5              # altitude (E1, McSharry): gol/1000 m [a calibrar fora da CONMEBOL]

# --- Confiança / incerteza (predict_match) ---
SIGMA_R_REF = 200.0          # escala de maturidade do rating p/ a confiança [a calibrar]
SIGMA_AJUSTE_DEFAULT = 40.0  # incerteza de forma/escalação p/ jogo futuro (entra na banda)

# --- Espelho dos defaults das dataclasses (referência p/ calibração coordenada) ---
# predictor.PredictParams:
THETA_GD = 0.45              # GD = θ·dr/100
T_BASE = 2.6                 # T_m = T_base + κ·|dr|/100
KAPPA_TM = 0.10
LAMBDA_MIN = 0.15            # piso de λ (regularização honesta)
W_POISSON = 0.56             # pesos do ensemble sem odds
W_ELO = 0.44
W_AD = 0.50                  # perna ataque/defesa não-Elo — ADOTADA v0.4; afinado por grid+portão (0.30->0.50)
USE_XG_PRIOR = False         # liga o prior de xG na perna AD — SÓ após o portão (gate_xg_increment); muda o modelo -> nova versão
SIM_AD_BLEND = 0.5           # mistura λ da perna AD (gols) no λ da SIMULAÇÃO (0=Elo puro). ADOTADO: portão major +0.0071/all +0.0050 IC>0
EPS_KO = 0.03                # vantagem do + forte no desempate de mata-mata
# elo_engine.EloParams:
H_HIST = 100.0               # mando histórico em jogo não-neutro
SIGMA_FLOOR = 40.0           # σ_R mínimo (muitos jogos)
SIGMA_PROVISIONAL = 200.0    # σ_R de estreante (n=0)
SIGMA_TAU = 20.0             # escala de decaimento de σ_R
# features_pit.FeatureParams:
FORM_SCALE = 60.0            # residual[-1,1] -> Elo
FORM_CAP = 30.0             # cap ±30 Elo (contrato)
SIGMA_AJUSTE_C = 80.0        # σ_ajuste = c·desvio_forma
