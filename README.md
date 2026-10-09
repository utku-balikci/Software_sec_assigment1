# Secure Notes & Export System

A secure microservices application written in Python (FastAPI) demonstrating the **3-component architecture**, role-based access control (RBAC), and external packaging.

## Architecture

- **Component 1 (Application API)**: Port `8000` (Gateway & JWT Auth)
- **Component 2 (Resource Service)**: Port `8001` (Notes Database & Ownership Enforcement)
- **Component 3 (Processing Service)**: Port `8002` (Worker & HTML Export Engine)
- **External Dependency**: `html_note_formatter` (Packaged wheel inside `packages/html_note_formatter/dist`)

---

## Quick Start

### 1. Activate Environment
```bash
cd "/Users/utkubalikci/Desktop/Software sec 1"
source venv/bin/activate
```

### 2. Run All 3 Services Concurrently
```bash
python run_services.py
```

### 3. Run Automated Tests
In a separate terminal:
```bash
source venv/bin/activate
pytest -v tests/test_flow.py
```

---

## Seeded Users & Credentials

| Username | Password | Role | Notes Access | Export Access | Delete Access |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `alice` | `password123` | Ordinary (`user`) | Alice's notes only (Read/Write) | Allowed | Denied |
| `bob` | `password123` | Ordinary (`user`) | Bob's notes only (Read/Write) | Allowed | Denied |
| `charlie` | `admin123` | Admin (`admin`) | All notes (Read Only) | Allowed | Allowed |

---

## Documentation
- Complete SSDLC Blueprint & STRIDE Threat Model: [`docs/PLANNING_AND_STRIDE.md`](file:///Users/utkubalikci/Desktop/Software%20sec%201/docs/PLANNING_AND_STRIDE.md)
