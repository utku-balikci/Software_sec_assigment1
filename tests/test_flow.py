import pytest
import requests
import time

GATEWAY_URL = "http://127.0.0.1:8000"

def get_auth_token(username, password):
    resp = requests.post(f"{GATEWAY_URL}/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, f"Login failed for {username}: {resp.text}"
    return resp.json()["access_token"]

def test_login_flow():
    token_alice = get_auth_token("alice", "password123")
    token_bob = get_auth_token("bob", "password123")
    token_charlie = get_auth_token("charlie", "admin123")
    assert token_alice is not None
    assert token_bob is not None
    assert token_charlie is not None

def test_functionality_1_create_note():
    token_alice = get_auth_token("alice", "password123")
    headers = {"Authorization": f"Bearer {token_alice}"}
    
    note_payload = {
        "title": "Alice Special Research",
        "content": "Zero-day vulnerability notes and findings."
    }
    resp = requests.post(f"{GATEWAY_URL}/notes", json=note_payload, headers=headers)
    assert resp.status_code == 201
    created = resp.json()
    assert created["title"] == note_payload["title"]
    assert created["owner"] == "alice"

def test_functionality_2_view_note_and_authorization():
    token_alice = get_auth_token("alice", "password123")
    token_bob = get_auth_token("bob", "password123")
    
    # Alice views her seeded note 1
    resp_alice = requests.get(f"{GATEWAY_URL}/notes/1", headers={"Authorization": f"Bearer {token_alice}"})
    assert resp_alice.status_code == 200
    assert resp_alice.json()["id"] == 1
    assert resp_alice.json()["owner"] == "alice"
    
    # Bob attempts to view Alice's note 1 -> Denied (403 Forbidden)
    resp_bob = requests.get(f"{GATEWAY_URL}/notes/1", headers={"Authorization": f"Bearer {token_bob}"})
    assert resp_bob.status_code == 403

def test_functionality_3_export_note():
    token_alice = get_auth_token("alice", "password123")
    headers = {"Authorization": f"Bearer {token_alice}"}
    
    # Alice requests export for note 1
    # App API -> Processing Service -> Resource Service -> html_note_formatter -> HTML response
    resp = requests.post(f"{GATEWAY_URL}/notes/1/export", headers=headers)
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")
    assert ("Alice's Secret Project" in resp.text or "Alice&#x27;s Secret Project" in resp.text)
    assert "Confidential plan for Q4 security review." in resp.text
    assert "<!DOCTYPE html>" in resp.text

def test_admin_and_delete_permissions():
    token_alice = get_auth_token("alice", "password123")
    token_charlie = get_auth_token("charlie", "admin123")
    
    # Alice attempts to delete note 1 -> Denied (403 Forbidden)
    resp_del_alice = requests.delete(f"{GATEWAY_URL}/notes/1", headers={"Authorization": f"Bearer {token_alice}"})
    assert resp_del_alice.status_code == 403
    
    # Create a test note to be deleted by admin
    create_resp = requests.post(
        f"{GATEWAY_URL}/notes", 
        json={"title": "Temporary Note", "content": "To be deleted"},
        headers={"Authorization": f"Bearer {token_alice}"}
    )
    temp_note_id = create_resp.json()["id"]

    # Admin (Charlie) deletes the note -> Allowed
    resp_del_admin = requests.delete(f"{GATEWAY_URL}/notes/{temp_note_id}", headers={"Authorization": f"Bearer {token_charlie}"})
    assert resp_del_admin.status_code == 200
