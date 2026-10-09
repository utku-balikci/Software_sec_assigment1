import os
from fastapi import FastAPI, HTTPException, Header, status
from pydantic import BaseModel
from typing import Optional, List, Dict

app = FastAPI(title="Resource Service (Component 2)", version="1.0.0")

# Vulnerability Toggle: Controlled via VULNERABLE_MODE environment variable
VULNERABLE_MODE = os.getenv("VULNERABLE_MODE", "false").lower() in ("true", "1", "yes")

class NoteCreate(BaseModel):
    title: str
    content: str

class NoteResponse(BaseModel):
    id: int
    title: str
    content: str
    owner: str

# In-memory note storage seeded with initial notes
notes_db: Dict[int, Dict] = {
    1: {"id": 1, "title": "Alice's Secret Project", "content": "Confidential plan for Q4 security review.", "owner": "alice"},
    2: {"id": 2, "title": "Bob's Work Log", "content": "Implemented new user telemetry module.", "owner": "bob"}
}
next_note_id = 3

@app.get("/health")
def health():
    return {
        "status": "ok", 
        "service": "resource_service",
        "vulnerable_mode": VULNERABLE_MODE
    }

@app.post("/notes", response_model=NoteResponse, status_code=status.HTTP_201_CREATED)
def create_note(note: NoteCreate, x_user: Optional[str] = Header(None)):
    global next_note_id
    if not x_user:
        raise HTTPException(status_code=401, detail="Missing user identity header")
    
    new_note = {
        "id": next_note_id,
        "title": note.title,
        "content": note.content,
        "owner": x_user
    }
    notes_db[next_note_id] = new_note
    next_note_id += 1
    return new_note

@app.get("/notes", response_model=List[NoteResponse])
def list_notes(x_user: Optional[str] = Header(None), x_role: Optional[str] = Header("user")):
    if not x_user:
        raise HTTPException(status_code=401, detail="Missing user identity header")
    
    # Charlie (Admin) has Read Only view across all notes; Ordinary users only see their own
    if x_role == "admin":
        return list(notes_db.values())
    
    return [note for note in notes_db.values() if note["owner"] == x_user]

@app.get("/notes/{note_id}", response_model=NoteResponse)
def get_note(note_id: int, x_user: Optional[str] = Header(None), x_role: Optional[str] = Header("user")):
    if note_id not in notes_db:
        raise HTTPException(status_code=404, detail="Note not found")
    
    note = notes_db[note_id]
    
    # --- Planted Vulnerability 1: CWE-862 (Missing Authorization / IDOR) ---
    if VULNERABLE_MODE:
        # VULNERABLE: Omits ownership verification. Any authenticated user can read any note ID.
        return note
    
    # --- SECURE: Complete Mediation & Least Privilege ---
    if x_role != "admin" and note["owner"] != x_user:
        raise HTTPException(status_code=403, detail="Forbidden: You do not own this note")
        
    return note

@app.delete("/notes/{note_id}")
def delete_note(note_id: int, x_user: Optional[str] = Header(None), x_role: Optional[str] = Header("user")):
    if note_id not in notes_db:
        raise HTTPException(status_code=404, detail="Note not found")
    
    note = notes_db[note_id]
    
    # Access Control Matrix:
    # Feature 'Delete Any Note': Ordinary users (Denied), Admin (Allowed)
    if x_role != "admin":
        raise HTTPException(status_code=403, detail="Forbidden: Ordinary users cannot delete notes per policy")

    deleted = notes_db.pop(note_id)
    return {"message": f"Note {note_id} deleted successfully", "note": deleted}

# --- Planted Vulnerability 2: CWE-209 (Information Exposure Through Error / Debug Messages) ---
@app.get("/debug/environment")
def debug_environment():
    if VULNERABLE_MODE:
        # VULNERABLE: Exposes raw environment variables, process details, and in-memory dumps
        return {
            "status": "vulnerable_debug_exposure",
            "environment": dict(os.environ),
            "all_notes": notes_db
        }
    # SECURE: Blocked in production / secure mode
    raise HTTPException(status_code=403, detail="Access denied: Debug endpoints are disabled in secure mode")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8001)
