import os
import sys
import uuid
import json
import asyncio
import threading
from pathlib import Path
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

# Add parent path for local imports
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config.settings import validate_config
from graph.pipeline import create_arcwright_graph, make_initial_state
from langgraph.types import Command

app = FastAPI(title="Arcwright UI API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global graph instance
validate_config(raise_on_error=True)
graph = create_arcwright_graph()

# In-memory store for event queues per session
session_queues: Dict[str, asyncio.Queue] = {}

class ChatRequest(BaseModel):
    session_id: str
    message: str

def get_or_create_queue(session_id: str) -> asyncio.Queue:
    if session_id not in session_queues:
        session_queues[session_id] = asyncio.Queue()
    return session_queues[session_id]

async def push_event(session_id: str, event_type: str, data: Any):
    q = get_or_create_queue(session_id)
    await q.put({"event": event_type, "data": json.dumps(data)})

def _run_graph_thread(session_id: str, message: str, is_new: bool = False):
    """Run LangGraph synchronously in a background thread and push events to SSE queue."""
    config = {"configurable": {"thread_id": session_id}}
    
    async def push(ev_type, payload):
        # Fire-and-forget push from sync context to async event loop
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(push_event(session_id, ev_type, payload))
        except RuntimeError:
            pass

    if is_new:
        # Create initial state
        state = make_initial_state(user_name="User", platform="general", session_id=session_id)
        iterator = graph.stream(state, config, stream_mode="updates")
    else:
        # Check if we are resuming from an interrupt
        state_info = graph.get_state(config)
        is_interrupted = hasattr(state_info, "next") and state_info.next
        
        if is_interrupted:
            # We are answering a question or outline approval
            resume_data = {"messages": [{"role": "user", "content": message}]}
            # Note: For outline approval, message might be "approve"/"revise"/"reject"
            if message.lower() in ("approve", "revise", "reject", "1", "2", "3"):
                decision = "approve" if message.lower() in ("approve", "1") else ("revise" if message.lower() in ("revise", "2") else "reject")
                iterator = graph.stream(Command(resume=decision), config, stream_mode="updates")
            else:
                iterator = graph.stream(Command(resume=resume_data), config, stream_mode="updates")
        else:
            # Normal invocation (shouldn't really happen since we use interrupt_before)
            iterator = graph.stream({"messages": [{"role": "user", "content": message}]}, config, stream_mode="updates")

    # Start stepping through the graph
    try:
        for chunk in iterator:
            node_name = list(chunk.keys())[0]
            node_data = chunk[node_name]
            
            # Send status update
            asyncio.run(push_event(session_id, "status", {"node": node_name, "message": f"Agent running: {node_name}"}))
            
            # If the node produced a new AI message, send it to the UI
            if "messages" in node_data:
                for msg in node_data["messages"]:
                    if hasattr(msg, "type") and msg.type == "ai" and msg.content:
                        asyncio.run(push_event(session_id, "chat", {"role": "assistant", "content": msg.content}))

        # If we exited the loop, check if we hit an interrupt
        state_info = graph.get_state(config)
        if hasattr(state_info, "next") and state_info.next:
            interrupts = state_info.tasks[0].interrupts if hasattr(state_info.tasks[0], "interrupts") else []
            if interrupts:
                payload = interrupts[0].value if hasattr(interrupts[0], "value") else interrupts[0]
                
                if payload.get("type") == "interview_question":
                    # Send the question
                    asyncio.run(push_event(session_id, "chat", {"role": "assistant", "content": payload.get("question", "")}))
                elif payload.get("type") == "outline_approval":
                    outline = payload.get("outline", {})
                    # Format outline nicely
                    out_str = "📋 YOUR STORY OUTLINE\n"
                    for k, v in outline.items():
                        out_str += f"- **{k.capitalize()}**: {v}\n"
                    out_str += "\nWhat would you like to do? Type: **approve**, **revise**, or **reject**."
                    asyncio.run(push_event(session_id, "chat", {"role": "assistant", "content": out_str}))
                    asyncio.run(push_event(session_id, "outline", outline))

        # Check if pipeline is fully complete
        final_state = graph.get_state(config).values
        if final_state and final_state.get("output_script"):
            asyncio.run(push_event(session_id, "script", final_state["output_script"]))
            asyncio.run(push_event(session_id, "chat", {"role": "assistant", "content": "✅ Your final script is ready! Check the Output tab."}))

    except Exception as e:
        asyncio.run(push_event(session_id, "error", {"message": str(e)}))
        
    finally:
        asyncio.run(push_event(session_id, "status", {"node": "idle", "message": "Waiting for input..."}))


@app.get("/")
def serve_ui():
    """Serve the simple HTML React UI."""
    html_path = Path(__file__).parent / "ui.html"
    if html_path.exists():
        return HTMLResponse(content=html_path.read_text())
    return HTMLResponse(content="<h1>UI File not found</h1>")

@app.get("/api/start")
def start_session():
    """Start a new Arcwright session."""
    session_id = str(uuid.uuid4())
    
    # Run graph initialization in background
    threading.Thread(target=_run_graph_thread, args=(session_id, "", True)).start()
    
    return {"session_id": session_id}

@app.post("/api/chat")
def send_chat(req: ChatRequest):
    """Send a message to the active session."""
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Empty message")
        
    threading.Thread(target=_run_graph_thread, args=(req.session_id, req.message, False)).start()
    return {"status": "processing"}

@app.get("/api/stream")
async def stream_events(session_id: str, request: Request):
    """SSE endpoint for real-time updates."""
    q = get_or_create_queue(session_id)
    
    async def event_generator():
        while True:
            if await request.is_disconnected():
                break
            try:
                # Wait for next event
                msg = await asyncio.wait_for(q.get(), timeout=1.0)
                yield msg
            except asyncio.TimeoutError:
                # Send heartbeat
                yield {"event": "ping", "data": json.dumps({"status": "alive"})}
                
    return EventSourceResponse(event_generator())

if __name__ == "__main__":
    import uvicorn
    print("Starting Arcwright Web UI on http://localhost:8000")
    uvicorn.run("api_server:app", host="0.0.0.0", port=8000, reload=True)