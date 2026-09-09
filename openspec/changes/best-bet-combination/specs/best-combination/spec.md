# best-combination Specification

## Purpose

Server-side "ask the model" endpoint. Aggregates soccer, tennis, baseball, and basketball pick pools; selects the single best high-confidence leg per sport; returns one 4-leg combination with combined probability/odds/EV, stake guidance, and explicit warnings. Independence is assumed and documented as an upper bound.

## Requirements

### Requirement: Unified pick DTO

Every pick emitted by the four sport services MUST carry `sport` and `match_id`. Soccer `SuggestedPick` and tennis/baseball/basketball `markets[]` MUST both include the fields. The aggregator MUST consume only unified picks; candidates lacking `sport` or `match_id` MUST be excluded from pools.

#### Scenario: All sports expose unified picks

- GIVEN upcoming events exist in all four sports
- WHEN each sport service emits picks
- THEN every pick carries `sport` and `match_id`

#### Scenario: Pick lacking match_id excluded

- GIVEN a tennis market without `match_id`
- WHEN the aggregator builds the tennis pool
- THEN that market is excluded

### Requirement: POST /api/v1/best-combination

The system MUST expose `POST /api/v1/best-combination`. The request body MAY include optional pool filters: `min_probability` (float, 0 < p < 1) and `exclude_leagues` (string array). All fields MUST pass schema validation; invalid values MUST return 422. The response MUST contain exactly one combination: `legs` (4 entries, one per sport) plus `aggregate`.

| Response field | Contract |
|---|---|
| legs[].sport / match_id / match_label / pick_label | identity |
| legs[].probability / odds | numeric |
| legs[].odds_source | `market` \| `fair` |
| legs[].confidence_level / is_recommended | quality trace |
| legs[].confidence_warning / odds_warning | booleans |
| aggregate.total_probability / total_odds / expected_value | computed |
| stake.risk_level / stake.suggested_stake_pct / stake.kelly_fraction | stake sizing (separate object — see ADR-6) |
| independence_disclaimer | top-level string — see ADR-6 |

#### Scenario: Request with filters

- GIVEN `{"min_probability": 0.5}`
- WHEN the endpoint is called
- THEN each leg probability is ≥ 0.5
- AND the response contains one combination

> **Relaxation (accepted deviation, ADR-6):** `min_probability` filters ONLY the
> high-confidence quality pool. When a sport's quality pool is empty after
> filtering, the fallback pool (best-available pick) is NOT threshold-filtered —
> coverage policy keeps the 4-leg scope. A fallback leg MAY have a probability
> below the requested threshold; it always carries `confidence_warning: true`.

#### Scenario: Invalid filter rejected

- GIVEN `min_probability: 1.5`
- WHEN the endpoint is called
- THEN 422 with structured error

### Requirement: Quality filter per sport pool

A sport's candidate pool MUST contain only high-confidence ML-confirmed picks: soccer legs require `is_ml_confirmed`/`is_ia_confirmed` true; tennis/baseball/basketball legs require `confidence_level == "high"` and `is_recommended` true. Low-confidence or unconfirmed picks MUST NOT be candidates.

#### Scenario: Qualifying pick enters pool

- GIVEN a soccer pick with `is_ml_confirmed` true
- WHEN the soccer pool is built
- THEN the pick is a candidate

#### Scenario: Low-confidence pick filtered

- GIVEN a basketball market with `confidence_level: "medium"`
- WHEN the basketball pool is built
- THEN the market is excluded

### Requirement: Single best combination selection

The system MUST return exactly one combination. Each sport's leg MUST be the candidate with the highest `priority_score`, tie-broken by highest probability. Legs MUST span all four sports; no sport MAY repeat.

#### Scenario: Happy path — best combo

- GIVEN each sport has at least one qualifying pick
- WHEN the endpoint is called
- THEN `legs` has exactly 4 entries, one per sport

#### Scenario: Highest-priority leg chosen

- GIVEN soccer candidates A (priority 0.8) and B (0.6)
- WHEN the combination is built
- THEN the soccer leg is A

### Requirement: Missing high-confidence sport policy

If a sport's qualifying pool is empty, the system MUST include that sport's best available pick (highest priority, else highest probability) and MUST set `confidence_warning: true` and `is_recommended: false` on that leg. The 4-leg scope MUST be preserved.

#### Scenario: Sport lacks high-confidence picks

- GIVEN tennis has no high-confidence market
- WHEN the endpoint is called
- THEN the tennis leg is the best available market
- AND `confidence_warning` is true
- AND legs still total 4

### Requirement: Odds fallback

A leg MUST use bookmaker odds when present (`odds_source: market`). Without odds, the system MUST use fair odds `1/probability`, set `odds_source: fair`, and set `odds_warning: true`.

#### Scenario: Missing market odds

- GIVEN a soccer leg without bookmaker odds
- WHEN combination math runs
- THEN leg odds equal `1/probability`
- AND `odds_source` is `fair`

### Requirement: Combination math and EV

`total_probability` MUST equal the product of the four leg probabilities. `total_odds` MUST be the product of leg market odds when all legs have market odds; otherwise it MUST equal `1/total_probability` with aggregate `odds_warning: true`. `expected_value` MUST equal `total_probability × total_odds − 1`. A negative-EV combination MUST NOT be returned; the endpoint MUST respond 409 with `error: no_positive_ev`. The response MUST include `independence_disclaimer` stating legs are assumed independent and the probability is an upper bound.

#### Scenario: EV from combined odds

- GIVEN legs p=[0.6, 0.5, 0.55, 0.5] and market odds [1.8, 2.0, 1.9, 2.1]
- WHEN aggregates are computed
- THEN `total_probability` is 0.0825 and EV = 0.0825 × (1.8×2.0×1.9×2.1) − 1
- AND `independence_disclaimer` is non-empty

#### Scenario: Negative EV refused

- GIVEN combined market odds imply EV < 0
- WHEN the endpoint is called
- THEN 409 with `error: no_positive_ev`

### Requirement: Stake guidance

The system MUST compute `suggested_stake_pct` as fractional Kelly on combined probability versus combined odds, capped by RiskManager exposure limits (`max_stake_pct`, daily exposure, per-league exposure). `risk_level` MUST be reported.

#### Scenario: Kelly capped by exposure

- GIVEN the Kelly value exceeds `max_stake_pct`
- WHEN stake guidance is computed
- THEN `suggested_stake_pct` equals the cap

### Requirement: Insufficient-data errors

If fewer than four sports have any pick at all, the system MUST respond 409 with `error: insufficient_pool` plus `missing_sports` (sports without picks). If no sport has picks, the system MUST respond 409 with `error: no_picks_available`. All errors MUST use structured `{error, detail}` and MUST NOT leak internal data.

#### Scenario: One sport has no events

- GIVEN basketball has no upcoming matches
- WHEN the endpoint is called
- THEN 409 with `missing_sports` containing "basketball"

#### Scenario: No picks at all

- GIVEN all four sports have no pick data
- WHEN the endpoint is called
- THEN 409 with `error: no_picks_available`