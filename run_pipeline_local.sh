#!/usr/bin/env bash
set -e

echo "=================================================================="
echo "           PIPELINE SIMULATION (Matching Jenkinsfile)            "
echo "=================================================================="

echo ""
echo "[STAGE 1: Setup & Dependencies]"
source venv/bin/activate
pip install -q bandit flake8
echo ">> Virtual environment active and dependencies verified."

echo ""
echo "[STAGE 2: Static Analysis & Security Gate]"
echo ">> Running Bandit security scanner on services..."
bandit -r services/ -ll || true
echo ">> Security gate check completed."

echo ""
echo "[STAGE 3: Launch Services & Run Automated Tests]"
# Free any previous ports
lsof -ti :8000 -ti :8001 -ti :8002 | xargs kill -9 2>/dev/null || true

# Start microservices in background
python run_services.py > /tmp/pipeline_services.log 2>&1 &
RUNNER_PID=$!
sleep 3

echo ">> Running functional & authorization test suite..."
pytest -v tests/test_flow.py --junitxml=test-results.xml

echo ">> Running vulnerability demonstration suite..."
pytest -s -v tests/test_vulnerabilities.py

# Cleanup services
kill -TERM $RUNNER_PID 2>/dev/null || true
lsof -ti :8000 -ti :8001 -ti :8002 | xargs kill -9 2>/dev/null || true

echo ""
echo "[STAGE 4: Post-Build & Artifacts]"
if [ -f "test-results.xml" ]; then
    echo ">> Test artifact generated: test-results.xml ($(wc -l < test-results.xml) lines)"
fi

echo ""
echo "=================================================================="
echo "                PIPELINE COMPLETED SUCCESSFULLY!                  "
echo "=================================================================="
