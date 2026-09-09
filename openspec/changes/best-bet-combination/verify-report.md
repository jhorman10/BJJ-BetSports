# Verify Report: best-bet-combination

**Change**: best-bet-combination
**Version**: spec v1 (best-combination + api-client deltas)
**Mode**: Standard (strict TDD not active per openspec/config.yaml `tdd: false`)
**Date**: 2026-09-08
**Evidence base**: real execution (ruff/black/isort/mypy/pytest/tsc/eslint/vitest/API smoke via FastAPI TestClient)

## Verdict: FAIL

One CRITICAL response-schema contract mismatch (aggregate.* field placement vs spec) — all runtime evidence green (291 backend tests, 79 frontend tests, live 200 smoke response, end-to-end 4-leg combination computed through production fetchers).

## Completeness

| Metric | Value |
|--------|-------|
| Tasks total | 33 |
| Tasks complete | 33 |
| Tasks incomplete | 0 |

## Build & Tests Execution

**Backend**
- `ruff check src/ tests/` → ✅ All checks passed
- `black --check src/ tests/` → ✅ 199 files unchanged
- `isort --check-only src/ tests/` → ✅ clean
- `mypy src --ignore-missing-imports --follow-imports=skip` → ✅ Success, 149 source files
- `pytest tests/ -q` → ✅ 291 passed, 3331 warnings (pre-existing deprecation warnings), 37.08s
  - New change tests: 36 passed (test_combination_optimizer.py + test_best_combination_use_case.py + test_best_combination_router.py)

**Frontend**
- `tsc -b` → ✅ clean (exit 0)
- `npm run lint` → ✅ 0 errors, 19 warnings (≤ 25)
- `npx vitest run` → 79 tests; 4 full-suite runs: 78/79, 79/79, 79/79, 79/79 (1 intermittent failure = pre-existing TrainingControlPanel.test.tsx flake under parallel load; passes solo 2/2; file untouched by this branch — verified via git diff)

**API smoke (FastAPI TestClient, real app, production fetchers)**
- `POST /api/v1/best-combination` `{}` → **200 OK** real 4-leg combination (soccer E0 ESPN fixture, tennis US Open, baseball MLB, basketball NBA demo; all legs `odds_source: fair`, aggregate `total_probability 0.3794`, `total_odds 2.64` = 1/0.3794, `EV 0.0016`, stake 0.02%, risk 1, independence_disclaimer present, 5 warnings) — quality gate, fair-odds fallback, mixed-odds rule, Kelly stake, and disclaimer all proven end-to-end
- `{"min_probability": 1.5}` → 422 `less_than` (Pydantic `lt=1` gate) ✅
- `{"exclude_leagues": "E0"}` → 422 (type validation) ✅
- `{"min_probability": 0.5, "exclude_leagues": ["E0"]}` → 409 `{detail: {error: insufficient_pool, detail, missing_sports: [soccer]}}` — exclude_leagues hard-constraint behaved correctly (E0 exclusion wiped soccer pool) ✅
- No internal leak: response bodies contain no tracebacks/source paths ✅

## Spec Compliance Matrix (specs/best-combination/spec.md)

| Requirement | Scenario | Test / Evidence | Result |
|-------------|----------|-----------------|--------|
| Unified pick DTO | All sports expose unified picks | Smoke 200 (real legs carried match_id); static picks.py:58-62, tennis_prediction_service.py:705-707, baseball_prediction_service.py:433-435, basketball_prediction_service.py:466-468. No dedicated unit test | ⚠️ PARTIAL |
| Unified pick DTO | Pick lacking match_id excluded | `test_drops_picks_missing_match_id` | ✅ COMPLIANT |
| POST /best-combination | Request with filters | `test_min_probability_filters_quality_pool`, `test_min_probability_passthrough`, `test_exclude_leagues_passthrough`; fallback path ignores min_probability (see WARNING W-3) | ⚠️ PARTIAL |
| POST /best-combination | Invalid filter rejected | `test_422_on_invalid_min_probability`, `test_422_on_invalid_exclude_leagues_type` + smoke 422 | ✅ COMPLIANT |
| Quality filter | Qualifying pick enters pool | `test_soccer_requires_ml_or_ia_confirmed` | ✅ COMPLIANT |
| Quality filter | Low-confidence pick filtered | `test_other_sports_require_high_and_recommended` | ✅ COMPLIANT |
| Single best selection | Happy path — best combo | `test_happy_path_four_legs_and_totals`, `test_returns_four_legs`, smoke 200 (4 distinct sports) | ✅ COMPLIANT |
| Single best selection | Highest-priority leg chosen | `test_picks_best_by_priority_then_probability`, `test_priority_tie_breaks_by_probability` | ✅ COMPLIANT |
| Missing high-confidence policy | Sport lacks high-confidence picks | `test_fallback_when_quality_pool_empty` (confidence_warning + 4 legs) | ✅ COMPLIANT (scenario body); requirement text deviation → WARNING W-2 |
| Odds fallback | Missing market odds | `test_fair_odds_fallback_when_odds_missing` + smoke (all 4 legs fair, 1/p math verified) | ✅ COMPLIANT |
| Combination math & EV | EV from combined odds | `test_happy_path_four_legs_and_totals` (Πp, Πodds, EV formula); disclaimer asserted in `test_returns_four_legs` | ✅ COMPLIANT |
| Combination math & EV | Negative EV refused | `test_no_positive_ev_when_edge_not_positive`, `test_409_no_positive_ev` | ✅ COMPLIANT |
| Stake guidance | Kelly capped by exposure | `test_stake_capped_at_risk_manager_max` | ✅ COMPLIANT (scenario); requirement text deviation → WARNING W-4 |
| Insufficient-data errors | One sport has no events | `test_insufficient_pool_reports_missing_sports`, `test_409_insufficient_pool` (missing_sports asserted), smoke 409 | ✅ COMPLIANT |
| Insufficient-data errors | No picks at all | `test_no_picks_available_when_all_empty`, `test_409_no_picks_available` | ✅ COMPLIANT |

**Response field contract (spec table lines 29-37) vs implementation:**

| Spec field | Implemented | Status |
|------------|-------------|--------|
| legs[].sport / match_id / match_label / pick_label | ✅ legs.* | ✅ |
| legs[].probability / odds | ✅ legs.* | ✅ |
| legs[].odds_source market\|fair | ✅ legs.* Literal | ✅ |
| legs[].confidence_level / is_recommended | ✅ legs.* | ✅ |
| legs[].confidence_warning / odds_warning | ✅ legs.* | ✅ |
| aggregate.total_probability / total_odds / expected_value | ✅ aggregate.* | ✅ |
| **aggregate.risk_level** | ❌ `stake.risk_level` (best_combination_dtos.py:57-62) | ❌ **CRITICAL C-1** |
| **aggregate.suggested_stake_pct** | ❌ `stake.suggested_stake_pct` | ❌ **CRITICAL C-1** |
| **aggregate.independence_disclaimer** | ❌ top-level `independence_disclaimer` (lines 65-73) | ❌ **CRITICAL C-1** |

**Specs/api-client/spec.md**

| Scenario | Test / Evidence | Result |
|----------|-----------------|--------|
| Endpoint constant resolves | constants.ts:60 `BEST_COMBINATION: "/api/v1/best-combination"`; api.test.ts asserts POST to constant; smoke hit path → 200 | ✅ COMPLIANT |
| Typed client method posts | api.test.ts (3 tests: filter body, empty body, typed data resolution); api.surface.test.ts export (27 exports) | ✅ COMPLIANT |
| Type alignment with backend | types/bestCombination.ts mirrors backend DTO field-for-field (incl. stake subobject) | ✅ COMPLIANT |

**Compliance summary**: 17/18 scenarios compliant (1 PARTIAL without blocker, 1 PARTIAL with warning); 18/18 have runtime or static evidence; 0 UNTESTED with zero evidence.

## Correctness (Static Evidence)

| Requirement | Status | Notes |
|------------|--------|-------|
| Unified pick DTO (sport+match_id) | ✅ Implemented | unified_pick.py frozen dataclass; suggested_pick.py:105-106 backward-compatible defaults; picks.py:58-62 soccer emission |
| Quality filter per sport | ✅ Implemented | combination_optimizer.py:174-179 (`is_ml_confirmed or is_ia_confirmed` soccer; `high`+`is_recommended` others) |
| Single best selection | ✅ Implemented | `_best` priority→probability (182-184) |
| Fallback + confidence_warning | ✅ Implemented | `_select_sport_leg` 198-214; 4-leg scope preserved |
| Odds fallback market/fair | ✅ Implemented | `_leg_odds` 372-378 (market if >1.0 else 1/p, rounding 2) |
| Mixed-odds rule | ✅ Implemented | `_compute_totals` 347-370 (all-market product else 1/total_p) — ADR-3 honored |
| Neg-EV guard | ✅ Implemented | 280-286 → `no_positive_ev` |
| Coverage errors | ✅ Implemented | 246-260 `insufficient_pool`/`no_picks_available` + missing_sports |
| Kelly + RiskManager cap | ✅ Implemented (partial per W-4) | `size_stake` 380-402 |
| 409/422 error contract | ✅ Implemented | router 39-45 `{error, detail, missing_sports}`; Pydantic 422; no leak (smoke) |
| min_probability gt=0 lt=1 | ✅ Implemented | dtos.py:18-23; smoke 422 `less_than` |
| Router registered | ✅ Implemented | api/main.py:85-87, 111 |
| Frontend page/states/nav/route | ✅ Implemented | BestCombinationPage.tsx (loading/error/empty/data/warnings); App.tsx:156; MainLayout.tsx:46 "Mejor Combinación"; no `as any` (grep clean) |
| Spanish neutral copy | ✅ Implemented | Page + warnings + disclaimer professional neutral Spanish |
| ADR-5 ParleyService untouched | ✅ Implemented | `git diff 9c42dbe..HEAD -- parley_service.py get_parleys_use_case.py` → empty |

## Coherence (Design)

| Decision | Followed? | Notes |
|----------|-----------|-------|
| ADR-1 Max EV (ties→probability) | ✅ Yes | `_best` priority, probability tiebreak |
| ADR-2 Neg-EV forced 4-leg → 409 | ✅ Yes | ev <= 0 → 409 |
| ADR-3 Mixed-odds rule | ✅ Yes | product only if all 4 market |
| ADR-4 UnifiedPick + per-sport adapter | ✅ Yes | to_unified + default_pool_fetchers; explicit `is None` check for empty fetcher map (use_case.py:287) |
| ADR-5 New CombinationOptimizer; ParleyService untouched | ✅ Yes | git diff empty |
| Design interface: risk_level/suggested_stake_pct/independence_disclaimer inside `aggregate` | ❌ No | implemented in `stake` + top-level → CRITICAL C-1 |
| Design step 8: cap = max_single 0.05, daily 0.05, per-league 0.03 | ⚠️ Partial | only max_single + daily applied (W-4) |
| Design algorithm step 2 vs step 4: min_probability on quality pool only | ⚠️ Yes (documented) | implementation matches design; spec scenario text stricter (W-3) |
| Testing strategy | ✅ Yes | unit optimizer/use-case/Kelly + router integration + frontend vitest all present |

## Issues Found

**CRITICAL**
- **C-1 Response schema contract mismatch**: spec table (spec.md:36-37) and design interface (design.md:76-83) place `risk_level`, `suggested_stake_pct`, and `independence_disclaimer` **inside `aggregate`**. Implementation returns them in a separate `stake` object (`stake.risk_level`, `stake.suggested_stake_pct`) and top-level `independence_disclaimer` (best_combination_dtos.py:48-73). Response payload is a superset (frontend mirrors the implementation, so nothing breaks at runtime), but the public API shape does not match the spec contract. Fix = relocate DTO fields to `aggregate` + update frontend types/tests, OR record an accepted spec deviation (amend spec table). Deviation was not recorded in design Open Questions during apply.

**WARNING**
- **W-1 Frontend error extraction mismatch**: backend 409s serialize `detail` as an OBJECT (`{error, detail, missing_sports}` — best_combination.py:41-45) and 422s as a LIST (Pydantic); `extractErrorDetail` (BestCombinationPage.tsx:53-60) only renders string details, so real 409/422 messages are replaced by the generic fallback text. Test mocks a string detail (test:115-135), so this is not caught. Backend error contract itself is spec-correct.
- **W-2 Fallback leg does not force `is_recommended: false`**: spec requirement text (spec.md:86) — fallback "MUST set ... is_recommended: false". `_select_sport_leg` (combination_optimizer.py:212-214) returns the best-available pick with only `confidence_warning=True`; `_build_leg` (line 322) propagates `pick.is_recommended` unchanged. Test data masks it (fallback pick happened to be `is_recommended=False`). Reachable in production (e.g., recommended-but-unconfirmed soccer pick).
- **W-3 `min_probability` not enforced on fallback pool**: `_select_sport_leg` applies the threshold only to the quality pool (line 203); the fallback list (line 209) ignores it. With `min_probability: 0.6` and an empty quality pool, a 0.4-probability leg can be returned — contradicts spec scenario "Request with filters" ("each leg probability is ≥ 0.5"). Design algorithm step 4 implies this relaxation, but the spec scenario is unconditional. Needs explicit decision.
- **W-4 Per-league exposure cap not applied**: spec requirement 8 and design step 8 list per-league exposure (RiskManager.MAX_LEAGUE_EXPOSURE = 0.03, risk_manager.py:29); `size_stake` (combination_optimizer.py:393-397) caps only at MAX_SINGLE_STAKE (0.05) and MAX_DAILY_EXPOSURE (0.05). `test_stake_capped_at_risk_manager_max` asserts the 0.05 caps, so the scenario passes — but a Kelly of 0.05 would never be trimmed to 0.03 per-league.
- **W-5 Pre-existing frontend flake**: TrainingControlPanel.test.tsx intermittently fails under full-suite parallel load (1 failure in 4 runs; 2/2 solo passes). File untouched by this branch (git diff empty). Not introduced by this change; re-run solo confirms. Reported per instructions.

**SUGGESTION**
- **S-1** Add dedicated unit tests asserting soccer/tennis/baseball/basketball services emit `sport`/`match_id`/`odds` on market dicts (scenario 1 currently relies on smoke + static evidence; task 5.5 was a manual spot-check).
- **S-2** Add regression tests: fallback leg `is_recommended == False` (W-2) and `min_probability` enforcement on fallback (W-3).
- **S-3** Commit the SDD artifacts (proposal.md, design.md, specs/, tasks.md are untracked in git) so the PR/archive review can see them.
- **S-4** Branch was cut from `feat/multi-sport-support` HEAD (base 9c42dbe), not raw main — orchestrator should confirm PR base decision before archive (flagged in apply-progress too).

## Risks

- C-1 schema mismatch will break any external consumer implementing strictly against the spec; internal app unaffected (frontend types mirror implementation).
- W-3 could mislead users into thinking all legs meet the requested minimum probability.
- Production soccer legs always use fair odds (DTOs expose no decimal odds) → mixed-odds rule applies, EV ≈ 0 on fair legs; endpoint may frequently 409 `no_positive_ev` with real bookmaker-free data (smoke: EV 0.0016 barely positive). Expected per ADR-3; flagged in design Open Questions.
- Fetchers swallow per-sport exceptions as empty pools (use_case.py:295-305); silent pool degradation is by design but hides data-source outages behind `insufficient_pool` 409s.

## Verdict

**FAIL** — all execution gates green (lint/type/tests/smoke) and 17/18 spec scenarios compliant, but the response schema deviates from the spec contract table (aggregate.* field placement, C-1). Resolve C-1 (relocate DTO fields or amend spec as accepted deviation) and re-verify; W-2..W-5 should be addressed or explicitly accepted by the orchestrator in the same pass.