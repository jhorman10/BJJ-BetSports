# Spec: baseball-entity

## Purpose

Defines the `BaseballGame` dataclass — the core domain entity representing a single MLB game. Mirrors the `TennisMatch` pattern with team-sport additions: venue, day/night flag, and probable pitcher slots.

## Requirements

### Requirement: BaseballGame dataclass structure

`BaseballGame` MUST be a Python dataclass (or Pydantic model) with all fields typed. Fields MUST include team identifiers, scores, metadata, and pitcher slots. The entity MUST serialize to/from dict and MongoDB document format.

#### Scenario: Construct from Retrosheet data

- GIVEN raw Retrosheet game row with home/away team IDs and scores
- WHEN `BaseballGame` is constructed
- THEN `home_team`, `away_team`, `home_score`, `away_score` are populated
- AND `venue`, `date`, `day_night` are populated from metadata
- AND `home_pitcher_id`, `away_pitcher_id` are populated when available

#### Scenario: Serialize to dict

- GIVEN a `BaseballGame` instance
- WHEN `.to_dict()` or equivalent is called
- THEN all fields serialize to JSON-compatible types
- AND `date` is ISO 8601 formatted string

### Requirement: Required fields

The following fields MUST be present on every `BaseballGame` instance (non-nullable):

| Field | Type | Description |
|-------|------|-------------|
| `game_id` | `str` | Unique identifier (Retrosheet or MLB Stats API) |
| `date` | `str` | Game date ISO 8601 |
| `home_team` | `str` | Home team abbreviation (e.g., "NYY") |
| `away_team` | `str` | Away team abbreviation |
| `home_score` | `int` | Home team final runs |
| `away_score` | `int` | Away team final runs |
| `venue` | `str` | Ballpark name |
| `day_night` | `str` | "day" or "night" |

#### Scenario: Missing required field raises error

- GIVEN a partial game record missing `home_team`
- WHEN `BaseballGame` is constructed
- THEN a validation error is raised

### Requirement: Optional fields

The following fields MAY be present (nullable):

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `home_pitcher_id` | `str \| None` | `None` | Probable/starter pitcher ID |
| `away_pitcher_id` | `str \| None` | `None` | Probable/starter pitcher ID |
| `home_pitcher_name` | `str \| None` | `None` | Pitcher display name |
| `away_pitcher_name` | `str \| None` | `None` | Pitcher display name |
| `season` | `int` | derived from date | MLB season year |
| `series_id` | `str \| None` | `None` | Grouping key for multi-game series |

#### Scenario: Game without confirmed pitchers

- GIVEN a `BaseballGame` with `home_pitcher_id=None`
- WHEN the game is used for prediction
- THEN the prediction service flags "unconfirmed starter" in response
- AND degrades gracefully using team-level pitching stats

### Requirement: Field validation rules

- `home_score` and `away_score` MUST be >= 0
- `day_night` MUST be one of `"day"`, `"night"`
- `date` MUST parse as valid ISO 8601
- `home_team` and `away_team` MUST be different
- `season` MUST be between 2000 and current year + 1

#### Scenario: Invalid score rejected

- GIVEN a game record with `home_score = -1`
- WHEN `BaseballGame` is constructed
- THEN a validation error is raised

#### Scenario: Same team home and away rejected

- GIVEN `home_team="NYY"` and `away_team="NYY"`
- WHEN `BaseballGame` is constructed
- THEN a validation error is raised

## Acceptance Criteria

- [ ] `BaseballGame` dataclass exists with all required fields typed
- [ ] Optional fields default to `None` or derived values
- [ ] `.to_dict()` produces JSON-serializable output
- [ ] Validation rejects invalid scores, dates, and same-team matchups
- [ ] Entity mirrors `TennisMatch` structural pattern
