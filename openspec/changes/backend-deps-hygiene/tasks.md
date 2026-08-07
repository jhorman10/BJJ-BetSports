# backend-deps-hygiene Tasks

## Task Breakdown

| # | Phase | Task | Files | Acceptance Criteria | Dependencies | Guarding Tests |
|---|-------|------|-------|---------------------|--------------|----------------|
| 1 | Foundation | Create requirements-dev.txt | backend/requirements-dev.txt (NEW) | File exists with 7 dev tools; `pip install -r backend/requirements-dev.txt` succeeds and all 7 tools available | None | None |
| 2 | Foundation | Update requirements.txt | backend/requirements.txt | orjson removed; 7 dev tools removed; motor==3.6.0 pinned; stale comments removed; `pip install -r backend/requirements.txt` installs only runtime deps | 1 | `pip install -r backend/requirements.txt` |
| 3 | Foundation | Update requirements-worker.txt | backend/requirements-worker.txt | 5 versions aligned to main; orjson & scipy removed; motor==3.6.0; stale comments removed; `pip install -r backend/requirements-worker.txt` succeeds | 1 | `pip install -r backend/requirements-worker.txt` |
| 4 | Foundation | Remove recharts & regenerate lockfile | frontend/package.json, frontend/package-lock.json | recharts removed from deps; `npm install` runs clean; `npm ls recharts` returns empty | None | `npm ls recharts` |
| 5 | CI | Update ci.yml lint step | .github/workflows/ci.yml | lint step uses `pip install -r backend/requirements-dev.txt` | 1 | Workflow syntax valid |
| 6 | CI | Update ci-pr.yml lint step | .github/workflows/ci-pr.yml | lint step uses `pip install -r backend/requirements-dev.txt` | 1 | Workflow syntax valid |
| 7 | CI | Update lint.yml lint step | .github/workflows/lint.yml | lint step uses `pip install -r backend/requirements-dev.txt` | 1 | Workflow syntax valid |
| 8 | Verification | Full validation | All files | All 3 pip installs succeed; frontend `npm install` clean; `npm ls recharts` empty; lint jobs pass on all 3 workflows | 1-7 | Full CI pipeline |

## Execution Order

1 → (2, 3, 4 parallel) → (5, 6, 7 parallel) → 8

## Review Workload Forecast

- Estimated changed lines: ~50
- 400-line budget risk: **Low**
- Chained PRs recommended: **No**
- Delivery strategy: `single-pr`
- Decision needed before apply: **No**

---

## Task Details

### Task 1: Create requirements-dev.txt
**Scope:** Create `backend/requirements-dev.txt`
**Content:**
```
pytest>=8.0.0
ruff>=0.1.0
black>=23.0.0
isort>=5.12.0
flake8>=6.0.0
mypy>=1.8.0
types-pytz>=2023.3
```
**Verify:** `pip install -r backend/requirements-dev.txt && pytest --version && ruff --version`

### Task 2: Update requirements.txt
**Scope:** Edit `backend/requirements.txt`
**Changes:**
- REMOVE: `orjson` (line 33)
- REMOVE: 7 dev tool lines (pytest, ruff, black, isort, flake8, mypy, types-pytz)
- CHANGE: `motor>=3.2.0` → `motor==3.6.0`
- REMOVE: stale comment block claiming "numpy, joblib, scikit-learn, scipy, pandas removed"
- KEEP: all runtime deps with aligned versions
**Verify:** `pip install -r backend/requirements.txt && python -c "import motor, pydantic, httpx, aiohttp, python_dotenv; print('OK')"`

### Task 3: Update requirements-worker.txt
**Scope:** Edit `backend/requirements-worker.txt`
**Changes:**
- CHANGE: `pydantic==2.7.4` → `pydantic==2.12.5`
- CHANGE: `pydantic-settings==2.3.4` → `pydantic-settings==2.12.0`
- CHANGE: `httpx==0.27.0` → `httpx==0.26.0`
- CHANGE: `aiohttp==3.9.5` → `aiohttp==3.13.2`
- CHANGE: `python-dotenv==1.0.1` → `python-dotenv==1.0.0`
- CHANGE: `motor>=3.2.0` → `motor==3.6.0`
- REMOVE: `orjson` line
- REMOVE: `scipy==1.13.1` line
- REMOVE: stale "removed" comment block
**Verify:** `pip install -r backend/requirements-worker.txt && python -c "import motor, pydantic, httpx, aiohttp, python_dotenv; print('Worker OK')"`

### Task 4: Remove recharts
**Scope:** Edit `frontend/package.json`, regenerate lockfile
**Changes:**
- REMOVE: `"recharts": "^3.6.0"` from dependencies
- RUN: `cd frontend && npm install`
**Verify:** `cd frontend && npm ls recharts` (should return empty)

### Task 5: Update ci.yml
**Scope:** Edit `.github/workflows/ci.yml`
**Change:** In lint step, change `pip install -r backend/requirements.txt` → `pip install -r backend/requirements-dev.txt`

### Task 6: Update ci-pr.yml
**Scope:** Edit `.github/workflows/ci-pr.yml`
**Change:** Same as ci.yml — lint step uses requirements-dev.txt

### Task 7: Update lint.yml
**Scope:** Edit `.github/workflows/lint.yml`
**Change:** Same — lint step uses requirements-dev.txt

### Task 8: Full verification
**Scope:** Run all verification commands
**Commands:**
```bash
pip install -r backend/requirements.txt
pip install -r backend/requirements-worker.txt
pip install -r backend/requirements-dev.txt
python -c "import motor, pydantic, httpx, aiohttp, python_dotenv; print('Runtime OK')"
cd frontend && npm install
npm ls recharts
# CI: push test branch or run act locally
```

## Review Workload Forecast

- Estimated changed lines: ~50
- 400-line budget risk: **Low**
- Chained PRs recommended: **No**
- Delivery strategy: `single-pr`
- Decision needed before apply: **No**
- Suggested work-unit order: T1 → (T2,T3,T4) → (T5,T6,T7) → T8