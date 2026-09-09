# Delta for api-client

## ADDED Requirements

### Requirement: Best combination endpoint constant and typed client method

`API_ENDPOINTS` in `frontend/src/config/constants.ts` MUST add a `BEST_COMBINATION` entry resolving to `/api/v1/best-combination`. `services/api.ts` MUST export `getBestCombination(pool?: BestCombinationRequest): Promise<BestCombinationResponse>` issuing a POST. New types MUST exist in `frontend/src/types/`: `BestCombinationRequest` (optional `min_probability?: number`, `exclude_leagues?: string[]`), `BestCombinationLeg`, and `BestCombinationResponse` (4 legs + aggregate), aligned field-for-field with the backend DTO.

#### Scenario: Endpoint constant resolves

- GIVEN the constants file after the change
- WHEN `API_ENDPOINTS.BEST_COMBINATION` is read
- THEN it equals `/api/v1/best-combination`

#### Scenario: Typed client method posts

- GIVEN `getBestCombination` called with `{ min_probability: 0.5 }`
- WHEN the request is issued
- THEN it POSTs to the endpoint with the filter body
- AND resolves to a typed `BestCombinationResponse`

#### Scenario: Type alignment with backend

- GIVEN the frontend `BestCombinationLeg` and `BestCombinationResponse` types
- WHEN compared against the backend best-combination DTO
- THEN every backend response field has a matching frontend field of the same type