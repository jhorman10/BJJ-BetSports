# sport-catalog Specification

## Purpose

Sport-aware dataset schema, loader indexing, and league catalog with a sport dimension. Extends the football-only platform to carry a `sport` field through dataset, loader, domain, and persistence layers.

## Requirements

### Requirement: Sport field on league entries

`leagues_global.json` MUST include a `sport` string field on every league entry within each continent/country/league hierarchy. The field MUST be one of the values defined in the Sport enum (`"soccer"`, `"tennis"`, `"baseball"`, `"basketball"`). All 850 existing football leagues MUST receive `sport: "soccer"`.

#### Scenario: Existing leagues carry soccer sport

- GIVEN `leagues_global.json` loaded
- WHEN any existing league entry is inspected
- THEN it contains `"sport": "soccer"`

#### Scenario: New sport placeholder sections

- GIVEN `leagues_global.json` loaded
- WHEN the `tennis`, `baseball`, or `basketball` top-level keys are accessed
- THEN each contains at least one placeholder league with `sport` set to its respective value
- AND placeholder leagues have `active: false`

### Requirement: Sport enum in domain constants

A `Sport` enum or string union type MUST exist in `backend/src/domain/constants.py` defining all supported sport values: `"soccer"`, `"tennis"`, `"baseball"`, `"basketball"`. The enum MUST be importable by loaders, repositories, and API routers.

#### Scenario: Sport enum values

- GIVEN the domain constants module
- WHEN `Sport` is imported
- THEN it exposes exactly `SOCCER`, `TENNIS`, `BASEBALL`, `BASKETBALL`

#### Scenario: Default sport constant

- GIVEN the domain constants module
- WHEN `DEFAULT_SPORT` is referenced
- THEN it equals `"soccer"`

### Requirement: Sport-aware loader indexing

`LeagueDataset` MUST build an additional index keyed by `sport`. The loader MUST expose a `get_by_sport(sport: str)` method that returns all leagues for that sport. Existing indices (`by_id`, `by_country`, `by_confederation`) MUST remain unchanged.

#### Scenario: Query leagues by sport

- GIVEN `LeagueDataset` loaded with multi-sport data
- WHEN `get_by_sport("tennis")` is called
- THEN only leagues with `sport: "tennis"` are returned

#### Scenario: Query soccer leagues

- GIVEN `LeagueDataset` loaded
- WHEN `get_by_sport("soccer")` is called
- THEN all 850 existing football leagues are returned

#### Scenario: Unknown sport returns empty

- GIVEN `LeagueDataset` loaded
- WHEN `get_by_sport("cricket")` is called
- THEN an empty list is returned

### Requirement: Sport field on domain League entity

The `League` entity in `backend/src/domain/entities/entities.py` MUST include a `sport: str` field with a default value of `"soccer"`. The field MUST be serialized when the entity is converted to dict/JSON.

#### Scenario: Default sport on League

- GIVEN a `League` constructed without explicit sport
- WHEN `league.sport` is accessed
- THEN it equals `"soccer"`

### Requirement: Sport field on prediction documents

MongoDB prediction documents MUST carry a `sport` string field at the document root, defaulting to `"soccer"` via `doc.get("sport", "soccer")` in all repository mappers. Existing documents without the field MUST be read as soccer.

#### Scenario: New document includes sport

- GIVEN a new prediction document written to MongoDB
- WHEN the document is read back
- THEN it contains `"sport"` at the root level

#### Scenario: Legacy document defaults to soccer

- GIVEN an existing prediction document without a `sport` field
- WHEN `mongo_repository.py` reads it
- THEN the mapper resolves `sport` as `"soccer"`
