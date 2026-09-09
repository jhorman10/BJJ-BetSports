# sport-selector-ui Specification

## Purpose

Add a sport toggle to the LeagueSelector component, manage sport state in `useUIStore`, and ensure the league/country lists filter by the selected sport. Enables users to switch between soccer, tennis, baseball, and basketball views.

## Requirements

### Requirement: Sport constant type in frontend

A `Sport` string union type and `SPORTS` constant array MUST exist in `frontend/src/config/constants.ts`. The type MUST include `"soccer"`, `"tennis"`, `"baseball"`, `"basketball"`. A `DEFAULT_SPORT` constant MUST equal `"soccer"`.

#### Scenario: Sport type defines all values

- GIVEN `Sport` type imported in frontend code
- WHEN TypeScript compiles
- THEN only the four sport values are assignable to `Sport`

#### Scenario: SPORTS array usable for iteration

- GIVEN `SPORTS` constant
- WHEN iterated in a UI component
- THEN it returns exactly the four sport values with display labels

### Requirement: Selected sport in useUIStore

`useUIStore` MUST expose a `selectedSport: Sport` state field (default `"soccer"`) and a `setSport(sport: Sport)` action. The store MUST persist the selected sport to `localStorage` and restore it on page load.

#### Scenario: Default sport on fresh load

- GIVEN a user opens the app for the first time
- WHEN `useUIStore` initializes
- THEN `selectedSport` is `"soccer"`

#### Scenario: Sport persists across reload

- GIVEN a user selects `sport: "tennis"`
- WHEN the page is reloaded
- THEN `selectedSport` is restored as `"tennis"` from localStorage

#### Scenario: setSport updates state

- GIVEN `selectedSport` is `"soccer"`
- WHEN `setSport("baseball")` is called
- THEN `selectedSport` becomes `"baseball"`
- AND localStorage is updated

### Requirement: Sport toggle in LeagueSelector

`LeagueSelector` MUST render a row of sport toggle chips/buttons above the existing country/league selectors. The toggle MUST call `setSport` from `useUIStore`. The active sport MUST be visually distinguished.

#### Scenario: Toggle renders all sports

- GIVEN `LeagueSelector` mounted
- WHEN the component renders
- THEN four sport chips are visible: Soccer, Tennis, Baseball, Basketball

#### Scenario: Toggle changes sport

- GIVEN sport toggle with Soccer active
- WHEN user clicks Tennis chip
- THEN `selectedSport` becomes `"tennis"`
- AND country/league lists update to show tennis leagues

#### Scenario: Active chip highlighted

- GIVEN `selectedSport` is `"baseball"`
- WHEN LeagueSelector renders
- THEN the Baseball chip has an active/selected visual state

### Requirement: League list filtered by sport

The country selector and league selector MUST display only leagues matching `selectedSport`. When sport changes, the country list MUST recompute to show only countries with leagues in that sport.

#### Scenario: Country list updates on sport change

- GIVEN selected sport is `"soccer"` showing 211 countries
- WHEN user switches to `"tennis"`
- THEN country list shows only countries with tennis leagues

#### Scenario: League list scoped to country + sport

- GIVEN selected country is `"US"` and sport is `"baseball"`
- WHEN league list renders
- THEN only US baseball leagues are shown

### Requirement: Sport field on frontend League type

The `League` TypeScript interface in `frontend/src/domain/entities/` MUST include `sport: string`. The field MUST be populated from API responses.

#### Scenario: League type includes sport

- GIVEN an API response with `sport: "basketball"` on a league
- WHEN the frontend deserializes it
- THEN `league.sport` equals `"basketball"`
