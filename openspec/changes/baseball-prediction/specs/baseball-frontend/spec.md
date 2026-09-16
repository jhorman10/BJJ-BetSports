# Spec: baseball-frontend

## Purpose

Frontend components for displaying baseball predictions. Mirrors the tennis prediction UI pattern with baseball-specific market displays. Located in `client/src/components/BaseballPrediction/`.

## Requirements

### Requirement: Component hierarchy

The baseball prediction frontend MUST follow this component structure:

```
BaseballPrediction/
├── BaseballPredictionsPage.tsx    ← Main page, routing entry
├── BaseballGameCard.tsx           ← Single game card with matchup
├── BaseballMarketsPanel.tsx       ← 6-market display grid
├── BaseballMarketCard.tsx         ← Individual market with probability bars
├── BaseballKeyFactors.tsx         ← Key factors list
├── BaseballSeriesView.tsx         ← Multi-game series display
└── index.ts                       ← Barrel exports
```

#### Scenario: Component tree renders

- GIVEN the BaseballPredictionsPage component
- WHEN it receives game data from the API
- THEN BaseballGameCard renders for each game
- AND BaseballMarketsPanel displays all 6 markets
- AND BaseballKeyFactors shows top factors

### Requirement: Routing integration

Baseball predictions MUST be accessible at `/baseball` route. The route MUST be registered in the main router alongside existing sport routes (`/soccer`, `/tennis`). Navigation MUST appear in the sport selector.

#### Scenario: Navigate to baseball

- GIVEN the user clicks "Baseball" in the sport selector
- WHEN navigation completes
- THEN the URL is `/baseball`
- AND BaseballPredictionsPage renders

#### Scenario: Direct URL access

- GIVEN the user navigates directly to `/baseball`
- WHEN the page loads
- THEN BaseballPredictionsPage renders with upcoming games

### Requirement: Market display — 6 market types

Each market type MUST have a dedicated visual treatment:

| Market | Visual | Primary Display |
|--------|--------|-----------------|
| Moneyline | Two probability bars | Home % vs Away % |
| Run Line | Two probability bars with handicap label | Home -1.5 cover % |
| Total Runs | Threshold selector (7.5/8.5/9.5) | Over % at selected threshold |
| First 5 Innings | Two probability bars | Home lead % vs Away lead % |
| Team Total Runs | Per-team threshold selector | Home O/U at 3.5/4.5/5.5 |
| Both Teams Score | Yes/No toggle | Yes % |

#### Scenario: Moneyline display

- GIVEN a game with home 55% / away 45% moneyline
- WHEN BaseballMarketsPanel renders
- THEN two horizontal bars show 55% (green) and 45% (gray)
- AND the favored team bar is highlighted

#### Scenario: Total Runs threshold switching

- GIVEN a game with Total Runs market
- WHEN the user selects 8.5 threshold
- THEN the probability bar updates to show Over 8.5 probability
- AND the 7.5 and 9.5 options remain selectable

### Requirement: Game card display

`BaseballGameCard` MUST show:
- Team logos/abbreviations with home/away designation
- Game date and time
- Probable pitchers (or "TBD" if unconfirmed)
- Venue
- Quick summary: home win probability from Moneyline

#### Scenario: Game card with confirmed pitchers

- GIVEN a game with both pitchers confirmed
- WHEN BaseballGameCard renders
- THEN pitcher names are displayed under each team
- AND a checkmark or indicator shows confirmation status

#### Scenario: Game card with unconfirmed pitcher

- GIVEN a game with away pitcher unconfirmed
- WHEN BaseballGameCard renders
- THEN "TBD" is shown for the away pitcher
- AND a warning icon indicates unconfirmed status

### Requirement: Value bet indicators

When value bets are detected, they MUST be visually highlighted:
- A badge or icon on the relevant market card
- Color coding: green for strong value (>5% edge), yellow for marginal (2-5%)
- Tooltip showing exact edge percentage

#### Scenario: Strong value bet badge

- GIVEN a prediction with 8% edge on moneyline
- WHEN the market card renders
- THEN a green badge with "Value" label appears
- AND tooltip shows "Edge: 8.0%"

### Requirement: Series view

`BaseballSeriesView` MUST group games by series and show:
- Series header (e.g., "NYY vs BOS — 3 game series")
- Games listed chronologically
- Aggregate series prediction summary

#### Scenario: 3-game series display

- GIVEN a series of 3 games between NYY and BOS
- WHEN BaseballSeriesView renders
- THEN all 3 games appear under one series header
- AND each game shows its individual prediction summary

### Requirement: Loading and error states

- Loading state: skeleton cards matching game card layout
- Error state: friendly message with retry button
- Empty state: "No upcoming games" message when no fixtures available
- Demo mode: banner indicating "Demo Data" when using fallback fixtures

#### Scenario: Loading skeleton

- GIVEN the page is fetching game data
- WHEN BaseballPredictionsPage renders
- THEN skeleton placeholders appear in game card positions

#### Scenario: Demo mode banner

- GIVEN the API returned demo data
- WHEN the page renders
- THEN a banner at the top says "Demo Data — Predictions are for demonstration only"

### Requirement: Responsive design

The frontend MUST be responsive:
- Desktop: 2-column game card grid
- Tablet: 1-column with full-width cards
- Mobile: stacked layout with collapsible market panels

#### Scenario: Mobile layout

- GIVEN a viewport width of 375px
- WHEN BaseballPredictionsPage renders
- THEN game cards stack vertically
- AND market panels are collapsible via accordion

## Acceptance Criteria

- [ ] All 7 components created in `BaseballPrediction/` directory
- [ ] `/baseball` route registered and navigable
- [ ] 6 market types render with correct visualizations
- [ ] Probable pitchers displayed or flagged as TBD
- [ ] Value bet badges appear with correct color coding
- [ ] Series view groups multi-game matchups
- [ ] Loading skeletons and error states implemented
- [ ] Responsive across desktop/tablet/mobile
