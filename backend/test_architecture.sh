#!/bin/bash
# Test script for serverless architecture
# This script tests both API-only mode and worker script

set -e  # Exit on error

echo "========================================="
echo "🧪 Testing Serverless Architecture"
echo "========================================="
echo ""

# Colors
GREEN='\033[0.32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo -e "${YELLOW}⚠️  Virtual environment not activated${NC}"
    echo "Activating venv..."
    source venv/bin/activate
fi

echo -e "${GREEN}✓ Virtual environment active${NC}"
echo ""

# Test 1: Check dependencies
echo "========================================="
echo "📦 Test 1: Checking Dependencies"
echo "========================================="

if python -c "import pandas" 2>/dev/null; then
    echo -e "${YELLOW}⚠️  Heavy ML dependencies detected (pandas)${NC}"
    echo "   For API-only mode, these should not be installed"
    echo "   Run: pip uninstall pandas numpy scikit-learn scipy joblib -y"
else
    echo -e "${GREEN}✓ No heavy ML dependencies (good for API-only mode)${NC}"
fi
echo ""

# Test 2: Test API-only mode startup
echo "========================================="
echo "🚀 Test 2: API-Only Mode Startup"
echo "========================================="

export API_ONLY_MODE=true
export DATABASE_URL="sqlite:///./test_api_only.db"

echo "Starting server in API-only mode..."
timeout 10s uvicorn src.api.main:app --port 8001 > /tmp/api_only_test.log 2>&1 &
SERVER_PID=$!

sleep 5

if ps -p $SERVER_PID > /dev/null; then
    echo -e "${GREEN}✓ Server started successfully in API-only mode${NC}"
    
    # Check logs for API-only mode message
    if grep -q "API-ONLY MODE" /tmp/api_only_test.log; then
        echo -e "${GREEN}✓ API-only mode detected in logs${NC}"
    else
        echo -e "${RED}✗ API-only mode not detected in logs${NC}"
    fi
    
    # Test health endpoint
    if curl -s http://localhost:8001/health > /dev/null; then
        echo -e "${GREEN}✓ Health endpoint responding${NC}"
    else
        echo -e "${RED}✗ Health endpoint not responding${NC}"
    fi
    
    # Cleanup
    kill $SERVER_PID 2>/dev/null || true
else
    echo -e "${RED}✗ Server failed to start${NC}"
    cat /tmp/api_only_test.log
fi

rm -f test_api_only.db
echo ""

# Test 3: Check worker script exists
echo "========================================="
echo "🔧 Test 3: Worker Script"
echo "========================================="

if [ -f "scripts/run_predictions.py" ]; then
    echo -e "${GREEN}✓ Worker script exists${NC}"
    
    # Check if it's executable
    if python -m py_compile scripts/run_predictions.py 2>/dev/null; then
        echo -e "${GREEN}✓ Worker script syntax is valid${NC}"
    else
        echo -e "${RED}✗ Worker script has syntax errors${NC}"
    fi
else
    echo -e "${RED}✗ Worker script not found${NC}"
fi
echo ""

# Test 4: Check GitHub Actions workflow
echo "========================================="
echo "🤖 Test 4: GitHub Actions Workflow"
echo "========================================="

if [ -f "../.github/workflows/update_predictions.yml" ]; then
    echo -e "${GREEN}✓ GitHub Actions workflow exists${NC}"
    
    # Check if it has cron schedule
    if grep -q "cron:" ../.github/workflows/update_predictions.yml; then
        echo -e "${GREEN}✓ Cron schedule configured${NC}"
    else
        echo -e "${YELLOW}⚠️  No cron schedule found${NC}"
    fi
else
    echo -e "${RED}✗ GitHub Actions workflow not found${NC}"
fi
echo ""

# Test 5: Check requirements files
echo "========================================="
echo "📋 Test 5: Requirements Files"
echo "========================================="

if [ -f "requirements.txt" ]; then
    echo -e "${GREEN}✓ requirements.txt exists${NC}"
    
    # Check if pandas is NOT in requirements.txt
    if ! grep -q "pandas" requirements.txt; then
        echo -e "${GREEN}✓ requirements.txt is lightweight (no pandas)${NC}"
    else
        echo -e "${RED}✗ requirements.txt contains heavy dependencies${NC}"
    fi
fi

if [ -f "requirements-worker.txt" ]; then
    echo -e "${GREEN}✓ requirements-worker.txt exists${NC}"
    
    # Check if pandas IS in requirements-worker.txt
    if grep -q "pandas" requirements-worker.txt; then
        echo -e "${GREEN}✓ requirements-worker.txt contains ML dependencies${NC}"
    else
        echo -e "${RED}✗ requirements-worker.txt missing ML dependencies${NC}"
    fi
fi
echo ""

# Summary
echo "========================================="
echo "📊 Test Summary"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. Install worker dependencies: pip install -r requirements-worker.txt"
echo "2. Run worker locally: python scripts/run_predictions.py"
echo "3. Set up GitHub Actions secrets (DATABASE_URL, API keys)"
echo "4. Deploy to Render with API_ONLY_MODE=true"
echo ""
echo "========================================="
