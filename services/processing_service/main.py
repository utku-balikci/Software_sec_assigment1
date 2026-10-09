import os
import sys
from pathlib import Path
from fastapi import FastAPI, HTTPException, Header, Response
from typing import Optional
import requests

try:
    from html_note_formatter import format_note_html
except ModuleNotFoundError:
    # Fallback to local package directory if executed outside the venv
    package_dir = Path(__file__).resolve().parent.parent.parent / "packages" / "html_note_formatter"
    sys.path.insert(0, str(package_dir))
    from html_note_formatter import format_note_html

app = FastAPI(title="Processing Service (Component 3)", version="1.0.0")

RESOURCE_SERVICE_URL = os.getenv("RESOURCE_SERVICE_URL", "http://127.0.0.1:8001")

@app.get("/health")
def health():
    return {"status": "ok", "service": "processing_service"}

@app.post("/export/{note_id}")
def export_note(
    note_id: int, 
    x_user: Optional[str] = Header(None), 
    x_role: Optional[str] = Header("user")
):
    """
    Worker export functionality:
    1. Fetches raw note data from the Resource Service.
    2. Uses html_note_formatter external dependency to wrap note in HTML.
    3. Returns formatted HTML.
    """
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
        raise HTTPException(status_code=resp.status_code, detail=resp.json().get("detail", "Error retrieving note"))
        
    note_data = resp.json()
    
    # Process and format note with the External Helper Package
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
