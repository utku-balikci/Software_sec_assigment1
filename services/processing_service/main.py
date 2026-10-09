import os
import sys
from pathlib import Path
from fastapi import FastAPI, HTTPException, Header, Response
from typing import Optional
import requests

try:
    from html_note_formatter import format_note_html
except ModuleNotFoundError:
    package_dir = Path(__file__).resolve().parent.parent.parent / "packages" / "html_note_formatter"
    sys.path.insert(0, str(package_dir))
    from html_note_formatter import format_note_html

app = FastAPI(title="Processing Service (Component 3)", version="1.0.0")

VULNERABLE_MODE = os.getenv("VULNERABLE_MODE", "false").lower() in ("true", "1", "yes")
RESOURCE_SERVICE_URL = os.getenv("RESOURCE_SERVICE_URL", "http://127.0.0.1:8001")

@app.get("/health")
def health():
    return {
        "status": "ok", 
        "service": "processing_service",
        "vulnerable_mode": VULNERABLE_MODE
    }

@app.post("/export/{note_id}")
def export_note(
    note_id: int, 
    x_user: Optional[str] = Header(None), 
    x_role: Optional[str] = Header("user")
):
    """
    Worker export functionality:
    1. Fetches raw note data from the Resource Service.
    2. Formats note using external helper package html_note_formatter.
    3. Returns formatted HTML.
    """
    # --- Compositional Vulnerability: Confused Deputy & Implicit Service Trust ---
    if VULNERABLE_MODE:
        # VULNERABLE: The Processing Service blindly trusts the caller without verifying
        # the originating user's token or permission, and queries Component 2 using an elevated
        # internal admin role (Confused Deputy).
        headers = {
            "X-User": "internal-exporter-service",
            "X-Role": "admin"
        }
    else:
        # SECURE: Strict caller identity propagation and Least Privilege
        if not x_user:
            raise HTTPException(status_code=401, detail="Missing user identity header")
        headers = {
            "X-User": x_user,
            "X-Role": x_role
        }

    try:
        resp = requests.get(f"{RESOURCE_SERVICE_URL}/notes/{note_id}", headers=headers, timeout=5)
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Failed to communicate with Resource Service: {str(e)}")
        
    if resp.status_code != 200:
        detail_msg = "Error retrieving note"
        try:
            detail_msg = resp.json().get("detail", detail_msg)
        except Exception:
            pass
        raise HTTPException(status_code=resp.status_code, detail=detail_msg)
        
    note_data = resp.json()
    
    html_content = format_note_html(
        note_id=note_data["id"],
        title=note_data["title"],
        content=note_data["content"],
        author=note_data["owner"]
    )
    
    return Response(content=html_content, media_type="text/html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8002)
