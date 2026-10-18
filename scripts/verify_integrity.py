#!/usr/bin/env python3
"""
Integrity Gate: Package Manifest Verifier
==========================================
Reads the consumer-controlled approval manifest and verifies that every
listed package artifact matches its recorded digest before installation.

Usage:
    python3 scripts/verify_integrity.py

Exit codes:
    0  — All packages passed integrity check (safe to install)
    1  — One or more packages failed (pipeline must abort)
"""

import hashlib
import json
import sys
from pathlib import Path

# Resolve paths relative to the project root (one level up from scripts/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = PROJECT_ROOT / "manifest" / "approved_packages.json"

RESET  = "\033[0m"
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
BOLD   = "\033[1m"


def compute_digest(algorithm: str, file_path: Path) -> str:
    h = hashlib.new(algorithm)
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_manifest(manifest_path: Path) -> bool:
    print(f"\n{BOLD}=== Package Integrity Gate ==={RESET}")
    print(f"  Manifest : {manifest_path}\n")

    if not manifest_path.exists():
        print(f"{RED}[FATAL] Manifest not found: {manifest_path}{RESET}")
        return False

    with open(manifest_path, "r") as f:
        manifest = json.load(f)

    packages = manifest.get("packages", [])
    if not packages:
        print(f"{YELLOW}[WARN] No packages listed in manifest.{RESET}")
        return True

    all_passed = True

    for entry in packages:
        name      = entry["name"]
        version   = entry["version"]
        source    = entry["source"]
        algorithm = entry.get("algorithm", "sha256")
        expected  = entry["digest"]

        artifact_path = PROJECT_ROOT / source

        print(f"  {BOLD}Package :{RESET} {name} v{version}")
        print(f"  {BOLD}Artifact:{RESET} {artifact_path}")

        if not artifact_path.exists():
            print(f"  {RED}[FAIL] Artifact file not found!{RESET}\n")
            all_passed = False
            continue

        actual = compute_digest(algorithm, artifact_path)

        print(f"  {BOLD}Expected:{RESET} {expected}")
        print(f"  {BOLD}Actual  :{RESET} {actual}")

        if actual == expected:
            print(f"  {GREEN}[PASS] Digest matches — artifact is authentic.{RESET}\n")
        else:
            print(f"  {RED}[FAIL] Digest MISMATCH — artifact has been tampered with!{RESET}")
            print(f"  {RED}       Installation blocked to protect supply chain integrity.{RESET}\n")
            all_passed = False

    return all_passed


def main():
    passed = verify_manifest(MANIFEST_PATH)
    if passed:
        print(f"{GREEN}{BOLD}Integrity gate PASSED. Proceeding with installation.{RESET}\n")
        sys.exit(0)
    else:
        print(f"{RED}{BOLD}Integrity gate FAILED. Pipeline aborted.{RESET}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
