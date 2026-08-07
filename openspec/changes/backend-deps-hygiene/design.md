# backend-deps-hygiene Technical Design

## Overview

Pure configuration refactor across 7 files. No code changes, no behavior changes. Minimal diffs, zero abstraction.

## File-by-File Edit Plan

### 1. backend/requirements.txt

**Current state (key lines):**
```
# ... runtime deps ...
numpy==1.26.4
joblib==1.4.2
scikit-learn==1.5.0
pandas==2.2.2
pydantic==2.12.5
pydantic-settings==2.12.0
httpx==0.26.0
aiohttp==3.13.2
python-dotenv==1.0.0
motor>=3.2.0
orjson                    # line 33 - REMOVE
scipy==1.13.1             # not in this file (only in worker)

# Dev tooling inline - MOVE to requirements-dev.txt:
pytest>=8.0.0
ruff>=0.1.0
black>=23.0.0
isort>=5.12.0
flake8>=6.0.0
mypy>=1.8.0
types-pytz>=2023.3
```

**After:**
```
# Runtime dependencies only
numpy==1.26.4
joblib==1.4.2
scikit-learn==1.5.0
pandas==2.2.2
pydantic==2.12.5
pydantic-settings==2.12.0
httpx==0.26.0
aiohttp==3.13.2
python-dotenv==1.0.0
motor==3.6.0           # pinned exact
# orjson removed
# scipy not in this file
# Dev tooling moved to requirements-dev.txt
```

**Changes:**
- Remove `orjson` line
- Change `motor>=3.2.0` → `motor==3.6.0` (resolve to current stable 3.x)
- Remove 7 dev tool lines
- Remove stale "removed" comment block (if present)
- Keep all other runtime deps with aligned versions

**Verification:** `pip install -r backend/requirements.txt && python -c "import motor, pydantic, httpx, aiohttp, python_dotenv; print('OK')"`

---

### 2. backend/requirements-worker.txt

**Current state (key lines):**
```
# Stale comment: "numpy, joblib, scikit-learn, scipy, pandas removed"
numpy==1.26.4
joblib==1.4.2
scikit-learn==1.5.0
pandas==2.2.2
pydantic==2.7.4           # drift: main is 2.12.5
pydantic-settings==2.3.4   # drift: main is 2.12.0
httpx==0.27.0              # drift: main is 0.26.0
aiohttp==3.9.5             # drift: main is 3.13.2
python-dotenv==1.0.1       # drift: main is 1.0.0
motor>=3.2.0               # same unpinned
orjson                     # REMOVE
scipy==1.13.1              # REMOVE
```

**After:**
```
# Worker runtime dependencies (aligned with main)
numpy==1.26.4
joblib==1.4.2
scikit-learn==1.5.0
pandas==2.2.2
pydantic==2.12.5
pydantic-settings==2.12.0
httpx==0.26.0
aiohttp==3.13.2
python-dotenv==1.0.0
motor==3.6.0
# orjson removed
# scipy removed
# stale "removed" comment removed
```

**Changes:**
- Align all 5 drifted versions to match main
- Remove `orjson` line
- Remove `scipy==1.13.1` line
- Change `motor>=3.2.0` → `motor==3.6.0`
- Remove stale "removed" comment block

**Verification:** `pip install -r backend/requirements-worker.txt && python -c "import motor, pydantic, httpx, aiohttp, python_dotenv; print('Worker OK')"`

---

### 3. backend/requirements-dev.txt (NEW FILE)

**Create new file:**
```
# Development tooling — NOT installed in production
pytest>=8.0.0
ruff>=0.1.0
black>=23.0.0
isort>=5.12.0
flake8>=6.0.0
mypy>=1.8.0
types-pytz>=2023.3
```

**Verification:** `pip install -r backend/requirements-dev.txt && pytest --version && ruff --version && black --version`

---

### 4. frontend/package.json

**Current (dependencies):**
```json
"dependencies": {
  ...,
  "recharts": "^3.6.0"
}
```

**After:**
```json
"dependencies": {
  ...
  // recharts removed
}
```

**Then regenerate lockfile:** `cd frontend && npm install`

**Verification:** `cd frontend && npm install && npm ls recharts` (should return empty)

---

### 5. .github/workflows/ci.yml

**Find lint step:**
```yaml
- name: Lint
  run: |
    pip install -r backend/requirements.txt
    ruff check .
    black --check .
    isort --check .
    mypy backend/src --ignore-missing-imports --follow-imports=skip
```

**After:**
```yaml
- name: Lint
  run: |
    pip install -r backend/requirements-dev.txt
    ruff check .
    black --check .
    isort --check .
    mypy backend/src --ignore-missing-imports --follow-imports=skip
```

**Verification:** Run workflow locally via `act` or push test branch to trigger CI.

---

### 6. .github/workflows/ci-pr.yml

Same pattern as ci.yml — find lint step, change `pip install -r backend/requirements.txt` → `pip install -r backend/requirements-dev.txt`.

---

### 7. .github/workflows/lint.yml

Same pattern — change install source to `backend/requirements-dev.txt`.

---

## Verification Commands (after all changes)

```bash
# Backend
pip install -r backend/requirements.txt
pip install -r backend/requirements-worker.txt
pip install -r backend/requirements-dev.txt
python -c "import motor, pydantic, httpx, aiohttp, python_dotenv; print('Runtime OK')"

# Frontend
cd frontend && npm install
npm ls recharts  # should be empty

# CI test (local via act or dry-run)
# push test branch to trigger CI
```

---

## Risk Mitigation

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Worker aiohttp 3.9.5→3.13.2 breaks async HTTP | Low | Exploration confirmed no breaking usage; `aiohttp` used in `async_mongo_adapter.py` and `async_mongo_repository.py` — compatible |
| Worker pydantic 2.7.4→2.12.5 breaks models | Low | `pydantic` used in `prediction_service.py`, `ml_training_orchestrator.py` — minor version bumps within 2.x are backward compatible |
| `motor==3.6.0` vs `>=3.2.0` | Low | Exact pin is safer; current resolved version is 3.6.x |
| Dev tools missing in CI lint | None | Explicit install from requirements-dev.txt is identical tool set |

---

## YAGNI Checklist

- [x] No new directories
- [x] No new code files beyond requirements-dev.txt
- [x] No new abstractions
- [x] No runtime behavior changes
- [x] Minimal diffs (each file: only lines that must change)

---

## Rollback Plan

Each file change is independent and revertible:
- `git checkout -- backend/requirements.txt`
- `git checkout -- backend/requirements-worker.txt`
- `rm backend/requirements-dev.txt`
- `git checkout -- frontend/package.json && cd frontend && npm install`
- `git checkout -- .github/workflows/{ci.yml,ci-pr.yml,lint.yml}`

---

## Files Changed Summary

| File | Action | Lines Changed |
|------|--------|---------------|
| backend/requirements.txt | Modified | ~15 (remove orjson, 7 dev tools, pin motor, fix comments) |
| backend/requirements-worker.txt | Modified | ~15 (align 5 versions, remove orjson/scipy, pin motor) |
| backend/requirements-dev.txt | Created | 7 lines |
| frontend/package.json | Modified | 1 (remove recharts) |
| .github/workflows/ci.yml | Modified | 1 (requirements.txt → requirements-dev.txt) |
| .github/workflows/ci-pr.yml | Modified | 1 |
| .github/workflows/lint.yml | Modified | 1 |

Total: ~50 lines changed across 8 files. Pure config refactor.