# Proposal: Baseball Prediction Module

## Change: baseball-prediction

### Intent

Add MLB baseball predictions following the established tennis module pattern. Baseball is the second team sport in the platform — it introduces team-aggregate features (9-player lineups) and pitcher-dependent markets, which tennis does not have.

**Why now**: Pattern is proven from tennis; Retrosheet data is free and historical; MLB Stats API provides live fixtures with no auth.

### Scope — First Slice

- Backend: `BaseballGame` entity, `BaseballFeatureExtractor`, `BaseballPredictionService`, router, DTOs
- Data: Retrosheet CSV ingestion (gameinfo, teamstats, batting, pitching) + MLB Stats API fixture source
- Model: RandomForest classifier (~46 features, 6 markets)
- Frontend: `BaseballPrediction/` directory mirroring tennis components
- API: `POST /baseball/predict`, `GET /baseball/games`, `GET /baseball/series`, `GET /baseball/predictions/{series_id}`
- Training script: `train_baseball_model.py`

### Out of Scope

- Live in-play predictions (pre-game only)
- Player prop bets (strikeouts, hits)
- Historical backtesting dashboard
- Parlay/accumulator logic

### Architecture Mapping

| Tennis | Baseball | Notes |
|--------|----------|-------|
| `TennisMatch` | `BaseballGame` | Adds: venue, day/night, pitcher slots |
| `TennisFeatureExtractor` | `BaseballFeatureExtractor` | 46 features vs ~15 tennis |
| `TennisPredictionService` | `BaseballPredictionService` | 6 markets vs tennis ML |
| `TennisDataSource` | `RetrosheetDataSource` | CSV parsing, no API auth |
| `TennisFixtureSource` | `MLBFixtureSource` | MLB Stats API |
| `tennis_router.py` | `baseball_router.py` | Same CRUD pattern |
| `tennis_dtos.py` | `baseball_dtos.py` | Pydantic models |
| `train_tennis_model.py` | `train_baseball_model.py` | Feature pipeline + training |

### Feature Groups (46 total)

- Pitcher matchup: 8 (ERA, WHIP, K/9, BB/9, HR/9, IP, FIP proxy, recent ERA)
- Team batting: 10 (OPS, wOBA proxy, R/G, HR/G, BB%, K%, BABIP, wRC+ proxy, RISP, slugging)
- Bullpen/pitching: 8 (ERA, WHIP, saves, holds, K/9, HR/9, team ERA, team FIP)
- Recent form: 6 (last10 win%, run differential, streaks)
- Head-to-head: 3 (season, overall, home/away)
- Context: 8 (home field, day/night, month, division, ballpark, travel, rest)
- Betting odds: 3 (home implied prob, away implied prob, odds diff)

### Markets (6)

1. Moneyline — home vs away
2. Run Line (-1.5) — handicap
3. Total Runs O/U — combined (7.5/8.5/9.5)
4. First 5 Innings — pitcher-dependent half-game
5. Team Total Runs — per-team O/U
6. Both Teams Score — yes/no

### Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Starting pitcher not confirmed | Prediction accuracy drops | Flag "unconfirmed starter" in response; degrade gracefully |
| Team sport noise (9 players) | Lower ceiling than tennis | Expected55-60% ML accuracy is normal for baseball |
| MLB season Apr-Oct | No live fixtures off-season | Historical mode only; off-season = model retraining window |
| Retrosheet data freshness | Stats lag behind current season | Supplement with MLB Stats API for current-year stats |

### Rollback

- Remove `baseball_router.py` from app router registration
- Remove `BaseballPrediction/` frontend directory
- Delete `baseball/` from MongoDB collections (TTL auto-cleans)
- No shared code with tennis module — zero blast radius

### Success Criteria

- [ ] `POST /baseball/predict` returns 6 markets for a valid matchup
- [ ] Feature extractor produces46 features from Retrosheet data
- [ ] Model accuracy55% on held-out MLB games
- [ ] Frontend renders predictions matching tennis UX pattern
- [ ] Existing soccer + tennis tests unaffected (0 regressions)
- [ ] Training script completes on historical data without errors

### Estimated Size

- **Files to create**: ~12 (router, service, extractor, DTOs, fixture source, data source, model, training script, frontend components)
- **Files to modify**: 1 (app router registration)
- **Rough line count**: ~600–800 lines total
