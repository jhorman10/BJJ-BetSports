# Spec: baseball-api

## Purpose

Defines the 4 REST API endpoints for the baseball prediction module. Mirrors the tennis API structure with baseball-specific data shapes. All endpoints are under the `/baseball` prefix.

## Requirements

### Requirement: POST /baseball/predict

Accepts a matchup and returns predictions for all 6 markets.

**Request Schema**:
```json
{
  "home_team": "NYY",
  "away_team": "BOS",
  "date": "2025-07-15",
  "home_pitcher_id": "605288",
  "away_pitcher_id": "605141",
  "odds": {
    "home_decimal": 1.85,
    "away_decimal": 2.10
  }
}
```

**Response Schema**:
```json
{
  "game_id": "baseball_NYY_BOS_20250715",
  "markets": {
    "moneyline": {"home_prob": 0.55, "away_prob": 0.45},
    "run_line": {"home_cover_prob": 0.42, "away_cover_prob": 0.58},
    "total_runs": {"over_7.5": 0.52, "over_8.5": 0.38, "over_9.5": 0.25},
    "first_5_innings": {"home_lead_prob": 0.53, "away_lead_prob": 0.47},
    "team_total_runs": {"home_over_4.5": 0.48, "away_over_4.5": 0.44},
    "both_teams_score": {"yes_prob": 0.82, "no_prob": 0.18}
  },
  "value_bets": [
    {"market": "moneyline", "selection": "home", "edge": 0.05, "confidence": "medium"}
  ],
  "key_factors": [
    {"feature": "home_era", "value": 2.85, "direction": "favor_home"},
    {"feature": "away_bullpen_era", "value": 4.21, "direction": "favor_home"}
  ],
  "confidence": 0.62,
  "unconfirmed_starter": false,
  "model_version": "2025-07-01"
}
```

**Validation Rules**:
- `home_team` and `away_team` are required, must be valid 3-letter MLB abbreviations
- `date` is required, ISO 8601 format
- `odds` is optional; if provided, both `home_decimal` and `away_decimal` must be present
- Pitcher IDs are optional

#### Scenario: Valid prediction request

- GIVEN a request with valid teams and date
- WHEN POST /baseball/predict is called
- THEN 200 OK with all 6 markets returned
- AND key factors are populated

#### Scenario: Invalid team abbreviation

- GIVEN a request with `home_team="INVALID"`
- WHEN POST /baseball/predict is called
- THEN 422 Unprocessable Entity with validation error

#### Scenario: Missing required fields

- GIVEN a request body missing `away_team`
- WHEN POST /baseball/predict is called
- THEN 422 with error listing missing field

### Requirement: GET /baseball/games

Returns upcoming MLB games for prediction.

**Query Parameters**:
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `days` | `int` | `7` | Lookahead in days |
| `team` | `str` | `null` | Filter by team abbreviation |

**Response Schema**:
```json
{
  "games": [
    {
      "game_id": "game_776453",
      "date": "2025-07-15",
      "time": "19:05",
      "home_team": "NYY",
      "away_team": "BOS",
      "venue": "Yankee Stadium",
      "day_night": "night",
      "home_pitcher": {"id": "605288", "name": "Gerrit Cole", "confirmed": true},
      "away_pitcher": {"id": null, "name": null, "confirmed": false}
    }
  ],
  "demo": false
}
```

#### Scenario: Fetch upcoming games

- GIVEN default parameters
- WHEN GET /baseball/games is called
- THEN games for the next 7 days are returned
- AND each game includes probable pitchers with confirmation status

#### Scenario: Team filter

- GIVEN `team=NYY` parameter
- WHEN GET /baseball/games is called
- THEN only Yankees games are returned

### Requirement: GET /baseball/series

Returns grouped series of games between the same teams.

**Query Parameters**:
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `days` | `int` | `14` | Lookahead in days |

**Response Schema**:
```json
{
  "series": [
    {
      "series_id": "NYY_BOS_20250715",
      "home_team": "NYY",
      "away_team": "BOS",
      "games": [
        {"game_id": "g1", "date": "2025-07-15", "home_pitcher_confirmed": true},
        {"game_id": "g2", "date": "2025-07-16", "home_pitcher_confirmed": false},
        {"game_id": "g3", "date": "2025-07-17", "home_pitcher_confirmed": false}
      ],
      "game_count": 3
    }
  ]
}
```

#### Scenario: Series grouping

- GIVEN NYY vs BOS playing 3 consecutive games
- WHEN GET /baseball/series is called
- THEN all 3 games appear under one series entry
- AND `game_count` is 3

### Requirement: GET /baseball/predictions/{series_id}

Returns predictions for all games in a series.

**Response Schema**:
```json
{
  "series_id": "NYY_BOS_20250715",
  "predictions": [
    {
      "game_id": "g1",
      "date": "2025-07-15",
      "markets": { "...same as predict response..." },
      "key_factors": ["..."],
      "unconfirmed_starter": false
    }
  ]
}
```

#### Scenario: Series predictions

- GIVEN a valid series_id with 3 games
- WHEN GET /baseball/predictions/{series_id} is called
- THEN predictions for all 3 games are returned
- AND each prediction follows the same market structure as POST /predict

#### Scenario: Invalid series_id

- GIVEN a series_id that does not exist
- WHEN GET /baseball/predictions/{series_id} is called
- THEN 404 Not Found

### Requirement: Error handling

All endpoints MUST return consistent error responses:

```json
{
  "error": "string",
  "detail": "string (optional)",
  "status_code": 422
}
```

| Status | Meaning |
|--------|---------|
| 400 | Bad request (malformed input) |
| 404 | Resource not found (series_id, game_id) |
| 422 | Validation error (invalid team, missing fields) |
| 500 | Internal server error |

#### Scenario: Validation error response

- GIVEN an invalid request body
- WHEN any endpoint is called
- THEN a 422 response is returned with error and detail fields
- AND the error message identifies the invalid field

### Requirement: Rate limiting considerations

The API SHOULD implement rate limiting to protect the prediction model from abuse. Rate limit SHOULD be 60 requests per minute per client. Rate limit headers SHOULD be included in responses.

#### Scenario: Rate limit exceeded

- GIVEN a client making 61 requests in 1 minute
- WHEN the 61st request arrives
- THEN 429 Too Many Requests is returned
- AND `Retry-After` header indicates wait time

## Acceptance Criteria

- [ ] 4 endpoints implemented with correct HTTP methods
- [ ] Request/response schemas match specifications
- [ ] Validation errors return 422 with descriptive messages
- [ ] Series grouping correctly clusters multi-game matchups
- [ ] Demo mode flag propagated in responses
- [ ] Rate limiting configured at 60 req/min
