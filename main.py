from pathlib import Path
import os

from dotenv import load_dotenv
load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.chat.router import router as chat_router
from app.rag.search import load_knowledge

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
    return """<!DOCTYPE html>
<html>
<head><title>Gartner AI</title><meta charset="UTF-8">
<style>
  body { font-family: system-ui; max-width: 600px; margin: 50px auto; padding: 20px; background: #0D0D0D; color: #fff; }
  h1 { color: #C4A44B; }
  #chat { border: 1px solid #333; height: 400px; overflow-y: auto; padding: 10px; margin-bottom: 10px; border-radius: 8px; }
  .user { color: #C4A44B; margin: 5px 0; }
  .bot { color: #eee; margin: 5px 0; white-space: pre-wrap; }
  #input { width: 80%; padding: 10px; background: #1a1a1a; border: 1px solid #333; color: #fff; border-radius: 6px; }
  button { padding: 10px 20px; background: #C4A44B; border: none; color: #000; font-weight: 700; border-radius: 6px; cursor: pointer; }
</style></head>
<body>
  <h1>🧀 Gartner Bohinj AI</h1>
  <div id="chat"></div>
  <input type="text" id="input" placeholder="Vprašajte..." onkeypress="if(event.key==='Enter')send()">
  <button onclick="send()">Pošlji</button>
  <script>
    let sid = null;
    const chat = document.getElementById('chat');
    const input = document.getElementById('input');
    async function send() {
      const msg = input.value.trim();
      if (!msg) return;
      chat.innerHTML += `<div class="user"><b>Vi:</b> ${msg}</div>`;
      input.value = '';
      const res = await fetch('/chat', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({message: msg, session_id: sid})
      });
      const data = await res.json();
      sid = data.session_id;
      chat.innerHTML += `<div class="bot"><b>Gartner AI:</b> ${data.reply}</div>`;
      chat.scrollTop = chat.scrollHeight;
    }
  </script>
</body>
</html>"""


app.include_router(chat_router)

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8001))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
