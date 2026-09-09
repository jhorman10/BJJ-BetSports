# Spec: baseball-feature-extractor

## Purpose

Extracts 46 numeric features from `BaseballGame` + historical data for model input. Features are grouped into 7 categories: pitcher matchup, team batting, bullpen/pitching, recent form, head-to-head, context, and betting odds.

## Requirements

### Requirement: Feature extraction produces 46-element vector

`BaseballFeatureExtractor.extract(game, historical_data)` MUST return a dict or numpy array of exactly 46 numeric features. Every feature MUST be a `float`. No NaN or inf values — missing data MUST be handled via defaults.

#### Scenario: Complete data extraction

- GIVEN a `BaseballGame` with confirmed pitchers and full historical data
- WHEN `extract()` is called
- THEN the result contains exactly 46 features
- AND all values are finite floats

#### Scenario: Missing pitcher data degrades gracefully

- GIVEN a `BaseballGame` with `home_pitcher_id=None`
- WHEN `extract()` is called
- THEN pitcher matchup features use team-level pitching averages as fallback
- AND the result still contains exactly 46 features

### Requirement: Pitcher matchup features (8)

| # | Feature | Formula / Source |
|---|---------|-----------------|
| 1 | `home_era` | Home starter ERA (season) |
| 2 | `away_era` | Away starter ERA (season) |
| 3 | `home_whip` | Home starter WHIP |
| 4 | `away_whip` | Away starter WHIP |
| 5 | `home_k_per_9` | Home starter K/9 |
| 6 | `away_k_per_9` | Away starter K/9 |
| 7 | `home_fip_proxy` | `3 + (13*HR + 3*(BB+HBP) - 2*K) / IP` |
| 8 | `away_fip_proxy` | Same formula for away starter |

#### Scenario: FIP proxy calculation

- GIVEN home starter with 200 IP, 20 HR, 60 BB, 180 K
- WHEN FIP proxy is computed
- THEN result ≈ `3 + (13*20 + 3*60 - 2*180) / 200 = 3.7`

### Requirement: Team batting features (10)

| # | Feature | Formula / Source |
|---|---------|-----------------|
| 9 | `home_ops` | On-base + Slugging (season) |
| 10 | `away_ops` | Away team OPS |
| 11 | `home_woba_proxy` | Weighted OBA approximation: `(0.69*BB + 0.72*H + 0.89*2B + 1.27*3B + 1.62*HR) / (AB + BB + SF + HBP)` |
| 12 | `away_woba_proxy` | Away team wOBA proxy |
| 13 | `home_r_per_game` | Home team runs per game |
| 14 | `away_r_per_game` | Away team runs per game |
| 15 | `home_hr_per_game` | Home team HR per game |
| 16 | `away_hr_per_game` | Away team HR per game |
| 17 | `home_babip` | Batting avg on balls in play |
| 18 | `away_babip` | Away BABIP |

#### Scenario: OPS calculation

- GIVEN home team with .340 OBP and .450 SLG
- WHEN OPS is computed
- THEN `home_ops = 0.790`

### Requirement: Bullpen/pitching features (8)

| # | Feature | Formula / Source |
|---|---------|-----------------|
| 19 | `home_bullpen_era` | Home bullpen ERA (season) |
| 20 | `away_bullpen_era` | Away bullpen ERA |
| 21 | `home_bullpen_whip` | Home bullpen WHIP |
| 22 | `away_bullpen_whip` | Away bullpen WHIP |
| 23 | `home_saves` | Home team saves |
| 24 | `away_saves` | Away team saves |
| 25 | `home_team_era` | Home team overall ERA |
| 26 | `away_team_era` | Away team overall ERA |

### Requirement: Recent form features (6)

| # | Feature | Formula / Source |
|---|---------|-----------------|
| 27 | `home_last10_win_pct` | Home W% in last 10 games |
| 28 | `away_last10_win_pct` | Away W% in last 10 games |
| 29 | `home_run_diff_avg` | Avg run differential last 10 |
| 30 | `away_run_diff_avg` | Avg run differential last 10 |
| 31 | `home_streak` | Current win/loss streak (positive=wins) |
| 32 | `away_streak` | Current streak |

### Requirement: Head-to-head features (3)

| # | Feature | Formula / Source |
|---|---------|-----------------|
| 33 | `h2h_season` | Home win% vs away this season |
| 34 | `h2h_overall` | Home win% vs away all-time |
| 35 | `h2h_home_away` | Home team win% when hosting this opponent |

#### Scenario: No H2H history

- GIVEN two teams with no head-to-head games this season
- WHEN H2H features are computed
- THEN `h2h_season = 0.5` (neutral default)
- AND `h2h_overall` and `h2h_home_away` use available history or default to 0.5

### Requirement: Context features (8)

| # | Feature | Formula / Source |
|---|---------|-----------------|
| 36 | `is_home` | 1.0 (home team perspective always 1) |
| 37 | `day_night` | 1.0 for night, 0.0 for day |
| 38 | `month` | Month as float (4.0=April ... 10.0=October) |
| 39 | `is_division` | 1.0 if same division, 0.0 otherwise |
| 40 | `ballpark_factor` | Park run factor (lookup table) |
| 41 | `travel_distance` | Distance between team cities (miles, normalized) |
| 42 | `home_rest_days` | Days since home team's last game |
| 43 | `away_rest_days` | Days since away team's last game |

### Requirement: Betting odds features (3)

| # | Feature | Formula / Source |
|---|---------|-----------------|
| 44 | `home_implied_prob` | `1 / decimal_odds_home` |
| 45 | `away_implied_prob` | `1 / decimal_odds_away` |
| 46 | `odds_diff` | `home_implied_prob - away_implied_prob` |

#### Scenario: Odds features with no odds available

- GIVEN a game with no betting odds provided
- WHEN odds features are computed
- THEN all three odds features default to 0.0
- AND a flag is set indicating odds were unavailable

### Requirement: Missing data handling

Every feature MUST have a defined default when source data is unavailable:

| Category | Default | Rationale |
|----------|---------|-----------|
| Pitcher stats | Team-level average | Most common missing case |
| Batting stats | League average | Rare missing |
| Bullpen stats | League average | Rare missing |
| Form stats | 0.5 / 0.0 | Neutral |
| H2H stats | 0.5 | Neutral |
| Context stats | Computed or 0.0 | Depends on field |
| Odds | 0.0 | Explicit fallback |

#### Scenario: All pitcher data missing

- GIVEN historical data with no pitcher records for either starter
- WHEN features are extracted
- THEN pitcher features use team-level ERA/WHIP averages
- AND no NaN or inf values in output

### Requirement: Feature normalization

Extracted features MUST be normalized using Min-Max scaling or Z-score normalization (consistent with tennis module approach). The extractor SHOULD accept a pre-fitted scaler for inference and expose `fit()` for training.

#### Scenario: Scaler fitted during training

- GIVEN training data with 46 features across 10,000 games
- WHEN `extractor.fit(training_games)` is called
- THEN scaler parameters are computed and stored

#### Scenario: Scaler applied during prediction

- GIVEN a fitted scaler and a new game
- WHEN `extractor.extract(game, scaler=fitted_scaler)` is called
- THEN features are normalized using stored parameters
- AND output values are in expected range (typically [-3, 3] for Z-score)

## Acceptance Criteria

- [ ] 46 features extracted, all finite floats
- [ ] Every feature has a formula/source documented
- [ ] Missing data defaults defined per category
- [ ] No NaN or inf in output under any data condition
- [ ] FIP proxy formula matches specification
- [ ] Scaler fits and transforms consistently
