import os
import sys
import time
from typing import Optional, List
from fastapi import FastAPI, HTTPException, Depends, status, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import jwt
import requests

app = FastAPI(
    title="Application API Gateway (Component 1)",
    description="Gateway authenticating users, issuing JWT tokens, and routing requests to downstream microservices.",
    version="1.0.0"
)

# Vulnerability Toggle: Controlled via VULNERABLE_MODE environment variable
VULNERABLE_MODE = os.getenv("VULNERABLE_MODE", "false").lower() in ("true", "1", "yes")

# --- Planted Vulnerability 3: CWE-798 (Use of Hard-coded Credentials) ---
if VULNERABLE_MODE:
    # VULNERABLE: Known hardcoded secret committed into version control
    JWT_SECRET_KEY = "insecure-hardcoded-secret-key-cwe-798"
else:
    # SECURE: Production key loaded from secure runtime environment
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "prod-secure-key-92840918230912830918203918230918")

JWT_ALGORITHM = "HS256"

RESOURCE_SERVICE_URL = os.getenv("RESOURCE_SERVICE_URL", "http://127.0.0.1:8001")
PROCESSING_SERVICE_URL = os.getenv("PROCESSING_SERVICE_URL", "http://127.0.0.1:8002")

USERS_DB = {
    "alice": {"password": "password123", "role": "user", "name": "Alice"},
    "bob": {"password": "password123", "role": "user", "name": "Bob"},
    "charlie": {"password": "admin123", "role": "admin", "name": "Charlie"}
}

security = HTTPBearer()

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    role: str

class NoteCreate(BaseModel):
    title: str
    content: str

def create_access_token(data: dict) -> str:
    payload = data.copy()
    payload.update({"exp": time.time() + 3600})
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role")
        if username is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject")
        return {"username": username, "role": role}
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

@app.get("/health")
def health():
    return {
        "status": "ok", 
        "service": "app_api",
        "vulnerable_mode": VULNERABLE_MODE
    }

@app.post("/auth/login", response_model=TokenResponse)
def login(creds: LoginRequest):
    user = USERS_DB.get(creds.username)
    if not user or user["password"] != creds.password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
    
    token = create_access_token({"sub": creds.username, "role": user["role"]})
    return {
        "access_token": token,
        "token_type": "bearer",
        "username": creds.username,
        "role": user["role"]
    }

@app.post("/notes", status_code=status.HTTP_201_CREATED)
def create_note(note: NoteCreate, current_user: dict = Depends(get_current_user)):
    """Functionality 1: Create a Note (User -> App API -> Resource Service)"""
    headers = {"X-User": current_user["username"], "X-Role": current_user["role"]}
    try:
        resp = requests.post(
            f"{RESOURCE_SERVICE_URL}/notes",
            json=note.model_dump(),
            headers=headers,
            timeout=5
        )
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Resource service unavailable: {e}")

    if resp.status_code != 201:
        raise HTTPException(status_code=resp.status_code, detail=resp.json().get("detail", "Error creating note"))
    return resp.json()

@app.get("/notes")
def list_notes(current_user: dict = Depends(get_current_user)):
    """List notes accessible to current user"""
    headers = {"X-User": current_user["username"], "X-Role": current_user["role"]}
    try:
        resp = requests.get(f"{RESOURCE_SERVICE_URL}/notes", headers=headers, timeout=5)
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Resource service unavailable: {e}")

    return resp.json()

@app.get("/notes/{note_id}")
def get_note(note_id: int, current_user: dict = Depends(get_current_user)):
    """Functionality 2: View a Note (User -> App API -> Resource Service)"""
    headers = {"X-User": current_user["username"], "X-Role": current_user["role"]}
    try:
        resp = requests.get(f"{RESOURCE_SERVICE_URL}/notes/{note_id}", headers=headers, timeout=5)
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Resource service unavailable: {e}")

    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.json().get("detail", "Error fetching note"))
    return resp.json()

@app.delete("/notes/{note_id}")
def delete_note(note_id: int, current_user: dict = Depends(get_current_user)):
    """Delete a note (Permitted for Charlie Admin per matrix)"""
    headers = {"X-User": current_user["username"], "X-Role": current_user["role"]}
    try:
        resp = requests.delete(f"{RESOURCE_SERVICE_URL}/notes/{note_id}", headers=headers, timeout=5)
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Resource service unavailable: {e}")

    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.json().get("detail", "Deletion error"))
    return resp.json()

@app.post("/notes/{note_id}/export")
def export_note(note_id: int, current_user: dict = Depends(get_current_user)):
    """
    Functionality 3: Export a Note (Touches all 3 components):
    User -> App API -> Processing Service -> Resource Service -> Helper Package -> HTML
    """
    headers = {"X-User": current_user["username"], "X-Role": current_user["role"]}
    try:
        resp = requests.post(
            f"{PROCESSING_SERVICE_URL}/export/{note_id}",
            headers=headers,
            timeout=5
        )
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Processing service unavailable: {e}")

    if resp.status_code != 200:
        detail_msg = resp.text
        try:
            detail_msg = resp.json().get("detail", detail_msg)
        except Exception:
            pass
        raise HTTPException(status_code=resp.status_code, detail=detail_msg)

    return Response(content=resp.content, media_type="text/html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
