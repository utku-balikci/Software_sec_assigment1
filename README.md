# Secure Notes & Export System

A secure microservices application demonstrating role-based access control (RBAC), multi-tier complete mediation, and supply-chain integrity verification in CI/CD.

## Architecture

- **Component 1 (Application API)**: Port `8000` (Gateway & JWT Auth)
- **Component 2 (Resource Service)**: Port `8001` (Notes Storage & Complete Mediation)
- **Component 3 (Processing Service)**: Port `8002` (Worker & HTML Export Engine)
- **External Dependency**: `html_note_formatter` wheel (`packages/html_note_formatter/dist/`)

---

## 1. Build & Environment Setup

```bash
# 1. Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install --upgrade pip
pip install fastapi uvicorn requests pyjwt pytest bandit flake8 build wheel

# 3. Build the helper package wheel
cd packages/html_note_formatter
python3 -m build --wheel
cd ../..

# 4. Verify package integrity against consumer manifest and install
python3 scripts/verify_integrity.py
pip install packages/html_note_formatter/dist/html_note_formatter-0.1.0-py3-none-any.whl
```

---

## 2. Seed

The application automatically seeds three in-memory accounts and test notes on startup:

| Username | Password | Role | Notes Access | Export Access | Delete Access |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `alice` | `password123` | Ordinary (`user`) | Alice's notes only (Read/Write) | Allowed | Denied (403) |
| `bob` | `password123` | Ordinary (`user`) | Bob's notes only (Read/Write) | Allowed | Denied (403) |
| `charlie` | `admin123` | Admin (`admin`) | All notes (Read Only) | Allowed | Allowed (200) |

---

## 3. Run

### Secure Baseline Mode (Default)
```bash
source venv/bin/activate
python run_services.py
```
*API Gateway Swagger UI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)*

### Vulnerable Mode (Demonstrating Planted Flaws)
```bash
source venv/bin/activate
python run_services.py --vulnerable
```

---

## 4. Test & Verification

### A. Functional & Authorization Test Suite (5/5 passing)
```bash
source venv/bin/activate
pytest -v tests/test_flow.py
```

### B. Planted Vulnerability & Exploit Demonstration Suite
```bash
# In secure mode: all 4 attacks are blocked (401/403)
# In vulnerable mode: all 4 attacks succeed
source venv/bin/activate
pytest -s -v tests/test_vulnerabilities.py
```

### C. Static Security Analysis (Bandit)
```bash
source venv/bin/activate
bandit -r services/ -ll
```

### D. Experiment A — Supply Chain Tamper Demonstration
```bash
source venv/bin/activate
python3 scripts/demo_tamper.py
```

### E. Full Local Pipeline Simulation
```bash
./run_pipeline_local.sh
```

---

## Documentation & Lifecycle Plan
- **Initial Blueprint & Threat Model:** `docs/PLANNING_AND_STRIDE.md`
- **Supply Chain Integrity Report:** `docs/experiment_a_report.md`
- **Full Report (PDF):** `Softwaresec_Assigment1_utku.pdf`
