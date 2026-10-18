# Experiment A — Supply Chain Integrity Gate

**Generated:** 2026-10-18 20:12:34  
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
{
  "_comment": "Consumer-controlled approval manifest. This file must be kept read-only and outside supplier write permissions.",
  "schema_version": "1.0",
  "packages": [
    {
      "name": "html_note_formatter",
      "version": "0.1.0",
      "source": "packages/html_note_formatter/dist/html_note_formatter-0.1.0-py3-none-any.whl",
      "algorithm": "sha256",
      "digest": "c78738054c6302873d424ea2c14ecd05a214140e9dfd3ba12e417be734ab0f55"
    }
  ]
}
```

---

## Run 1 — Original (Unmodified) Artifact

**Scenario:** Artifact is exactly as the consumer approved.

| Field    | Value |
|----------|-------|
| Filename | `html_note_formatter-0.1.0-py3-none-any.whl` |
| SHA-256  | `c78738054c6302873d424ea2c14ecd05a214140e9dfd3ba12e417be734ab0f55` |
| Result   | ✅ PASSED |

```
[1m=== Package Integrity Gate ===[0m
  Manifest : /Users/utkubalikci/Desktop/Software_sec_assigment1/manifest/approved_packages.json

  [1mPackage :[0m html_note_formatter v0.1.0
  [1mArtifact:[0m /Users/utkubalikci/Desktop/Software_sec_assigment1/packages/html_note_formatter/dist/html_note_formatter-0.1.0-py3-none-any.whl
  [1mExpected:[0m c78738054c6302873d424ea2c14ecd05a214140e9dfd3ba12e417be734ab0f55
  [1mActual  :[0m c78738054c6302873d424ea2c14ecd05a214140e9dfd3ba12e417be734ab0f55
  [92m[PASS] Digest matches — artifact is authentic.[0m

[92m[1mIntegrity gate PASSED. Proceeding with installation.[0m
```

---

## Run 2 — Tampered Artifact *(same filename, different bytes)*

**Scenario:** An attacker replaces the wheel contents with a malicious payload
while keeping the filename `html_note_formatter-0.1.0-py3-none-any.whl` and version `0.1.0`
unchanged — simulating a supply chain substitution attack.

| Field    | Value |
|----------|-------|
| Filename | `html_note_formatter-0.1.0-py3-none-any.whl` *(unchanged)* |
| SHA-256  | `053ec0614abc95bd4c8d3c412fef9901521245428ebe723a70be7d2a0c83ba56` *(changed!)* |
| Result   | ❌ BLOCKED |

```
[1m=== Package Integrity Gate ===[0m
  Manifest : /Users/utkubalikci/Desktop/Software_sec_assigment1/manifest/approved_packages.json

  [1mPackage :[0m html_note_formatter v0.1.0
  [1mArtifact:[0m /Users/utkubalikci/Desktop/Software_sec_assigment1/packages/html_note_formatter/dist/html_note_formatter-0.1.0-py3-none-any.whl
  [1mExpected:[0m c78738054c6302873d424ea2c14ecd05a214140e9dfd3ba12e417be734ab0f55
  [1mActual  :[0m 053ec0614abc95bd4c8d3c412fef9901521245428ebe723a70be7d2a0c83ba56
  [91m[FAIL] Digest MISMATCH — artifact has been tampered with![0m
  [91m       Installation blocked to protect supply chain integrity.[0m

[91m[1mIntegrity gate FAILED. Pipeline aborted.[0m
```

> **Gate behaviour:** Exit code `1` — pipeline aborts, `pip install` is never reached.

---

## Run 3 — Restored Original Artifact

**Scenario:** The original approved artifact is restored.

| Field    | Value |
|----------|-------|
| Filename | `html_note_formatter-0.1.0-py3-none-any.whl` |
| SHA-256  | `c78738054c6302873d424ea2c14ecd05a214140e9dfd3ba12e417be734ab0f55` |
| Result   | ✅ PASSED |

```
[1m=== Package Integrity Gate ===[0m
  Manifest : /Users/utkubalikci/Desktop/Software_sec_assigment1/manifest/approved_packages.json

  [1mPackage :[0m html_note_formatter v0.1.0
  [1mArtifact:[0m /Users/utkubalikci/Desktop/Software_sec_assigment1/packages/html_note_formatter/dist/html_note_formatter-0.1.0-py3-none-any.whl
  [1mExpected:[0m c78738054c6302873d424ea2c14ecd05a214140e9dfd3ba12e417be734ab0f55
  [1mActual  :[0m c78738054c6302873d424ea2c14ecd05a214140e9dfd3ba12e417be734ab0f55
  [92m[PASS] Digest matches — artifact is authentic.[0m

[92m[1mIntegrity gate PASSED. Proceeding with installation.[0m
```

---

## Jenkinsfile Pipeline Stage

The `Package Integrity Gate` stage was inserted **between** environment setup
and package installation:

```groovy
stage('Package Integrity Gate') {
    steps {
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
    }
}
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
