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
SIM_SIGMA_MODE = "per_game"  # incerteza no torneio: "per_game" (atual) ou "per_team" (correlacionada, P-S/D-74) — trocar SÓ se o portão (scm.calibrate_simvar) der IC>0
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


# --- Overrides em runtime (página "Experimentos" da web) ---------------------------------
# SÓ flags de SIMULAÇÃO entram aqui: recalculam na hora e NÃO tocam em `predictions`/
# MODEL_VERSION. Flags de MODELO (xG, estilo, etc.) ficam de fora de propósito — mudá-los
# exige rebuild + nova versão (senão a produção diverge do backtest validado). Persistência
# em dados/config_overrides.json (sobrevive a reinícios do servidor).
import json as _json
from pathlib import Path as _Path

_OVERRIDABLE = ("SIM_SIGMA_MODE", "SIM_AD_BLEND")
_OVR_PATH = _Path(__file__).resolve().parent.parent / "dados" / "config_overrides.json"


def _coerce(key, value):
    """Valida/normaliza o valor de um flag ativável (recusa lixo silenciosamente lá em cima)."""
    if key == "SIM_SIGMA_MODE":
        if value not in ("per_game", "per_team"):
            raise ValueError("SIM_SIGMA_MODE deve ser 'per_game' ou 'per_team'")
        return value
    if key == "SIM_AD_BLEND":
        v = float(value)
        if not (0.0 <= v <= 1.0):
            raise ValueError("SIM_AD_BLEND deve estar em [0, 1]")
        return v
    raise ValueError(f"flag '{key}' não é ativável pela web")


def _read_overrides() -> dict:
    try:
        d = _json.loads(_OVR_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {}
    out = {}
    for k in _OVERRIDABLE:
        if k in d:
            try:
                out[k] = _coerce(k, d[k])
            except ValueError:
                pass
    return out


def current_overrides() -> dict:
    """Valores efetivos dos flags ativáveis (já com override aplicado)."""
    return {k: globals().get(k) for k in _OVERRIDABLE}


def set_override(key: str, value):
    """Aplica AO VIVO (a próxima simulação já usa) e persiste no JSON. Recusa flag de modelo."""
    if key not in _OVERRIDABLE:
        raise ValueError(f"flag '{key}' não é ativável pela web (só {_OVERRIDABLE})")
    value = _coerce(key, value)
    globals()[key] = value
    cur = {}
    try:
        cur = _json.loads(_OVR_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        cur = {}
    cur[key] = value
    _OVR_PATH.parent.mkdir(parents=True, exist_ok=True)
    _OVR_PATH.write_text(_json.dumps(cur, ensure_ascii=False, indent=1), encoding="utf-8")
    return value


globals().update(_read_overrides())   # aplica overrides salvos no import
