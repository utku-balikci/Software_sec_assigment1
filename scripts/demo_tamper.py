#!/usr/bin/env python3
"""
Tamper Demo Script
==================
Demonstrates the integrity gate in action by:
  1. Saving a backup of the original wheel file
  2. Replacing the wheel with tampered bytes (same filename, different content)
  3. Running the integrity verifier — which must FAIL
  4. Restoring the original wheel
  5. Running the integrity verifier again — which must PASS

Usage:
    python3 scripts/demo_tamper.py
"""

import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
WHEEL_PATH   = PROJECT_ROOT / "packages" / "html_note_formatter" / "dist" / "html_note_formatter-0.1.0-py3-none-any.whl"
BACKUP_PATH  = WHEEL_PATH.with_suffix(".whl.original_backup")
VERIFIER     = PROJECT_ROOT / "scripts" / "verify_integrity.py"

RESET  = "\033[0m"
CYAN   = "\033[96m"
RED    = "\033[91m"
GREEN  = "\033[92m"
BOLD   = "\033[1m"
SEP    = "=" * 60


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def run_verifier() -> int:
    result = subprocess.run([sys.executable, str(VERIFIER)])
    return result.returncode


def main():
    print(f"\n{BOLD}{CYAN}{SEP}")
    print("  SUPPLY CHAIN INTEGRITY — TAMPER DEMONSTRATION")
    print(f"{SEP}{RESET}\n")

    # ── Step 1: Show original digest ──────────────────────────────────────
    print(f"{BOLD}[Step 1] Original wheel digest:{RESET}")
    print(f"  {sha256(WHEEL_PATH)}\n")

    # ── Step 2: Run verifier on clean artifact ────────────────────────────
    print(f"{BOLD}[Step 2] Running integrity gate on ORIGINAL (unmodified) wheel...{RESET}")
    rc = run_verifier()
    assert rc == 0, "Expected PASS on original — something is wrong with the manifest."

    # ── Step 3: Tamper — replace bytes, keep same filename & version ──────
    print(f"\n{SEP}")
    print(f"{BOLD}{RED}[Step 3] TAMPERING: replacing wheel contents with malicious bytes...{RESET}")
    shutil.copy2(WHEEL_PATH, BACKUP_PATH)   # save original
    WHEEL_PATH.write_bytes(
        b"TAMPERED PAYLOAD - attacker-controlled bytes injected here!\n"
        b"Same filename, same version, completely different content.\n"
    )
    print(f"  Tampered digest: {sha256(WHEEL_PATH)}")
    print(f"  (filename unchanged: {WHEEL_PATH.name})\n")

    # ── Step 4: Run verifier — must FAIL ─────────────────────────────────
    print(f"{BOLD}[Step 4] Running integrity gate on TAMPERED wheel...{RESET}")
    rc = run_verifier()
    if rc != 0:
        print(f"{RED}{BOLD}  ✓ Gate correctly BLOCKED the tampered artifact.{RESET}\n")
    else:
        print(f"{RED}{BOLD}  ✗ Gate unexpectedly PASSED — this is a bug!{RESET}\n")

    # ── Step 5: Restore original ──────────────────────────────────────────
    print(f"{SEP}")
    print(f"{BOLD}[Step 5] Restoring original wheel...{RESET}")
    shutil.copy2(BACKUP_PATH, WHEEL_PATH)
    BACKUP_PATH.unlink()
    print(f"  Restored digest: {sha256(WHEEL_PATH)}\n")

    # ── Step 6: Verify clean again ────────────────────────────────────────
    print(f"{BOLD}[Step 6] Running integrity gate on RESTORED wheel...{RESET}")
    rc = run_verifier()
    if rc == 0:
        print(f"{GREEN}{BOLD}  ✓ Gate correctly PASSED after restore.{RESET}\n")
    else:
        print(f"{RED}{BOLD}  ✗ Gate failed on restored wheel — this is a bug!{RESET}\n")

    print(f"{BOLD}{CYAN}{SEP}")
    print("  DEMONSTRATION COMPLETE")
    print(f"{SEP}{RESET}\n")


if __name__ == "__main__":
    main()
