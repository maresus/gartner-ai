from pathlib import Path
import os

from dotenv import load_dotenv
load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")

from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.chat.router import router as chat_router
from app.rag.search import load_knowledge
from app.core.convlog import fetch as fetch_conversations

app = FastAPI(title="Gartner AI", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.on_event("startup")
def startup():
    kb_path = Path(__file__).parent / "knowledge.jsonl"
    count = load_knowledge(kb_path)
    print(f"[startup] Gartner AI — naloženih {count} znanj")


@app.get("/health")
def health():
    return {"status": "ok", "bot": "gartner-ai"}


@app.get("/", response_class=HTMLResponse)
def home():
    widget_html = static_dir / "widget.html"
    if widget_html.exists():
        return widget_html.read_text(encoding="utf-8")
    return "<h1>Gartner Bohinj AI</h1>"


app.include_router(chat_router)


@app.get("/api/admin/conversations")
def admin_conversations(
    hours: int = Query(default=25),
    limit: int = Query(default=5000),
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
):
    """Seznam pogovorov za statistiko. Zaščiteno z X-Admin-Token (ADMIN_TOKEN).
    Če ADMIN_TOKEN ni nastavljen, vrne 401 (varen privzetek)."""
    token = os.environ.get("ADMIN_TOKEN")
    if not token or x_admin_token != token:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return fetch_conversations(hours=hours, limit=limit)


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8001))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
