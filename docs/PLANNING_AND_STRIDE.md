# Secure Notes & Export System: Step 1 Blueprint & STRIDE Threat Model

## 1. Domain & Protected Resources
- **Domain**: Secure Notes & Export System.
- **Protected Resources**:
  1. **Private Text Notes**: Notes owned by individual users containing confidential text.
  2. **Formatted HTML Exports**: Formatted output files generated dynamically from private notes.

---

## 2. Architecture: 3 Microservices + 1 External Dependency
The architecture is structured across three isolated services running on distinct network ports:

1. **Application API (Component 1) - Port 8000**
   - **Role**: API Gateway & Authentication Service.
   - **Function**: Authenticates users (Alice, Bob, Charlie), validates credentials, issues signed JWT session tokens, and proxies authorized calls to internal microservices.
2. **Resource Service (Component 2) - Port 8001**
   - **Role**: Data Storage & Authorization Enforcement.
   - **Function**: Persists user notes, enforces ownership rules, and prevents unauthorized cross-user data access.
3. **Processing Service (Component 3) - Port 8002**
   - **Role**: Worker & Formatter.
   - **Function**: Receives export jobs, contacts the Resource Service over internal REST channels to fetch raw note data, and transforms it into HTML reports.
4. **External Helper Package (Dependency)**
   - **Package**: `html_note_formatter` (built as `html_note_formatter-0.1.0-py3-none-any.whl`).
   - **Function**: Library providing HTML sanitization and styling templates to wrap raw text into structured export documents.

---

## 3. The 3 Core Functionalities & Data Flow
1. **Functionality 1: Create a Note**
   - Flow: `User (Client)` $\rightarrow$ `App API` $\rightarrow$ `Resource Service`
   - Description: Authenticated user posts title/content. App API passes user identity (`X-User`), and Resource Service stores note linked to the creator.
2. **Functionality 2: View a Note**
   - Flow: `User (Client)` $\rightarrow$ `App API` $\rightarrow$ `Resource Service`
   - Description: User requests specific note ID. App API routes request; Resource Service validates that the requester owns the note (or is Admin) before returning data.
3. **Functionality 3: Export a Note (Touches All 3 Components + Dependency)**
   - Flow: `User (Client)` $\rightarrow$ `App API` $\rightarrow$ `Processing Service` $\rightarrow$ `Resource Service` $\rightarrow$ `html_note_formatter` $\rightarrow$ `Formatted HTML returned to User`
   - Description: The export request enters the gateway, is dispatched to the worker, which queries the database layer for note details, applies the external helper package, and renders the result.

---

## 4. Access Control Matrix & Seeded Accounts

| Role / User | Resource: Alice's Notes | Resource: Bob's Notes | Feature: Trigger Export | Feature: Delete Any Note |
| :--- | :--- | :--- | :--- | :--- |
| **Ordinary (Alice)** (`alice:password123`) | **Read / Write** | **Denied** | **Allowed** | **Denied** |
| **Ordinary (Bob)** (`bob:password123`) | **Denied** | **Read / Write** | **Allowed** | **Denied** |
| **Admin (Charlie)** (`charlie:admin123`) | **Read Only** | **Read Only** | **Allowed** | **Allowed** |

---

## 5. Initial STRIDE Threat Model

| STRIDE Category | Threat Description | Affected Component / Flow | Baseline Mitigation / Analysis |
| :--- | :--- | :--- | :--- |
| **S - Spoofing** | An attacker creates forged JWT tokens or fakes the `X-User` header to impersonate Alice or Charlie. | Client $\rightarrow$ App API $\rightarrow$ Downstream Services | Cryptographic signature on JWTs using secure secret; internal services only accept verified headers from gateway. *(Target for CWE-798 if secret is exposed)* |
| **T - Tampering** | An attacker modifies note payload or alters internal export instructions in transit. | App API $\leftrightarrow$ Resource / Processing Services | Strict schema validation with Pydantic; TLS between microservices. |
| **R - Repudiation** | A user deletes another user's note or exports confidential data and denies action. | Resource Service & App API | Structured audit logging recording timestamps, caller IDs, and note IDs. |
| **I - Information Disclosure** | Unauthorized users reading notes belonging to other tenants (IDOR). | Resource Service (`GET /notes/{id}`) | Enforce ownership matching (`note.owner == requester`). *(Target for CWE-862)* |
| **D - Denial of Service** | Flooding export requests with large payloads exhausting processing memory. | Processing Service | Timeout limits, payload size limits, asynchronous worker queues. |
| **E - Elevation of Privilege** | An ordinary user executing administrative endpoints (e.g. `DELETE /notes/{id}`). | App API & Resource Service | Role-Based Access Control (RBAC) inspecting `role == 'admin'` claims before routing sensitive actions. |

---

## 6. Documented Planted Vulnerabilities (3 Catalog + 1 Compositional)

The codebase implements a toggle switch (`VULNERABLE_MODE=true` or `python run_services.py --vulnerable`) to allow reproducible side-by-side evaluation between the vulnerable state and the hardened secure baseline.

### Vulnerability 1: CWE-798 (Use of Hard-coded Credentials)
- **Affected Component**: `services/app_api/main.py`
- **Flaw**: When vulnerable mode is active, the JWT signing secret is hardcoded (`"insecure-hardcoded-secret-key-cwe-798"`).
- **Exploitation**: An adversary inspects the application repository or binary, extracts the static signing key, and mints an offline arbitrary JWT claim granting admin access (`"sub": "charlie", "role": "admin"`), completely bypassing the password gate.
- **Defense / Mitigation**: In secure mode, secrets are strictly injected from runtime environment variables (`JWT_SECRET_KEY`) with high-entropy cryptographic generation.

### Vulnerability 2: CWE-862 (Missing Authorization / IDOR)
- **Affected Component**: `services/resource_service/main.py` (`GET /notes/{note_id}`)
- **Flaw**: The endpoint looks up the note by ID without verifying if `note["owner"] == x_user`.
- **Exploitation**: Bob logs in legitimately, discovers note IDs are sequential integers, and requests `GET /notes/1` (belonging to Alice). The Resource Service returns Alice's confidential note.
- **Defense / Mitigation**: Complete mediation is enforced: if `x_role != 'admin'`, the service asserts `note["owner"] == x_user`, returning `403 Forbidden` if mismatched.

### Vulnerability 3: CWE-209 (Information Exposure Through Debug / Error Dumps)
- **Affected Component**: `services/resource_service/main.py` (`GET /debug/environment`)
- **Flaw**: Exposes raw environment variables, process configurations, and in-memory note tables to unauthenticated requesters.
- **Exploitation**: An attacker discovers the debug route and immediately dumps all tenant notes and environment variables without needing any user credentials.
- **Defense / Mitigation**: The endpoint is disabled in production/secure mode, returning `403 Forbidden`.

### Vulnerability 4: Compositional Vulnerability (Confused Deputy & Inter-Service Implicit Trust)
- **Affected Component**: `services/processing_service/main.py` & inter-service interaction with `resource_service`
- **Flaw**: The Processing Service blindly trusts incoming internal network requests on port 8002 without verifying client authentication headers, and queries the Resource Service using an elevated internal admin role (`X-Role: admin`).
- **Exploitation**: An attacker with access to the internal network sends a direct request to `POST http://127.0.0.1:8002/export/1` bypassing the Application API Gateway completely. The Processing Service acts as a "Confused Deputy", fetches Alice's private note as admin, and renders it to the attacker.
- **Defense / Mitigation**: Principle of Least Privilege and Caller Context Propagation: Component 3 enforces the originating user's identity headers and forwards them directly to Component 2 without privilege escalation.

---

## 7. How to Reproduce & Verify

### Test 1: Verify All Defenses in Secure Baseline
```bash
# Terminal 1: Run in Secure Mode (Default)
python run_services.py

# Terminal 2: Run verification test
pytest -s -v tests/test_vulnerabilities.py
```
*Result: All 4 exploits are blocked (`[DEFENSE ACTIVE]`).*

### Test 2: Demonstrate All 4 Exploits in Vulnerable Mode
```bash
# Terminal 1: Run in Vulnerable Mode
python run_services.py --vulnerable

# Terminal 2: Run verification test
pytest -s -v tests/test_vulnerabilities.py
```
*Result: All 4 exploits succeed (`[EXPLOIT SUCCEEDED]`).*

