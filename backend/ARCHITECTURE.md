# 🏗️ Serverless Architecture - Worker & API Separation

## Overview

This project now uses a **serverless architecture** that separates heavy ML computations from the lightweight API server:

- **GitHub Actions (The Brain)**: Runs ML training and prediction generation every 6 hours
- **PostgreSQL (The Memory)**: Stores all pre-computed predictions and training results
- **FastAPI on Render (The Face)**: Lightweight API that only reads from the database

## Architecture Diagram

```
┌─────────────────────────────────────┐
│   GitHub Actions Worker             │
│   (Every 6 hours)                   │
│                                     │
│   1. Fetch historical data          │
│   2. Train ML models                │
│   3. Generate predictions           │
│   4. Save to PostgreSQL             │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│   PostgreSQL Database               │
│   - Training results                │
│   - League predictions              │
│   - Match predictions               │
│   - Picks & statistics              │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│   FastAPI Server (Render)           │
│   API_ONLY_MODE=true                │
│                                     │
│   - No ML computations              │
│   - Only database reads             │
│   - Memory: ~100-150MB              │
└─────────────────────────────────────┘
```

## 🚀 Quick Start

### Local Development (Full Mode)

```bash
# Install all dependencies (including ML libraries)
cd backend
pip install -r requirements-worker.txt

# Run the server in full mode (with ML computations)
API_ONLY_MODE=false uvicorn src.api.main:app --reload

# Or run the worker script manually
python scripts/run_predictions.py
```

### Production (API-Only Mode)

```bash
# Install lightweight dependencies only
pip install -r requirements.txt

# Run the server in API-only mode
API_ONLY_MODE=true uvicorn src.api.main:app
```

## 📁 File Structure

```
backend/
├── scripts/
│   ├── run_predictions.py      # Main worker script
│   └── worker_config.py        # Worker configuration
├── requirements.txt            # Lightweight API dependencies (~50MB)
├── requirements-worker.txt     # Full ML dependencies (~400MB)
└── .env.example               # Environment variables template

.github/
└── workflows/
    └── update_predictions.yml  # GitHub Actions workflow
```

## 🔧 Configuration

### Environment Variables

#### Required for Production

```bash
# Architecture mode
API_ONLY_MODE=true              # Enable lightweight API mode

# Database (REQUIRED in production)
DATABASE_URL=postgresql://user:pass@host:port/db

# API Keys (for worker)
FOOTBALL_DATA_ORG_KEY=your_key
THE_ODDS_API_KEY=your_key
```

#### Optional

```bash
# Development
API_ONLY_MODE=false             # Enable full ML mode locally
LOW_MEMORY_MODE=false           # Disable for local development
DISABLE_ML_TRAINING=false       # Enable training locally
CLEAR_CACHE_ON_START=false      # Clear cache on startup

# Logging
LOG_LEVEL=INFO
```

### GitHub Actions Secrets

Add these secrets to your GitHub repository:

1. Go to **Settings** → **Secrets and variables** → **Actions**
2. Add the following secrets:
   - `DATABASE_URL`: PostgreSQL connection string
   - `FOOTBALL_DATA_ORG_KEY`: Football-Data.org API key
   - `THE_ODDS_API_KEY`: The Odds API key
   - `RAPIDAPI_KEY`: RapidAPI key (optional)

## 🔄 Worker Script

### Manual Execution

```bash
cd backend
python scripts/run_predictions.py
```

### What It Does

1. **Training Phase** (~5-10 minutes)

   - Fetches 4,912 historical matches from multiple sources
   - Trains Random Forest classifier
   - Calculates global statistical averages
   - Saves training results to database

2. **Prediction Phase** (~10-15 minutes)

   - Generates predictions for all leagues
   - Calculates suggested picks for each match
   - Saves individual match predictions to database
   - Total: ~500-1000 predictions saved

3. **Cleanup**
   - Removes old predictions (>7 days)
   - Logs summary statistics

### Output

```
================================================================================
✨ WORKER COMPLETED SUCCESSFULLY
================================================================================
⏱️  Duration: 847.23 seconds (14.12 minutes)
📊 Leagues processed: 16
🔮 Predictions saved: 847
📚 Training accuracy: 67.45%
💰 Training ROI: 12.34%
================================================================================
```

## 🤖 GitHub Actions Workflow

### Schedule

The worker runs automatically:

- **Every 6 hours**: `0 */6 * * *` (00:00, 06:00, 12:00, 18:00 UTC)
- **Manual trigger**: Via GitHub Actions UI

### Manual Trigger

1. Go to **Actions** tab in GitHub
2. Select **Update Predictions** workflow
3. Click **Run workflow**
4. Wait ~15-20 minutes for completion

### Monitoring

- View logs in **Actions** tab
- Download worker logs as artifacts (retained for 7 days)
- Automatic issue creation on failure

## 📊 Memory Usage Comparison

| Mode          | Dependencies            | RAM Usage  | Use Case                   |
| ------------- | ----------------------- | ---------- | -------------------------- |
| **API-Only**  | requirements.txt        | ~100-150MB | Production (Render)        |
| **Full Mode** | requirements-worker.txt | ~512MB+    | Local dev / GitHub Actions |

### Dependencies Removed in API-Only Mode

- ❌ `pandas` (~100MB)
- ❌ `numpy` (~50MB)
- ❌ `scikit-learn` (~100MB)
- ❌ `scipy` (~50MB)
- ❌ `joblib` (~10MB)
- ❌ `apscheduler` (~5MB)

**Total savings: ~300-400MB**

## 🧪 Testing

### Test Worker Locally

```bash
# 1. Set up test database
export DATABASE_URL="postgresql://localhost/bjj_test"

# 2. Run worker
python scripts/run_predictions.py

# 3. Check logs
tail -f worker.log
```

### Test API-Only Mode

```bash
# 1. Start server in API-only mode
API_ONLY_MODE=true uvicorn src.api.main:app

# 2. Check startup logs (should skip ML initialization)
# Expected: "🚀 Starting in API-ONLY MODE (Lightweight)"

# 3. Test endpoint
curl http://localhost:8000/api/v1/predictions/league/E0

# 4. If no data: empty predictions array
# After worker runs: full predictions
```

## 🚢 Deployment

### Render Configuration

1. **Environment Variables**:

   ```
   API_ONLY_MODE=true
   DATABASE_URL=<your-postgres-url>
   ```

2. **Build Command**:

   ```bash
   pip install -r requirements.txt
   ```

3. **Start Command**:
   ```bash
   uvicorn src.api.main:app --host 0.0.0.0 --port $PORT
   ```

### Expected Behavior

1. **First Deploy** (before worker runs):

   - Server starts successfully
   - API returns empty predictions
   - Memory usage: ~100-150MB

2. **After Worker Runs**:
   - API serves predictions from database
   - No ML computations on server
   - Memory usage stays low

## 🐛 Troubleshooting

### "No predictions available"

**Cause**: Worker hasn't run yet or database is empty

**Solution**:

```bash
# Manually trigger GitHub Actions workflow
# OR run worker locally:
python scripts/run_predictions.py
```

### "API_ONLY_MODE but still high memory"

**Cause**: Wrong requirements file installed

**Solution**:

```bash
# Reinstall with correct requirements
pip uninstall pandas numpy scikit-learn scipy joblib
pip install -r requirements.txt
```

### "Worker fails in GitHub Actions"

**Cause**: Missing secrets or database connection

**Solution**:

1. Check GitHub secrets are set correctly
2. Verify DATABASE_URL is accessible from GitHub Actions
3. Check workflow logs for specific error

## 📚 Additional Resources

- [Implementation Plan](/.gemini/antigravity/brain/b9e031cf-d2c8-405f-b10d-b2f432b72199/implementation_plan.md)
- [Task Breakdown](/.gemini/antigravity/brain/b9e031cf-d2c8-405f-b10d-b2f432b72199/task.md)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Render Documentation](https://render.com/docs)

## 🎯 Benefits

✅ **Reduced Memory Usage**: 512MB → 100-150MB (70% reduction)
✅ **Faster Deployments**: No ML model loading on startup
✅ **Better Reliability**: Pre-computed predictions always available
✅ **Cost Savings**: Can use smaller Render instance
✅ **Scalability**: Worker can run on powerful GitHub Actions runners
✅ **Separation of Concerns**: API and compute are independent
