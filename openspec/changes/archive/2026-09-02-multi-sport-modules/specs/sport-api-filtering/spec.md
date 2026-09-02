# sport-api-filtering Specification

## Purpose

Add `?sport=` query parameter to league and prediction endpoints, and include `sport` in API response schemas. Enables clients to filter league catalogs and predictions by sport.

## Requirements

### Requirement: Sport query parameter on league endpoints

`GET /api/v1/leagues` and `GET /api/v1/leagues/active` MUST accept an optional `sport` query parameter (`str`, default `"soccer"`). The parameter MUST filter the response to leagues matching the given sport value.

#### Scenario: Default sport filter

- GIVEN a client calls `GET /api/v1/leagues/active` without `?sport=`
- WHEN the response is returned
- THEN only leagues with `sport: "soccer"` are included

#### Scenario: Explicit sport filter

- GIVEN a client calls `GET /api/v1/leagues/active?sport=tennis`
- WHEN the response is returned
- THEN only leagues with `sport: "tennis"` are included

#### Scenario: Invalid sport returns empty

- GIVEN a client calls `GET /api/v1/leagues?sport=cricket`
- WHEN the response is returned
- THEN `leagues` is an empty array
- AND status is 200

### Requirement: Sport query parameter on prediction endpoints

`GET /api/v1/predictions/league/{league_id}` MUST accept an optional `sport` query parameter. When provided, the endpoint MUST verify the league belongs to the specified sport. League metadata resolution MUST use sport context.

#### Scenario: Prediction with sport context

- GIVEN predictions exist for league `B_MLB` with `sport: "baseball"`
- WHEN a client calls `GET /api/v1/predictions/league/B_MLB?sport=baseball`
- THEN predictions are returned with league metadata resolved

#### Scenario: Sport mismatch returns empty

- GIVEN predictions exist for league `B_MLB` with `sport: "baseball"`
- WHEN a client calls `GET /api/v1/predictions/league/B_MLB?sport=soccer`
- THEN the response is empty or returns a 404/400

### Requirement: Sport field on LeagueModel schema

`LeagueModel` in `backend/src/api/schemas/leagues.py` MUST include a `sport: str` field. `LeaguesResponse` MUST include `sport` in its structure. The field MUST be populated from the league dataset or MongoDB document.

#### Scenario: LeagueModel includes sport

- GIVEN a league with `sport: "baseball"`
- WHEN the API serializes it via `LeagueModel`
- THEN `sport` is present and equals `"baseball"`

#### Scenario: LeaguesResponse groups by sport

- GIVEN leagues from multiple sports
- WHEN `LeaguesResponse` is returned
- THEN each league entry includes its `sport` field

### Requirement: Backward-compatible endpoint signatures

All new query parameters MUST be optional with safe defaults. Existing clients calling endpoints without `sport` MUST receive identical responses to the current behavior (soccer-only leagues).

#### Scenario: No-param call unchanged

- GIVEN an existing client that calls `GET /api/v1/leagues` without `?sport=`
- WHEN the endpoint is updated
- THEN the response shape and content are identical to the pre-change response
