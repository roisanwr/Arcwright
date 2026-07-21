"""
Arcwright Web API — FastAPI + SSE backend untuk Storytelling AI UI.
Menghubungkan LangGraph pipeline ke browser via Server-Sent Events.
"""
import os
import sys
import uuid
import json
import asyncio
import threading
from pathlib import Path
from typing import Dict, Any

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config.settings import validate_config, ADMIN_KEY
from graph.pipeline import create_arcwright_graph, make_initial_state
from langgraph.types import Command

# ── App setup ─────────────────────────────────────────────────────────────────

app = FastAPI(title="Arcwright UI API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from langgraph.checkpoint.sqlite import SqliteSaver
import sqlite3
from typing import Optional

# ── Global state ──────────────────────────────────────────────────────────────

validate_config(raise_on_error=True)

# Gunakan SQLite sebagai persistent checkpointer agar sesi tidak hilang saat direfresh
conn = sqlite3.connect("arcwright_sessions.db", check_same_thread=False)
checkpointer = SqliteSaver(conn)

graph = create_arcwright_graph(checkpointer=checkpointer)

# ── History DB — terpisah dari LangGraph checkpoint ──────────────────────────
_hist_conn = sqlite3.connect("arcwright_history.db", check_same_thread=False)
_hist_conn.row_factory = sqlite3.Row

def _init_history_db():
    cur = _hist_conn.cursor()
    cur.executescript("""
        CREATE TABLE IF NOT EXISTS session_meta (
            session_id  TEXT PRIMARY KEY,
            device_id   TEXT NOT NULL,
            title       TEXT DEFAULT 'Sesi baru',
            platform    TEXT DEFAULT 'general',
            language    TEXT DEFAULT 'id',
            status      TEXT DEFAULT 'active',
            created_at  TEXT DEFAULT (datetime('now')),
            updated_at  TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_device_id ON session_meta(device_id);

        CREATE TABLE IF NOT EXISTS chat_messages (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id  TEXT NOT NULL REFERENCES session_meta(session_id),
            role        TEXT NOT NULL,
            content     TEXT NOT NULL,
            msg_type    TEXT DEFAULT 'chat',
            created_at  TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_session_messages ON chat_messages(session_id, created_at);
    """)
    _hist_conn.commit()

_init_history_db()

def _hist_save_session(session_id: str, device_id: str, platform: str, language: str):
    _hist_conn.execute(
        "INSERT OR IGNORE INTO session_meta (session_id, device_id, platform, language) VALUES (?,?,?,?)",
        (session_id, device_id, platform, language)
    )
    _hist_conn.commit()

def _hist_save_message(session_id: str, role: str, content: str, msg_type: str = "chat"):
    _hist_conn.execute(
        "INSERT INTO chat_messages (session_id, role, content, msg_type) VALUES (?,?,?,?)",
        (session_id, role, content, msg_type)
    )
    _hist_conn.execute(
        "UPDATE session_meta SET updated_at = datetime('now') WHERE session_id = ?",
        (session_id,)
    )
    _hist_conn.commit()

def _hist_update_title(session_id: str, title: str):
    _hist_conn.execute(
        "UPDATE session_meta SET title = ?, updated_at = datetime('now') WHERE session_id = ?",
        (title, session_id)
    )
    _hist_conn.commit()

# Per-session: queue SSE events
session_queues: Dict[str, asyncio.Queue] = {}
# Shared event loop (set on startup)
_main_loop: asyncio.AbstractEventLoop | None = None

# ── Helpers ───────────────────────────────────────────────────────────────────

def _push(session_id: str, event_type: str, data: Any):
    """Thread-safe: push SSE event dari background thread ke async event loop.
    Sekaligus auto-save pesan chat ke history DB."""
    # Auto-persist chat events ke DB
    if event_type == "chat" and isinstance(data, dict):
        role    = data.get("role", "assistant")
        content = data.get("content", "")
        if content:
            try:
                _hist_save_message(session_id, role, content, msg_type="chat")
            except Exception:
                pass  # jangan crash SSE karena DB error
    elif event_type == "script" and isinstance(data, dict):
        title = data.get("title", "Script")
        body  = data.get("body", "")
        if body:
            try:
                _hist_save_message(session_id, "assistant", f"[SCRIPT:{title}]\n{body}", msg_type="script")
                # Update status sesi jadi completed
                _hist_conn.execute(
                    "UPDATE session_meta SET status='completed', updated_at=datetime('now') WHERE session_id=?",
                    (session_id,)
                )
                _hist_conn.commit()
            except Exception:
                pass

    if _main_loop is None:
        return
    q = session_queues.get(session_id)
    if q is None:
        return
    payload = {"event": event_type, "data": json.dumps(data)}
    _main_loop.call_soon_threadsafe(q.put_nowait, payload)


def _agent_label(node_name: str) -> str:
    labels = {
        "story_director":  "🧠 Story Director memproses...",
        "story_miner":     "💬 Story Miner bersiap bertanya...",
        "rag_librarian":   "📚 RAG Librarian mencari framework...",
        "web_researcher":  "🌐 Web Researcher mencari referensi...",
        "deep_dive":       "🔍 Deep Dive menganalisis...",
        "validator":       "✅ Validator menilai outline...",
        "outline_writer":  "📝 Outline Writer menulis kerangka...",
        "script_writer":   "🎬 Script Writer menulis skrip...",
        "user_approval":   "⏸️  Menunggu persetujuanmu...",
        "__interrupt__":   "⏸️  Menunggu input...",
    }
    return labels.get(node_name, f"⚙️ {node_name} berjalan...")


# ── LangGraph thread ───────────────────────────────────────────────────────────

def _run_graph_thread(session_id: str, message: str, is_new: bool = False,
                      user_name: str = "User", language: str = "id", platform: str = "general"):
    """Jalankan LangGraph di background thread, push events via SSE."""
    config = {"configurable": {"thread_id": session_id}}

    try:
        if is_new:
            state = make_initial_state(
                user_name=user_name, platform=platform, session_id=session_id
            )
            # Simpan language preference ke user_profile
            state["user_profile"]["preferred_language"] = language
            iterator = graph.stream(state, config, stream_mode="updates")
        else:
            state_info = graph.get_state(config)
            is_interrupted = bool(getattr(state_info, "next", None))

            if is_interrupted:
                # Cek apakah message adalah outline approval decision
                if message.strip().lower() in ("approve", "revise", "reject", "1", "2", "3"):
                    decision_map = {
                        "approve": "approve", "1": "approve",
                        "revise":  "revise",  "2": "revise",
                        "reject":  "reject",  "3": "reject",
                    }
                    decision = decision_map.get(message.strip().lower(), "reject")
                    iterator = graph.stream(Command(resume=decision), config, stream_mode="updates")
                else:
                    resume_data = {"messages": [{"role": "user", "content": message}]}
                    iterator = graph.stream(Command(resume=resume_data), config, stream_mode="updates")
            else:
                iterator = graph.stream(
                    {"messages": [{"role": "user", "content": message}]},
                    config,
                    stream_mode="updates",
                )

        # ── Stream graph steps ────────────────────────────────────────────────
        for chunk in iterator:
            node_name = list(chunk.keys())[0]
            node_data = chunk[node_name]
            
            _push(session_id, "status", {
                "node":    node_name,
                "message": _agent_label(node_name),
            })

            # Check and push explicit Thought Process
            if isinstance(node_data, dict) and "thought_process" in node_data:
                for tp in node_data["thought_process"]:
                    _push(session_id, "reasoning", {
                        "agent": tp.get("agent", node_name),
                        "type": "thought_process",
                        "content": tp.get("thought", ""),
                        "data": tp.get("data", None)
                    })

            # Extract reasoning or internal notes from node_data
            if isinstance(node_data, dict):
                # 1. Check for agent_notes added in this step
                if "agent_notes" in node_data:
                    notes = node_data["agent_notes"]
                    if isinstance(notes, list):
                        for note in notes:
                            if isinstance(note, dict) and "content" in note:
                                _push(session_id, "reasoning", {
                                    "agent": note.get("agent_name", node_name),
                                    "type": note.get("note_type", "internal_note"),
                                    "content": note["content"]
                                })
                
                # 2. Check for validation result
                if "validation_result" in node_data and node_data["validation_result"]:
                    val = node_data["validation_result"]
                    _push(session_id, "reasoning", {
                        "agent": "validator",
                        "type": "scoring",
                        "content": f"Score: {val.get('score', 0)}/50\nFeedback: {val.get('feedback', '')}\nPassed: {val.get('passed', False)}"
                    })
                
                # 3. Check for deep_dive analysis
                if "deep_dive_analysis" in node_data and node_data["deep_dive_analysis"]:
                    dd = node_data["deep_dive_analysis"]
                    content = "\n".join([f"**{k.capitalize()}**: {v}" for k,v in dd.items() if isinstance(v, str)])
                    if content:
                        _push(session_id, "reasoning", {
                            "agent": "deep_dive",
                            "type": "analysis",
                            "content": content
                        })
                        
                # 4. Extract raw AI message thought process if available (some LLMs put it in content or additional_kwargs)
                if "messages" in node_data:
                    for msg in node_data.get("messages", []):
                        if hasattr(msg, "type") and msg.type == "ai":
                            # Gemini or DeepSeek might put reasoning in additional_kwargs
                            reasoning = getattr(msg, "additional_kwargs", {}).get("reasoning_content", "")
                            if reasoning:
                                _push(session_id, "reasoning", {
                                    "agent": node_name,
                                    "type": "chain_of_thought",
                                    "content": reasoning
                                })
                            # Or if it's a tool call
                            if hasattr(msg, "tool_calls") and msg.tool_calls:
                                tool_calls_str = "\n".join([f"🛠️ Tool: `{tc['name']}`\nArgs: {tc['args']}" for tc in msg.tool_calls])
                                _push(session_id, "reasoning", {
                                    "agent": node_name,
                                    "type": "tool_execution",
                                    "content": tool_calls_str
                                })

        # ── Cek interrupt setelah loop selesai ────────────────────────────────
        state_info = graph.get_state(config)
        if getattr(state_info, "next", None):
            # Cari semua interrupts dari semua tasks
            all_interrupts = []
            for task in (getattr(state_info, "tasks", None) or []):
                raw = getattr(task, "interrupts", None) or []
                all_interrupts.extend(raw)

            if all_interrupts:
                for interrupt in all_interrupts:
                    payload = getattr(interrupt, "value", interrupt)
                    if not isinstance(payload, dict):
                        continue
                    itype = payload.get("type", "")
                    if itype == "interview_question":
                        question = payload.get("question", "")
                        if question:
                            _push(session_id, "chat", {"role": "assistant", "content": question})
                    elif itype == "outline_approval":
                        outline = payload.get("outline", {})
                        # Format outline nicely
                        out_str = "## 📋 Story Outline-mu\n\n"
                        for k, v in outline.items():
                            out_str += f"- **{k.capitalize()}**: {v}\n"
                        out_str += "\n---\nKetik **approve**, **revise**, atau **reject**."
                        _push(session_id, "chat", {"role": "assistant", "content": out_str})
                        _push(session_id, "outline", outline)
            else:
                # Interrupt tapi gak ada payload — cek apakah pipeline nunggu story_miner atau user_approval
                next_nodes = getattr(state_info, "next", ())
                if "story_miner" in next_nodes:
                    # Pipeline nunggu input user tapi interrupt belum tersimpan — 
                    # tampilkan pesan dari messages terakhir
                    state_vals = getattr(state_info, "values", {}) or {}
                    msgs = state_vals.get("messages", [])
                    for msg in reversed(msgs):
                        if hasattr(msg, "type") and msg.type == "ai" and msg.content:
                            _push(session_id, "chat", {"role": "assistant", "content": msg.content})
                            break
                elif "user_approval" in next_nodes:
                    # Kadang interrupt payload gak kebaca dari state.tasks[0], ambil dari state.values manual
                    state_vals = getattr(state_info, "values", {}) or {}
                    outline = state_vals.get("story_outline", {})
                    if outline:
                        out_str = "## 📋 Story Outline-mu\n\n"
                        for k, v in outline.items():
                            if isinstance(v, str) and v.strip():
                                out_str += f"- **{k.capitalize()}**: {v}\n"
                        out_str += "\n---\nKetik **approve**, **revise**, atau **reject**."
                        _push(session_id, "chat", {"role": "assistant", "content": out_str})
                        _push(session_id, "outline", outline)

        # ── Cek script final ──────────────────────────────────────────────────
        final_values = getattr(graph.get_state(config), "values", {}) or {}
        output_script = final_values.get("output_script")
        if output_script:
            _push(session_id, "script", output_script)
            _push(session_id, "chat", {
                "role":    "assistant",
                "content": "✅ Skripmu sudah jadi! Lihat di panel kanan.",
            })

    except Exception as exc:
        import traceback
        err = traceback.format_exc()
        print(f"[Arcwright] Graph error:\n{err}")
        _push(session_id, "error", {"message": f"Graph error: {str(exc)}"})

    finally:
        _push(session_id, "status", {"node": "idle", "message": "Menunggu inputmu..."})


# ── Startup: simpan event loop ────────────────────────────────────────────────

@app.on_event("startup")
async def _on_startup():
    global _main_loop
    _main_loop = asyncio.get_running_loop()


# ── Static files (React frontend build) ──────────────────────────────────────

FRONTEND_DIST = Path(__file__).parent / "frontend" / "dist"
if FRONTEND_DIST.exists():
    # Mount /assets/ (JS, CSS bundles)
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="assets")

# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/dev")
def serve_dev_ui():
    """Developer UI (original ui.html) — tetap tersedia di /dev."""
    html_path = Path(__file__).parent / "ui.html"
    if html_path.exists():
        return HTMLResponse(content=html_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>ui.html not found</h1>")


# ── Root static files (logo, favicon, icons) — harus sebelum catch-all ──────

_STATIC_FILES = ["logo-mark.png", "logo-full.png", "favicon.svg", "icons.svg"]

@app.get("/{filename}")
def serve_root_static(filename: str):
    """Serve file statis di root dist/ (logo, favicon) sebelum SPA catch-all."""
    if filename in _STATIC_FILES:
        file_path = FRONTEND_DIST / filename
        if file_path.exists():
            return FileResponse(str(file_path))
    # Bukan static file — fallback ke SPA
    dist_index = FRONTEND_DIST / "index.html"
    if dist_index.exists():
        return FileResponse(str(dist_index))
    html_path = Path(__file__).parent / "ui.html"
    if html_path.exists():
        return HTMLResponse(content=html_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Frontend not found. Run: cd frontend && npm run build</h1>", status_code=503)


@app.get("/api/start")
def start_session(
    user_name: str = "User",
    language: str = "id",
    platform: str = "general",
    device_id: str = "",
):
    """Mulai sesi baru Arcwright. Terima nama user, bahasa, platform, dan device_id."""
    session_id = str(uuid.uuid4())
    # Simpan ke history DB jika ada device_id
    if device_id:
        _hist_save_session(session_id, device_id, platform, language)
    # Buat queue SEBELUM thread jalan, biar event gak ilang
    session_queues[session_id] = asyncio.Queue()
    threading.Thread(
        target=_run_graph_thread,
        args=(session_id, "", True, user_name, language, platform),
        daemon=True,
    ).start()
    return {"session_id": session_id}


class ChatRequest(BaseModel):
    session_id: str
    message: str
    device_id: str = ""


@app.post("/api/chat")
def send_chat(req: ChatRequest):
    """Kirim pesan user ke pipeline."""
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Pesan kosong")
    if req.session_id not in session_queues:
        session_queues[req.session_id] = asyncio.Queue()

    # Simpan pesan user ke history DB
    if req.device_id and req.message.strip().lower() not in ("approve", "revise", "reject", "1", "2", "3"):
        try:
            _hist_save_message(req.session_id, "user", req.message)
            # Auto-update title dari pesan user pertama
            cur = _hist_conn.execute(
                "SELECT COUNT(*) as cnt FROM chat_messages WHERE session_id=? AND role='user'",
                (req.session_id,)
            )
            row = cur.fetchone()
            if row and row["cnt"] == 1:
                title = req.message[:60] + ("…" if len(req.message) > 60 else "")
                _hist_update_title(req.session_id, title)
        except Exception:
            pass

    threading.Thread(
        target=_run_graph_thread,
        args=(req.session_id, req.message, False),
        daemon=True,
    ).start()
    return {"status": "processing"}


# ── History endpoints ─────────────────────────────────────────────────────────

@app.get("/api/history")
def get_history(device_id: str):
    """Ambil daftar sesi berdasarkan device_id."""
    if not device_id:
        raise HTTPException(status_code=400, detail="device_id diperlukan")
    cur = _hist_conn.execute(
        """SELECT session_id, title, platform, language, status, created_at, updated_at
           FROM session_meta
           WHERE device_id=? AND status != 'archived'
           ORDER BY updated_at DESC LIMIT 50""",
        (device_id,)
    )
    rows = [dict(r) for r in cur.fetchall()]
    return {"sessions": rows}


@app.get("/api/session/{session_id}")
def get_session(session_id: str, device_id: str):
    """Ambil chat history lengkap untuk satu sesi (verifikasi device_id)."""
    if not device_id:
        raise HTTPException(status_code=400, detail="device_id diperlukan")
    # Verifikasi ownership
    cur = _hist_conn.execute(
        "SELECT device_id FROM session_meta WHERE session_id=?", (session_id,)
    )
    row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Sesi tidak ditemukan")
    if row["device_id"] != device_id:
        raise HTTPException(status_code=403, detail="Akses ditolak")

    msgs = _hist_conn.execute(
        """SELECT role, content, msg_type, created_at
           FROM chat_messages WHERE session_id=? ORDER BY created_at ASC""",
        (session_id,)
    )
    return {
        "session_id": session_id,
        "messages": [dict(m) for m in msgs.fetchall()]
    }


class PatchSessionRequest(BaseModel):
    device_id: str
    title: Optional[str] = None
    status: Optional[str] = None


@app.patch("/api/session/{session_id}")
def patch_session(session_id: str, body: PatchSessionRequest):
    """Update title atau status sesi."""
    cur = _hist_conn.execute(
        "SELECT device_id FROM session_meta WHERE session_id=?", (session_id,)
    )
    row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Sesi tidak ditemukan")
    if row["device_id"] != body.device_id:
        raise HTTPException(status_code=403, detail="Akses ditolak")
    if body.title:
        _hist_update_title(session_id, body.title)
    if body.status:
        _hist_conn.execute(
            "UPDATE session_meta SET status=?, updated_at=datetime('now') WHERE session_id=?",
            (body.status, session_id)
        )
        _hist_conn.commit()
    return {"ok": True}


@app.delete("/api/session/{session_id}")
def delete_session(session_id: str, device_id: str):
    """Soft-delete sesi (set status='archived')."""
    if not device_id:
        raise HTTPException(status_code=400, detail="device_id diperlukan")
    cur = _hist_conn.execute(
        "SELECT device_id FROM session_meta WHERE session_id=?", (session_id,)
    )
    row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Sesi tidak ditemukan")
    if row["device_id"] != device_id:
        raise HTTPException(status_code=403, detail="Akses ditolak")
    _hist_conn.execute(
        "UPDATE session_meta SET status='archived', updated_at=datetime('now') WHERE session_id=?",
        (session_id,)
    )
    _hist_conn.commit()
    return {"ok": True}


def _check_admin(key: str):
    """Validasi admin key. Raise 403 jika salah."""
    if not ADMIN_KEY or key != ADMIN_KEY:
        raise HTTPException(status_code=403, detail="Akses ditolak. Admin key salah.")


# ── Admin endpoints (/api/admin/*) ────────────────────────────────────────────

@app.get("/api/admin/sessions")
def admin_get_all_sessions(key: str = ""):
    """Admin: ambil SEMUA sesi dari semua user, dikelompokkan per device_id."""
    _check_admin(key)
    cur = _hist_conn.execute(
        """SELECT session_id, device_id, title, platform, language,
                  status, created_at, updated_at
           FROM session_meta
           ORDER BY updated_at DESC
           LIMIT 200"""
    )
    rows = [dict(r) for r in cur.fetchall()]

    # Stats agregat
    stats_cur = _hist_conn.execute(
        """SELECT
             COUNT(*)                                          AS total_sessions,
             COUNT(DISTINCT device_id)                        AS total_users,
             SUM(CASE WHEN status='active'    THEN 1 ELSE 0 END) AS active,
             SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) AS completed,
             SUM(CASE WHEN date(created_at)=date('now') THEN 1 ELSE 0 END) AS today
           FROM session_meta WHERE status != 'archived'"""
    )
    stats = dict(stats_cur.fetchone() or {})

    # Cek sesi mana yang sedang live (punya SSE queue aktif)
    live_ids = list(session_queues.keys())

    return {"sessions": rows, "stats": stats, "live_session_ids": live_ids}


@app.get("/api/admin/session/{session_id}")
def admin_get_session(session_id: str, key: str = ""):
    """Admin: ambil chat history sesi manapun tanpa cek device_id."""
    _check_admin(key)
    meta_cur = _hist_conn.execute(
        "SELECT * FROM session_meta WHERE session_id=?", (session_id,)
    )
    meta = meta_cur.fetchone()
    if not meta:
        raise HTTPException(status_code=404, detail="Sesi tidak ditemukan")
    msgs = _hist_conn.execute(
        """SELECT role, content, msg_type, created_at
           FROM chat_messages WHERE session_id=? ORDER BY created_at ASC""",
        (session_id,)
    )
    return {
        "session_id": session_id,
        "meta": dict(meta),
        "messages": [dict(m) for m in msgs.fetchall()],
        "is_live": session_id in session_queues,
    }


class AdminChatRequest(BaseModel):
    session_id: str
    message: str
    key: str = ""


@app.post("/api/admin/chat")
def admin_send_chat(req: AdminChatRequest):
    """Admin: inject pesan ke sesi manapun yang sedang live."""
    _check_admin(req.key)
    if req.session_id not in session_queues:
        session_queues[req.session_id] = asyncio.Queue()
    threading.Thread(
        target=_run_graph_thread,
        args=(req.session_id, req.message, False),
        daemon=True,
    ).start()
    return {"status": "injected"}


@app.get("/api/admin/stream/{session_id}")
async def admin_stream_events(session_id: str, key: str, request: Request):
    """Admin SSE — subscribe ke event sesi manapun tanpa cek device_id."""
    if not ADMIN_KEY or key != ADMIN_KEY:
        raise HTTPException(status_code=403, detail="Akses ditolak.")
    # Buat queue jika belum ada (sesi lama yang sudah selesai)
    if session_id not in session_queues:
        session_queues[session_id] = asyncio.Queue()
    q = session_queues[session_id]

    async def generator():
        while True:
            if await request.is_disconnected():
                break
            try:
                msg = await asyncio.wait_for(q.get(), timeout=2.0)
                yield msg
            except asyncio.TimeoutError:
                yield {"event": "ping", "data": "{}"}

    return EventSourceResponse(generator())


@app.get("/api/stream")
async def stream_events(session_id: str, request: Request):
    """SSE endpoint — kirim real-time events ke browser."""
    if session_id not in session_queues:
        session_queues[session_id] = asyncio.Queue()

    q = session_queues[session_id]

    async def generator():
        while True:
            if await request.is_disconnected():
                break
            try:
                msg = await asyncio.wait_for(q.get(), timeout=2.0)
                yield msg
            except asyncio.TimeoutError:
                yield {"event": "ping", "data": "{}"}

    return EventSourceResponse(generator())


# ── SPA catch-all: semua route non-API → index.html ──────────────────────────

@app.get("/{full_path:path}")
def serve_spa(full_path: str):
    """Serve React SPA untuk semua sub-route (/chat, /about, dll.)."""
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404)
    dist_index = FRONTEND_DIST / "index.html"
    if dist_index.exists():
        return FileResponse(str(dist_index))
    html_path = Path(__file__).parent / "ui.html"
    if html_path.exists():
        return HTMLResponse(content=html_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Frontend not found. Run: cd frontend && npm run build</h1>", status_code=503)


if __name__ == "__main__":
    import uvicorn
    mode = "React UI" if FRONTEND_DIST.exists() else "Legacy ui.html"
    print(f"🎭 Arcwright Web UI ({mode}) → http://localhost:8765")
    print(f"   Developer UI → http://localhost:8765/dev")
    uvicorn.run("api_server:app", host="0.0.0.0", port=8765, reload=False)
