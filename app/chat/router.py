from __future__ import annotations

import uuid
from fastapi import APIRouter
from pydantic import BaseModel

from app.chat.llm_chat import chat
from app.core.convlog import log_exchange

router = APIRouter(tags=["chat"])

_sessions: dict[str, list[dict]] = {}


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    reply: str
    session_id: str


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(payload: ChatRequest) -> ChatResponse:
    session_id = payload.session_id or str(uuid.uuid4())
    if session_id not in _sessions:
        _sessions[session_id] = []

    history = _sessions[session_id]
    result = chat(message=payload.message.strip(), history=history)

    history.append({"role": "user", "content": payload.message.strip()})
    history.append({"role": "assistant", "content": result["reply"]})
    if len(history) > 20:
        _sessions[session_id] = history[-20:]

    # Trajno beleženje za statistiko — nikoli ne podre klepeta.
    try:
        log_exchange(session_id, payload.message.strip(), result["reply"])
    except Exception:
        pass

    return ChatResponse(reply=result["reply"], session_id=session_id)
