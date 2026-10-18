#!/usr/bin/env python3
"""
Experiment A — Documentation Generator
=======================================
Runs the integrity gate demo and captures all output into a timestamped
Markdown report saved to docs/experiment_a_report.md.

Usage:
    python3 scripts/generate_report.py
"""

import hashlib
import io
import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT  = Path(__file__).resolve().parent.parent
MANIFEST_PATH = PROJECT_ROOT / "manifest" / "approved_packages.json"
WHEEL_PATH    = PROJECT_ROOT / "packages" / "html_note_formatter" / "dist" / "html_note_formatter-0.1.0-py3-none-any.whl"
BACKUP_PATH   = WHEEL_PATH.with_suffix(".whl.bak")
VERIFIER      = PROJECT_ROOT / "scripts" / "verify_integrity.py"
REPORT_PATH   = PROJECT_ROOT / "docs" / "experiment_a_report.md"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def run_verifier() -> tuple[int, str]:
    """Run the verifier and return (exit_code, output)."""
    result = subprocess.run(
        [sys.executable, str(VERIFIER)],
        capture_output=True,
        text=True
    )
    return result.returncode, result.stdout + result.stderr


def main():
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[*] Generating Experiment A report at {timestamp}...")

    # Load manifest
    with open(MANIFEST_PATH) as f:
        manifest = json.load(f)
    pkg = manifest["packages"][0]

    original_digest = sha256(WHEEL_PATH)

    # ── Step 1: Run verifier on clean artifact ────────────────────────────
    rc_clean, out_clean = run_verifier()

    # ── Step 2: Tamper ────────────────────────────────────────────────────
    shutil.copy2(WHEEL_PATH, BACKUP_PATH)
    WHEEL_PATH.write_bytes(
        b"TAMPERED PAYLOAD - attacker-controlled bytes injected here!\n"
        b"Same filename, same version, completely different content.\n"
    )
    tampered_digest = sha256(WHEEL_PATH)
    rc_tampered, out_tampered = run_verifier()

    # ── Step 3: Restore ───────────────────────────────────────────────────
    shutil.copy2(BACKUP_PATH, WHEEL_PATH)
    BACKUP_PATH.unlink()
    restored_digest = sha256(WHEEL_PATH)
    rc_restored, out_restored = run_verifier()

    # ── Build Markdown report ─────────────────────────────────────────────
    status_clean    = "✅ PASSED" if rc_clean    == 0 else "❌ FAILED"
    status_tampered = "✅ PASSED" if rc_tampered == 0 else "❌ BLOCKED"
    status_restored = "✅ PASSED" if rc_restored == 0 else "❌ FAILED"

    report = f"""# Experiment A — Supply Chain Integrity Gate

**Generated:** {timestamp}  
**Project:** Secure Notes & Export System  
**Assignment:** Software Security — Assignment 1

---

## Overview

This experiment demonstrates a **consumer-controlled package integrity manifest**
that verifies a supplier artifact (a Python wheel) against a pre-approved
SHA-256 digest before it is installed in the build pipeline.

The key security property: even if an attacker replaces the wheel bytes
while keeping the same filename and version string, the integrity gate detects
the mismatch and **blocks installation**.

---

## Architecture

```
manifest/
  approved_packages.json    ← read-only (chmod 444), owned by consumer
scripts/
  verify_integrity.py       ← integrity gate (run before pip install)
  demo_tamper.py            ← tamper demonstration
Jenkinsfile                 ← "Package Integrity Gate" stage added
packages/
  html_note_formatter/
    dist/
      html_note_formatter-0.1.0-py3-none-any.whl   ← supplier artifact
```

**Trust boundary:** The manifest lives outside the supplier's write path.
The CI pipeline sets `chmod 444` on the manifest at checkout, so no build
step (including the supplier's own tooling) can modify the approved digests.

---

## Approval Manifest

File: `manifest/approved_packages.json`  
Permissions: `-r--r--r--` (read-only for all)

```json
{json.dumps(manifest, indent=2)}
```

---

## Run 1 — Original (Unmodified) Artifact

**Scenario:** Artifact is exactly as the consumer approved.

| Field    | Value |
|----------|-------|
| Filename | `{WHEEL_PATH.name}` |
| SHA-256  | `{original_digest}` |
| Result   | {status_clean} |

```
{out_clean.strip()}
```

---

## Run 2 — Tampered Artifact *(same filename, different bytes)*

**Scenario:** An attacker replaces the wheel contents with a malicious payload
while keeping the filename `{WHEEL_PATH.name}` and version `{pkg['version']}`
unchanged — simulating a supply chain substitution attack.

| Field    | Value |
|----------|-------|
| Filename | `{WHEEL_PATH.name}` *(unchanged)* |
| SHA-256  | `{tampered_digest}` *(changed!)* |
| Result   | {status_tampered} |

```
{out_tampered.strip()}
```

> **Gate behaviour:** Exit code `{rc_tampered}` — pipeline aborts, `pip install` is never reached.

---

## Run 3 — Restored Original Artifact

**Scenario:** The original approved artifact is restored.

| Field    | Value |
|----------|-------|
| Filename | `{WHEEL_PATH.name}` |
| SHA-256  | `{restored_digest}` |
| Result   | {status_restored} |

```
{out_restored.strip()}
```

---

## Jenkinsfile Pipeline Stage

The `Package Integrity Gate` stage was inserted **between** environment setup
and package installation:

```groovy
stage('Package Integrity Gate') {{
    steps {{
        echo 'Verifying supplier artifact against consumer-controlled manifest...'
        sh '''
            # Lock the manifest so the supplier cannot alter it during the build
            chmod 444 manifest/approved_packages.json

            . venv/bin/activate

            # Build the wheel from source so we have the artifact to verify
            cd packages/html_note_formatter
            python -m build --wheel
            cd ../..

            # Run integrity check — pipeline aborts here if digest mismatches
            python3 scripts/verify_integrity.py

            # Gate passed: safe to install
            pip install packages/html_note_formatter/dist/*.whl
        '''
    }}
}}
```

If `verify_integrity.py` exits with code `1`, the Jenkins stage fails and
no subsequent stages (static analysis, tests) are executed.

---

## Security Properties Demonstrated

| Property | Mechanism |
|---|---|
| **Consumer-controlled manifest** | `approved_packages.json` is owned and written by the consumer; `chmod 444` prevents supplier modification during build |
| **Cryptographic binding** | SHA-256 digest ties the approved *identity* (name + version) to specific *bytes* |
| **Pre-install gate** | Verifier runs before `pip install`; a non-zero exit aborts the pipeline |
| **Tamper detection** | Any byte-level change to the artifact produces a different digest and is immediately caught |
| **Self-healing demo** | `demo_tamper.py` shows PASS → BLOCK → PASS lifecycle without permanent side effects |
"""

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report, encoding="utf-8")

    print(f"[✓] Report written to: {REPORT_PATH}")
    print(f"    Clean  : {status_clean}")
    print(f"    Tamper : {status_tampered}")
    print(f"    Restore: {status_restored}")


if __name__ == "__main__":
    main()
