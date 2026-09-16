# Spec: baseball-data-source

## Purpose

Fetches and parses historical MLB game data from Retrosheet CSV files. Provides team-level and pitcher-level statistics for feature extraction. Mirrors `TennisDataSource` pattern with CSV parsing instead of API calls.

## Requirements

### Requirement: Retrosheet CSV fetching

`RetrosheetDataSource` MUST fetch game data from Retrosheet's free CSV files. Files MUST be downloaded from `https://www.retrosheet.org/game.htm` or equivalent structured endpoint. The data source MUST handle HTTP errors gracefully and retry with exponential backoff.

#### Scenario: Successful CSV fetch

- GIVEN a request for 2023 season data
- WHEN Retrosheet CSVs are fetched
- THEN game records are returned with all required fields populated
- AND the data covers April through October 2023

#### Scenario: HTTP error handling

- GIVEN Retrosheet returns HTTP 503
- WHEN the data source retries
- THEN it retries up to 3 times with exponential backoff
- AND raises `DataSourceError` after all retries exhausted

### Requirement: Historical data range

The data source MUST support seasons from 2015 to current year. Default training range SHOULD be 2015-2024. Current season data MUST be supplementable via MLB Stats API for freshness.

#### Scenario: Training data range

- GIVEN a request for training data
- WHEN data is fetched for 2015-2024
- THEN all available games in that range are returned
- AND each game includes team and pitcher statistics

#### Scenario: Current season supplement

- GIVEN it is mid-2025 season
- WHEN 2025 data is requested
- THEN Retrosheet data is used for completed games
- AND MLB Stats API provides current-year stats for upcoming games

### Requirement: CSV parsing — 4 file types

The data source MUST parse these Retrosheet CSV formats:

| File | Key Fields | Purpose |
|------|-----------|---------|
| `gameinfo` | date, home_team, away_team, score, venue | Game metadata |
| `teamstats` | team, W, L, RS, RA, ERA, OPS | Team-level stats |
| `batting` | player, team, AB, H, 2B, 3B, HR, BB, K, SB | Batting stats |
| `pitching` | player, team, W, L, ERA, WHIP, IP, K, BB, HR | Pitching stats |

#### Scenario: Parse gameinfo CSV

- GIVEN a gameinfo CSV row: `"20230715,0,NYY,BOS,5,3,Fenway Park,Night"`
- WHEN parsed
- THEN a game record is created with correct date, teams, scores, venue, day_night

#### Scenario: Parse teamstats CSV

- GIVEN a teamstats row with team "NYY", 95 wins, 67 losses
- WHEN parsed
- THEN team stats are available for feature extraction

### Requirement: Team name mapping

Retrosheet uses different abbreviations than MLB Stats API. The data source MUST maintain a mapping table:

| Retrosheet | MLB Stats API | Full Name |
|-----------|---------------|-----------|
| `NYA` | `NYY` | New York Yankees |
| `NYN` | `NYM` | New York Mets |
| `CHN` | `CHC` | Chicago Cubs |
| `CHA` | `CHW` | Chicago White Sox |
| `SLN` | `STL` | St. Louis Cardinals |
| `KCA` | `KC` | Kansas City Royals |
| `ANA` | `LAA` | Los Angeles Angels |
| `SDN` | `SD` | San Diego Padres |
| `SFN` | `SF` | San Francisco Giants |
| `WSN` | `WSH` | Washington Nationals |

#### Scenario: Team name resolution

- GIVEN a Retrosheet record with team "NYA"
- WHEN mapped to MLB Stats API format
- THEN the result is "NYY"

### Requirement: Data caching strategy

Fetched CSV data MUST be cached locally to avoid repeated downloads. Cache SHOULD be stored in `backend/data/cache/retrosheet/`. Cache validity SHOULD be 24 hours for current season, permanent for historical seasons.

#### Scenario: Cache hit for historical season

- GIVEN 2023 data was previously cached
- WHEN 2023 data is requested
- THEN cached data is returned without HTTP request

#### Scenario: Cache miss for current season

- GIVEN current 2025 season data cached 25 hours ago
- WHEN 2025 data is requested
- THEN fresh data is fetched from Retrosheet
- AND cache is updated

### Requirement: Team-level stat aggregation

The data source MUST aggregate per-game data into team-level statistics: season ERA, WHIP, OPS, runs per game, HR per game, bullpen ERA, wins, losses. Aggregations MUST be filterable by date range and home/away splits.

#### Scenario: Team stats for feature extraction

- GIVEN all 2023 games for team "NYY"
- WHEN team stats are aggregated
- THEN season ERA, WHIP, OPS, R/G, HR/G are available
- AND home/away splits are available separately

## Acceptance Criteria

- [ ] Retrosheet CSVs fetched with retry logic
- [ ] All 4 CSV types parsed correctly
- [ ] Team name mapping covers all 30 MLB teams
- [ ] Cache prevents redundant downloads
- [ ] Historical range 2015-current supported
- [ ] Team-level stats aggregated for feature extraction
