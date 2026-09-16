# Spec: baseball-fixture-source

## Purpose

Fetches upcoming MLB games and probable pitchers from the MLB Stats API (free, no auth required). Provides the live fixture data that feeds into predictions. Mirrors `TennisFixtureSource` pattern.

## Requirements

### Requirement: MLB Stats API integration

`MLBFixtureSource` MUST fetch upcoming games from the MLB Stats API (`statsapi.mlb.com`). The API provides schedule, probable pitchers, and game metadata. No authentication is required.

#### Scenario: Fetch today's games

- GIVEN a request for today's MLB schedule
- WHEN `get_upcoming_games()` is called
- THEN all games scheduled for today are returned
- AND each game includes home/away teams and game time

#### Scenario: API rate limiting

- GIVEN 5 rapid consecutive requests to MLB Stats API
- WHEN requests are made
- THEN a 100ms delay is applied between requests
- AND no HTTP 429 errors occur

### Requirement: Upcoming games fetching

The fixture source MUST provide games for configurable lookahead (default: 7 days). It MUST support filtering by date range, team, and league.

#### Scenario: 7-day lookahead

- GIVEN default configuration
- WHEN `get_upcoming_games()` is called
- THEN games for today through 7 days ahead are returned

#### Scenario: Team-specific lookup

- GIVEN a request for New York Yankees upcoming games
- WHEN `get_upcoming_games(team="NYY")` is called
- THEN only Yankees games are returned

### Requirement: Probable pitcher resolution

The fixture source MUST resolve probable pitchers for each game. When a pitcher is not yet announced, the field MUST be `null` with a flag indicating unconfirmed status.

#### Scenario: Probable pitchers confirmed

- GIVEN a game 3 days from now with both pitchers announced
- WHEN fixture data is fetched
- THEN `home_pitcher_id` and `away_pitcher_id` are populated
- AND pitcher names are available

#### Scenario: Probable pitchers unconfirmed

- GIVEN a game tomorrow with only home pitcher announced
- WHEN fixture data is fetched
- THEN `home_pitcher_id` is populated
- AND `away_pitcher_id` is `null`
- AND `away_pitcher_confirmed = false`

### Requirement: Game series grouping

The fixture source MUST group games into series (e.g., 3-game series between same teams). Series grouping enables the prediction endpoint to return series-level analysis.

#### Scenario: 3-game series detected

- GIVEN NYY vs BOS playing July 15, 16, 17
- WHEN fixtures are fetched
- THEN all 3 games share the same `series_id`
- AND the series metadata includes game count and current standings

### Requirement: Demo fallback data

When the MLB Stats API is unavailable (off-season, network issues), the fixture source MUST return demo/fallback data for development and testing. Demo data SHOULD include realistic-looking games with plausible matchups.

#### Scenario: API unavailable returns demo data

- GIVEN MLB Stats API returns HTTP 500
- WHEN `get_upcoming_games()` is called
- THEN demo games are returned
- AND each demo game has realistic team matchups
- AND a `"demo": true` flag is set in the response

#### Scenario: Off-season demo mode

- GIVEN it is November (MLB off-season)
- WHEN `get_upcoming_games()` is called
- THEN demo games for next season are returned
- AND a `"demo": true` flag is set

### Requirement: Current season stats supplement

For upcoming games, the fixture source SHOULD fetch current-season stats for both teams from the MLB Stats API. This supplements Retrosheet data with the most recent performance metrics.

#### Scenario: Current stats for upcoming game

- GIVEN an upcoming game between NYY and BOS
- WHEN fixture data is enriched
- THEN current 2025 season stats for both teams are included
- AND stats are more recent than cached Retrosheet data

## Acceptance Criteria

- [ ] MLB Stats API integration works without authentication
- [ ] Probable pitchers resolved or flagged as unconfirmed
- [ ] Series grouping identifies multi-game matchups
- [ ] Demo fallback data available when API is down
- [ ] Rate limiting prevents API throttling
- [ ] Current-season stats supplement historical data
