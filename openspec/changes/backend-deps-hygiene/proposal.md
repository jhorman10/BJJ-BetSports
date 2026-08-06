# Proposal: Backend Dependency Hygiene

## Intent

Eliminate dead dependencies, fix version drift between requirements files, stop shipping dev tooling to production, and correct misleading comments that claim packages are "removed" when they are still declared and used. This reduces attack surface, image size, and maintenance burden.

## Scope

### In Scope
- Remove `orjson` (unpinned) and `scipy==1.13.1` from both `backend/requirements.txt` and `backend/requirements-worker.txt` — zero imports repo-wide
- Remove `recharts@^3.6.0` from `frontend/package.json` and regenerate `frontend/package-lock.json` — no imports, no chart components
- Fix stale comments in both requirements files claiming `numpy` and `joblib` "removed" — both are still declared and used
- Reconcile cross-file version drift: align `requirements-worker.txt` to `requirements.txt` versions for:
  - `pydantic` 2.12.5, `pydantic-settings` 2.12.0, `httpx` 0.26.0, `aiohttp` 3.13.2, `python-dotenv` 1.0.0
- Pin `motor==3.2.0` (exact version from `requirements.txt`) — currently unpinned range `>=3.2.0`
- Extract dev tooling (`pytest`, `ruff`, `black`, `isort`, `flake8`, `mypy`, `types-pytz`) from `requirements.txt` into new `backend/requirements-dev.txt`
- Update CI workflows (`.github/workflows/ci.yml`, `ci-pr.yml`, `lint.yml`) to install from `requirements-dev.txt` for lint/type/test jobs
- Keep used deps as-is: `numpy==1.26.4`, `joblib==1.4.2`, `scikit-learn==1.5.0`, `apscheduler==3.10.4`, `pandas==2.2.2`

### Out of Scope
- Docker split (separate change C)
- CI dedup (separate change D)
- Bun migration (plan only, not executed)
- `datetime.utcnow` migration (separate change B)
- Any runtime behavior changes

## Capabilities

### New Capabilities
- None

### Modified Capabilities
- None

> Pure config/refactor change — no spec-level behavior modifications.

## Approach

1. Edit `backend/requirements.txt`: remove dead deps, fix comments, extract dev tooling to new file
2. Create `backend/requirements-dev.txt` with extracted dev dependencies
3. Edit `backend/requirements-worker.txt`: remove dead deps, align versions to main requirements
4. Edit `frontend/package.json`: remove `recharts` dependency
5. Regenerate `frontend/package-lock.json` via `npm install`
6. Update 3 CI workflow files to install `requirements-dev.txt` for lint/type/test jobs
7. Verify: `pip install -r requirements.txt` installs only runtime deps; worker env matches main; frontend builds without recharts

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `backend/requirements.txt` | Modified | Remove orjson, scipy; fix comments; extract dev deps |
| `backend/requirements-worker.txt` | Modified | Remove orjson, scipy; align versions to main |
| `backend/requirements-dev.txt` | New | Dev tooling extracted from requirements.txt |
| `frontend/package.json` | Modified | Remove recharts dependency |
| `frontend/package-lock.json` | Modified | Regenerated after recharts removal |
| `.github/workflows/ci.yml` | Modified | Install requirements-dev.txt for lint/test jobs |
| `.github/workflows/ci-pr.yml` | Modified | Install requirements-dev.txt for lint/test jobs |
| `.github/workflows/lint.yml` | Modified | Install requirements-dev.txt for lint job |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Version alignment breaks worker | Low | Exploration confirmed worker lags main; aligning is safe; worker tests in CI will catch regressions |
| Missing dev dep in CI | Low | Explicit list from current requirements.txt; verify CI passes after change |
| Frontend build fails without recharts | Low | Confirmed zero imports and no chart components in codebase |
| Dockerfile.portable installs both files | Low | Dockerfile installs both; worker version alignment ensures consistency |

## Rollback Plan

1. Revert all 8 modified files to pre-change state via `git checkout HEAD -- <files>`
2. Delete `backend/requirements-dev.txt` if created
3. CI workflows will automatically use reverted requirements.txt
4. No database migrations or schema changes — pure dependency manifest changes

## Dependencies

- None external. Requires `npm` and `pip` available in CI (already configured).

## Success Criteria

- [ ] `pip install -r backend/requirements.txt` installs only runtime dependencies (no pytest, ruff, black, isort, flake8, mypy, types-pytz)
- [ ] `pip install -r backend/requirements-dev.txt` installs all dev tooling for CI
- [ ] `pip install -r backend/requirements-worker.txt` versions match `requirements.txt` for pydantic, pydantic-settings, httpx, aiohttp, python-dotenv
- [ ] `motor==3.2.0` pinned in both files
- [ ] `orjson` and `scipy` absent from both requirements files
- [ ] `frontend/package.json` no longer contains `recharts`
- [ ] `npm install` in frontend succeeds and `npm run build` passes
- [ ] All 3 CI workflows pass with new dependency structure