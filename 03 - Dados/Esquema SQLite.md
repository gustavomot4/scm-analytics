---
tags: [dados, schema, sqlite]
status: atual
tipo: dados
data: 2026-06-15
---

# Esquema SQLite (normalização — design)
Desenho das tabelas (de [[camada2-planejamento-v1]] §2.3). DDL final é tarefa de implementação.

```
teams(team_id, fifa_code, name, confederation, home_altitude_m)
venues(venue_id, name, city, country, lat, lon, elevation_m, covered_bool)
matches(match_id, date_utc, tournament, stage, neutral_bool,
        home_team_id, away_team_id, home_goals, away_goals, kickoff_utc, venue_id)
ratings_pit(team_id, asof_date, elo, sigma_R, n_games_eff)     # point-in-time
form_pit(team_id, asof_date, ppj_pond, desvio_forma)
context(match_id, rest_days_home, rest_days_away, dfuso_home, dfuso_away, wbgt_est)
statsbomb(match_id, team_id, xg, setpiece_goal_share)          # subconjunto coberto
odds_hist(match_id, p_home, p_draw, p_away, source)            # OPCIONAL, 'a validar'
predictions(match_id, versao_modelo, p_v, p_e, p_d, banda_pv_lo, banda_pv_hi,
            lambda_a, lambda_b, sigma_dr, confianca, hash_inputs)
```
`predictions` é a versão estruturada do [[Registro de previsoes]] (CSV).

## Implementado até agora (`scm_analytics/scm/db.py`)
O baseline já cria um **subconjunto** deste design (ver [[Codigo (estrutura)]]):
```
teams(team_id, name, confederation, home_altitude_m)
matches(match_id, date, home_team_id, away_team_id, home_score, away_score,
        tournament, city, country, neutral, natural_key)      -- ingest
ratings_current(team_id, elo, sigma_r, n_games, provisional)   -- elo_engine
match_ratings(match_id, home_elo_pre, away_elo_pre, home_n_pre,
              away_n_pre, dr, we_home)                          -- elo_engine (POINT-IN-TIME)
match_features(match_id, dr_elo, form_home, form_away, dr_adj,
               sigma_r_home, sigma_r_away, sigma_ajuste_home,
               sigma_ajuste_away, sigma_dr, n_home_pre, n_away_pre)  -- features_pit (POINT-IN-TIME)
predictions(match_id, versao_modelo, p_v, p_e, p_d, band_pv_lo, band_pv_hi,
            lambda_a, lambda_b, p_over25, p_btts)                    -- predictor (PK match_id+versao)
meta(key, value)
```
`match_ratings` é o snapshot **pré-jogo** que o `features_pit` (próximo) vai consumir — é como o anti look-ahead fica garantido.

## Relacionado
[[Fontes gratuitas]] · [[Registro de previsoes]] · [[camada2-baseline-plano-v1]] (módulo `in