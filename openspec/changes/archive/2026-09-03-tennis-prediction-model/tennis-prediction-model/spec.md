# Spec: Tennis Prediction Model

## Change: tennis-prediction-model

### User Stories

**As a** tennis fan/bettor,
**I want** to get tennis match predictions based on mathematical models,
**So** that I can make informed betting decisions on tennis matches.

### Acceptance Criteria / Scenarios

#### T1: Tennis match prediction endpoint
- **Given** a tennis match with players/teams information
- **When** I call `GET /api/v1/predictions/tennis/{match_id}`
- **Then** the response includes prediction probabilities for:
  - Match winner (moneyline)
  - Sets odds (per set)
  - Games total (over/under per set)
- **And** the probabilities sum to 100% per prediction type

#### T2: Sport filter tennis-only
- **Given** I call `GET /api/v1/predictions?sport=tennis`
- **When** the response is returned
- **Then** only tennis predictions are included
- **And** non-tennis predictions are excluded

#### T3: Tennis prediction defaults
- **Given** no `sport` param is provided
- **When** I call `GET /api/v1/predictions`
- **Then** the default sport is "soccer" (backward compatibility)
- **And** tennis predictions require explicit `?sport=tennis`

#### T4: Tennis-specific semantics
- **Given** tennis match prediction payload
- **When** the model generates probabilities
- **Then** there is NO `draw_probability` field (tennis has no draws)
- **And** `set_over_under_probabilities` includes per-set over/under
- **And** `game_probabilities` includes per-game win probabilities

#### T5: Legacy fallback
- **Given** existing prediction documents without `sport` field
- **When** queried without `?sport=tennis`
- **Then** they default to soccer (backward compat)
- **And** tennis-specific fields are absent/ignored

### Edge Cases

- **E1**: Empty match data → return prediction with zero probabilities
- **E2**: Unknown tennis tournament → use tournament-level historical defaults
- **E3**: Women's vs Men's tennis → separate models or tournament-specific adjustments
- **E4**: Live/in-play tennis → different model than pre-match

### Non-Functional Requirements

- **Performance**: Tennis prediction generation ≤ 200ms per match
- **Accuracy**: Model calibrated to historical tennis data (separate from football models)
- **Backward Compatibility**: Existing football prediction models unchanged
- **Type Safety**: TypeScript types for tennis prediction payloads

### Dependencies

- ✅ Multi-sport modules (multi-sport-modules) - completed
- ✅ Sport enum in domain constants - completed
- ✅ `?sport=` query param on prediction endpoints - pending
- ⚠️ Tennis-specific feature extraction / data sources - follow-on
- ⚠️ Tennis prediction model training - follow-on

### Risks & Mitigations

- **R1**: Forcing football model semantics (draw probability, over/under goals) onto tennis is semantically wrong
  - **Mitigation**: Tennis model has no `draw_probability`; use `set_probabilities` and `game_probabilities` instead
- **R2**: Tennis data sources are separate from football - may require new integrations
  - **Mitigation**: Phase 1 is plumbing only; model training is follow-on
- **R3**: Women's and men's tennis have different competitive structures
  - **Mitigation**: Tournament-specific models; separate `tour` field (WTA/ATP)

### Status

**Phase**: Plumbing (endpoint + types + API filter) - follow-on: model training + data sources

### Spec Version

1.0.0