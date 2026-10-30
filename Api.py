
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from Backend import SQLiteBackend
from tools import execute_tool
from assistant import Assistant

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

backend = SQLiteBackend()
assistant = Assistant()
embedder = assistant.embedder


class RecordIn(BaseModel):
    type: str
    title: str
    date: Optional[str] = None
    is_completed: bool = False

class RecordUpdate(BaseModel):
    title: Optional[str] = None
    date: Optional[str] = None
    clear_date: Optional[bool] = None
    is_completed: Optional[bool] = None
    type: Optional[str] = None

class ChatIn(BaseModel):
    text: str

@app.get("/events")
def list_events(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    type: Optional[str] = None,
    is_completed: Optional[bool] = None,
):
    df = datetime.fromisoformat(date_from) if date_from else None
    dt = datetime.fromisoformat(date_to) if date_to else None
    return backend.search_records(
        record_type=type,
        date_from=df,
        date_to=dt,
        is_completed=is_completed,
        top_k=1000,
    )
@app.post("/chat")
def chat(payload: ChatIn):
    reply = assistant.handle(payload.text)
    return {"reply": reply}