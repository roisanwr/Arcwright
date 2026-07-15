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
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config.settings import validate_config
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

# ── Global state ──────────────────────────────────────────────────────────────

validate_config(raise_on_error=True)

# Gunakan SQLite sebagai persistent checkpointer agar sesi tidak hilang saat direfresh
conn = sqlite3.connect("arcwright_sessions.db", check_same_thread=False)
checkpointer = SqliteSaver(conn)

graph = create_arcwright_graph(checkpointer=checkpointer)

# Per-session: queue SSE events
session_queues: Dict[str, asyncio.Queue] = {}
# Shared event loop (set on startup)
_main_loop: asyncio.AbstractEventLoop | None = None

# ── Helpers ───────────────────────────────────────────────────────────────────

def _push(session_id: str, event_type: str, data: Any):
    """Thread-safe: push SSE event dari background thread ke async event loop."""
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

def _run_graph_thread(session_id: str, message: str, is_new: bool = False):
    """Jalankan LangGraph di background thread, push events via SSE."""
    config = {"configurable": {"thread_id": session_id}}

    try:
        if is_new:
            state = make_initial_state(
                user_name="User", platform="general", session_id=session_id
            )
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


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/")
def serve_ui():
    html_path = Path(__file__).parent / "ui.html"
    if html_path.exists():
        return HTMLResponse(content=html_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>ui.html not found</h1>")


@app.get("/api/start")
def start_session():
    """Mulai sesi baru Arcwright."""
    # Generate random session ID baru tiap hit endpoint ini
    session_id = str(uuid.uuid4())
    # Buat queue SEBELUM thread jalan, biar event gak ilang
    session_queues[session_id] = asyncio.Queue()
    threading.Thread(
        target=_run_graph_thread,
        args=(session_id, "", True),
        daemon=True,
    ).start()
    return {"session_id": session_id}


class ChatRequest(BaseModel):
    session_id: str
    message: str


@app.post("/api/chat")
def send_chat(req: ChatRequest):
    """Kirim pesan user ke pipeline."""
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Pesan kosong")
    if req.session_id not in session_queues:
        raise HTTPException(status_code=404, detail="Session tidak ditemukan")
    threading.Thread(
        target=_run_graph_thread,
        args=(req.session_id, req.message, False),
        daemon=True,
    ).start()
    return {"status": "processing"}


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


if __name__ == "__main__":
    import uvicorn
    print("🎭 Arcwright Web UI → http://localhost:8000")
    uvicorn.run("api_server:app", host="0.0.0.0", port=8000, reload=False)
