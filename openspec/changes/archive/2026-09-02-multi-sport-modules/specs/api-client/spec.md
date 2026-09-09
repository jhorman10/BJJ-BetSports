# Delta for api-client

## ADDED Requirements

### Requirement: Sport parameter on API fetch functions

`getLeagues` and `getActiveLeagues` in `frontend/src/infrastructure/api/leagues.ts` MUST accept an optional `sport?: string` parameter. When provided, the function MUST append `?sport={sport}` to the request URL. When omitted, the request MUST behave identically to the current implementation (no sport param, backend defaults to soccer).

#### Scenario: Fetch leagues with sport

- GIVEN `getActiveLeagues("tennis")` is called
- WHEN the HTTP request is issued
- THEN the URL includes `?sport=tennis`

#### Scenario: Fetch leagues without sport

- GIVEN `getActiveLeagues()` is called without arguments
- WHEN the HTTP request is issued
- THEN no `?sport=` param is appended
- AND the response contains soccer leagues (backward compatible)

#### Scenario: All sports return valid data

- GIVEN `getActiveLeagues("baseball")` is called
- WHEN the response is returned
- THEN leagues have `sport: "baseball"` in their data

### Requirement: Sport in API_ENDPOINTS

`API_ENDPOINTS` in `frontend/src/config/constants.ts` MUST include a comment or type annotation indicating that league endpoints support `?sport=` as a query parameter. No path changes are required since `sport` is a query param, not a path segment.

#### Scenario: Endpoints unchanged

- GIVEN `API_ENDPOINTS.LEAGUES` and `API_ENDPOINTS.LEAGUES_ACTIVE`
- WHEN inspected
- THEN path values are unchanged (no `/sport/` segment)
- AND sport filtering is done via query parameter
