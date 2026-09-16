# Verify Report: best-bet-combination

## Verification Report

**Change**: best-bet-combination
**Version**: spec v1 (best-combination + api-client deltas, amended w/ ADR-6 deviation + W-3 relaxation)
**Mode**: Standard (strict TDD not active per openspec/config.yaml `tdd: false`)
**Date**: 2026-09-08 (re-verify pass 2)
**Evidence base**: real execution (ruff/black/isort/mypy/pytest/tsc/eslint/vitest full runs + solo re-runs/API smoke via FastAPI TestClient against live production fetchers)

### Completeness
| Metric | Value |
|--------|-------|
| Tasks total | 33 |
| Tasks complete | 33 |
| Tasks incomplete | 0 |

### Build & Tests Execution
**Backend**
- `ruff check src/ tests/` → pass
- `black --check src/ tests/` → 199 files unchanged
- `isort --check-only src/ tests/` → clean
- `mypy src --ignore-missing-imports --follow-imports=skip` → success, 149 source files
- `pytest tests/ -q` → **297 passed** (291 + 6 new), pre-existing deprecation warnings only

**Frontend**
- `tsc -b` → clean (exit 0)
- `npm run lint` → 0 errors, 19 warnings
- `npx vitest run` (full) → **82 passed** (79 + 3 new), 21/21 files
  - Run 1 of 2: 79 passed / 3 timeouts in untouched files (TrainingControlPanel + MatchCard, 5000ms test timeouts under first-run parallel load); Run 2 full suite: 82/82; solo re-runs 4/4 + 4/4. Pre-existing timing flake (W-5), cleared by clean re-run, files untouched by this branch.
- Coverage: not configured as a gate for this change

**API smoke (FastAPI TestClient, real app, production fetchers — fresh run)**
- `POST /api/v1/best-combination` `{}` → **200 OK**, shape matches amended DTO exactly:
  - Top-level keys: `['aggregate', 'generated_at', 'independence_disclaimer', 'legs', 'stake', 'warnings']`
  - `legs`: 4 (soccer E0, tennis, baseball MLB, basketball NBA); leg[0] = soccer prob 0.95, odds 1.05 fair (odds_source=fair, odds_warning=True), is_recommended=True, confidence_warning=False, league=E0; all legs carry match_id/league
  - `aggregate` keys: `['expected_value', 'mixed_odds', 'total_odds', 'total_probability']` — risk_level/suggested_stake_pct/disclaimer NOT inside aggregate
  - `aggregate`: total_probability 0.3794, total_odds 2.64 (= 1/0.3794, mixed-odds rule), expected_value 0.0016 (= 0.3794×2.64−1), mixed_odds True
  - `stake` keys: `['kelly_fraction', 'risk_level', 'suggested_stake_pct']` → pct 0.0002, risk 1, kelly 0.0002
  - `independence_disclaimer` top-level, non-empty (Spanish); warnings 5; generated_at present
- `{"min_probability": 1.5}` → 422, `detail` is a LIST (`less_than` msg), matches the array parse path
- `{"exclude_leagues": "E0"}` → 422 (type validation)
- `{"min_probability": 0.9, "exclude_leagues": ["E0"]}` → 409, `detail` is an OBJECT `{error: insufficient_pool, detail, missing_sports: ['soccer']}`, matches the object parse path; no traceback/source-path leak in body

### Spec Compliance Matrix
| Requirement | Scenario | Test | Result |
|-------------|----------|------|--------|
| Unified pick DTO | All sports expose unified picks | Smoke 200 (real legs from all 4 sports carry sport/match_id/league/odds); static picks.py:58-62, tennis_prediction_service.py:705-707, baseball_prediction_service.py:433-435, basketball_prediction_service.py:466-468 | COMPLIANT |
| Unified pick DTO | Pick lacking match_id excluded | `test_drops_picks_missing_match_id` | COMPLIANT |
| POST /best-combination | Request with filters | `test_min_probability_filters_quality_pool`, `test_min_probability_passthrough`, `test_fallback_ignores_min_probability_but_warns` (documented relaxation: fallback may be below threshold, always confidence_warning) | COMPLIANT |
| POST /best-combination | Invalid filter rejected | `test_422_on_invalid_min_probability`, `test_422_on_invalid_exclude_leagues_type` + smoke 422 ×2 | COMPLIANT |
| Quality filter | Qualifying pick enters pool | `test_soccer_requires_ml_or_ia_confirmed` | COMPLIANT |
| Quality filter | Low-confidence pick filtered | `test_other_sports_require_high_and_recommended` | COMPLIANT |
| Single best selection | Happy path | `test_happy_path_four_legs_and_totals`, `test_returns_four_legs`, smoke 200 (4 distinct sports) | COMPLIANT |
| Single best selection | Highest-priority leg chosen | `test_picks_best_by_priority_then_probability`, `test_priority_tie_breaks_by_probability` | COMPLIANT |
| Missing high-confidence policy | Sport lacks high-confidence picks | `test_fallback_when_quality_pool_empty`, `test_fallback_leg_forces_is_recommended_false` (confidence_warning + is_recommended False + 4 legs) | COMPLIANT |
| Odds fallback | Missing market odds | `test_fair_odds_fallback_when_odds_missing` + smoke (soccer fair 1/0.95=1.05; total_odds 2.64 = 1/0.3794) | COMPLIANT |
| Combination math & EV | EV from combined odds | `test_happy_path_four_legs_and_totals` (Πp, Πodds, EV formula); disclaimer asserted in `test_returns_four_legs` + smoke (EV 0.0016) | COMPLIANT |
| Combination math & EV | Negative EV refused | `test_no_positive_ev_when_edge_not_positive`, `test_409_no_positive_ev` | COMPLIANT |
| Stake guidance | Kelly capped by exposure | `test_stake_capped_at_risk_manager_max`, `test_stake_capped_by_league_exposure_when_league_present`, `test_build_combination_applies_league_cap_end_to_end` | COMPLIANT |
| Insufficient-data errors | One sport has no events | `test_insufficient_pool_reports_missing_sports`, `test_409_insufficient_pool`, smoke 409 (missing_sports=[soccer]) | COMPLIANT |
| Insufficient-data errors | No picks at all | `test_no_picks_available_when_all_empty`, `test_409_no_picks_available` | COMPLIANT |

**Compliance summary**: 18/18 scenarios compliant (17 via unit/integration tests, scenario 1 via live smoke + static emission points); 0 UNTESTED, 0 NON-COMPLIANT.

**Response field contract (amended spec table) — spec == implementation == frontend types == live response:**

| Spec field | Implemented (DTO) | Frontend type | Live smoke | Status |
|------------|-------------------|---------------|------------|--------|
| legs[].sport / match_id / match_label / pick_label (+ league) | best_combination_dtos.py:33-37 | bestCombination.ts:15-20 | legs.* | ✅ |
| legs[].probability / odds | :38-39 | :21-22 | ✅ | ✅ |
| legs[].odds_source market\|fair | :40 Literal | :23 | fair observed | ✅ |
| legs[].confidence_level / is_recommended | :41-42 | :24-25 | ✅ | ✅ |
| legs[].confidence_warning / odds_warning | :44-45 | :27-28 | ✅ | ✅ |
| aggregate.total_probability / total_odds / expected_value (+ mixed_odds) | :51-54 | :31-36 | 0.3794 / 2.64 / 0.0016 / True | ✅ |
| stake.risk_level / stake.suggested_stake_pct / stake.kelly_fraction (separate object, ADR-6) | :57-62 | :38-42 | pct 0.0002 / risk 1 / kelly 0.0002; NOT in aggregate | ✅ |
| independence_disclaimer (top-level, ADR-6) | :72 | :49 | top-level, non-empty; NOT in aggregate | ✅ |

**Specs/api-client/spec.md**

| Scenario | Test / Evidence | Result |
|----------|-----------------|--------|
| Endpoint constant resolves | constants.ts:60 `BEST_COMBINATION: "/api/v1/best-combination"`; api.test.ts asserts POST to constant; smoke hit path → 200 | COMPLIANT |
| Typed client method posts | api.test.ts (3 tests: filter body, empty body, typed data resolution); api.surface.test.ts export | COMPLIANT |
| Type alignment with backend | types/bestCombination.ts mirrors backend DTO field-for-field incl. stake subobject + top-level disclaimer; page SAMPLE fixture same shape; smoke keys match | COMPLIANT |

### Correctness (Static Evidence)
| Requirement | Status | Notes |
|------------|--------|-------|
| Unified pick DTO (sport+match_id) | Implemented | unified_pick.py frozen dataclass; suggested_pick.py backward-compatible defaults; use-case fetchers emit unified dicts |
| Quality filter per sport | Implemented | combination_optimizer.py:174-179 |
| Single best selection | Implemented | `_best` priority→probability (:181-184) |
| Fallback + confidence_warning + is_recommended False | Implemented | `_select_sport_leg` :186-214; `_build_leg` :330 forces False on fallback (W-2) |
| min_probability on quality pool only; fallback relaxed + warned | Implemented | :200-209 + spec relaxation (W-3) |
| Odds fallback market/fair | Implemented | `_leg_odds` :380-386 |
| Mixed-odds rule | Implemented | `_compute_totals` :355-378 (all-market product else 1/total_p) — ADR-3 honored |
| Neg-EV guard | Implemented | :280-286 → `no_positive_ev` |
| Coverage errors | Implemented | :246-260 `insufficient_pool`/`no_picks_available` + missing_sports |
| Kelly + RiskManager caps incl. per-league | Implemented | `size_stake` :388-419 applies MAX_LEAGUE_EXPOSURE 0.03 when league present (W-4) |
| 409/422 error contract | Implemented | router :39-45 `{error, detail, missing_sports}`; Pydantic 422; no leak (smoke) |
| min_probability gt=0 lt=1 | Implemented | dtos.py:18-23; smoke 422 `less_than` |
| Router registered | Implemented | api/main.py include_router |
| Frontend page/states/nav/route | Implemented | BestCombinationPage.tsx (loading/error/empty/data/warnings); App.tsx route; MainLayout.tsx "Mejor Combinación"; no `as any` |
| Spanish neutral copy | Implemented | Page + warnings + disclaimer professional neutral Spanish |
| ADR-5 ParleyService untouched | Implemented | `git diff 9c42dbe..HEAD -- parley_service.py get_parleys_use_case.py` → empty |

### Coherence (Design)
| Decision | Followed? | Notes |
|----------|-----------|-------|
| ADR-1 Max EV (ties→probability) | Yes | `_best` priority, probability tiebreak |
| ADR-2 Neg-EV forced 4-leg → 409 | Yes | EV ≤ 0 → 409 |
| ADR-3 Mixed-odds rule | Yes | product only if all 4 market; smoke 2.64 = 1/0.3794 |
| ADR-4 UnifiedPick + per-sport adapter | Yes | to_unified + default_pool_fetchers; explicit None check (use_case.py:285-287) |
| ADR-5 New CombinationOptimizer; ParleyService untouched | Yes | git diff empty |
| ADR-6 Response DTO shape (documented deviation) | Yes | stake object separate from aggregate + top-level disclaimer; spec table amended (:37-38), design ADR-6 row (:16) + note (:94-99); frontend mirrors; live 200 matches |
| Design step 8: per-league cap 0.03 when league present | Yes | size_stake + end-to-end test (W-4) |
| Design algorithm step 4: min_probability on quality pool only; fallback relaxed | Yes | spec relaxation recorded (W-3) |
| Testing strategy | Yes | unit optimizer/use-case/Kelly caps + router integration + frontend vitest all present; remediation added 6 backend + 3 frontend tests |

### Issues Found
**CRITICAL**: None
**WARNING**: None
**SUGGESTION**:
- S-1 (follow-up): add dedicated unit tests asserting soccer/tennis/baseball/basketball services emit `sport`/`match_id`/`odds` on market dicts (scenario 1 relies on live smoke + static evidence; task 5.5 was a manual spot-check).

## Risks

- Production soccer legs always use fair odds (DTOs expose no decimal odds) → mixed-odds rule applies, EV ≈ 0 on fair legs; endpoint may frequently 409 `no_positive_ev` with real bookmaker-free data (smoke: EV 0.0016 barely positive). Expected per ADR-3; flagged in design.
- Fetchers swallow per-sport exceptions as empty pools (use_case.py:295-305); silent pool degradation is by design but hides data-source outages behind `insufficient_pool` 409s.
- W-5 class flake: timing-sensitive frontend tests (TrainingControlPanel, MatchCard) can time out under first-run parallel load; mitigate with solo re-runs or increased testTimeout — pre-existing, not from this change.

### Verdict
PASS
(All 33 tasks complete; 297/297 backend tests, 82/82 frontend tests, tsc/lint clean; 18/18 spec scenarios compliant; smoke 200/409/422 contract-correct; C-1 accepted as recorded deviation ADR-6, W-1..W-4 resolved with tests + live evidence, S-2/S-3/S-4 resolved; S-1 remains a follow-up.)