"""
Arcwright CLI — interactive terminal interface for the storytelling AI.

Usage:
    python main.py
    python main.py --platform youtube
    python main.py --name "Rois" --platform tiktok
"""
import argparse
import sys
import uuid

from langgraph.types import Command

from config.settings import validate_config
from graph.pipeline import create_arcwright_graph, make_initial_state


# ── Display helpers ────────────────────────────────────────────────────────────

def _print_banner():
    print("\n" + "="*56)
    print("  🎭  Arcwright — Storytelling AI")
    print("  Powered by LangGraph + 26 Storytelling Books")
    print("="*56)
    print()


def _print_outline(outline: dict):
    print("\n" + "─"*56)
    print("  📋 YOUR STORY OUTLINE")
    print("─"*56)
    for label, key in [
        ("Title",         "title"),
        ("Hook",          "hook"),
        ("Setup",         "setup"),
        ("Turning Point", "turning_point"),
        ("Struggle",      "struggle"),
        ("Resolution",    "resolution"),
        ("Punchline",     "punchline"),
        ("Platform",      "platform"),
        ("Duration",      "duration"),
    ]:
        value = outline.get(key, "")
        if value:
            print(f"  {label:<14}: {value}")
    print("─"*56)


def _print_script(script: dict):
    print("\n" + "="*56)
    print(f"  📝 {script.get('title', 'Your Story')}")
    print(f"  Platform: {script.get('platform_variant', '')} | "
          f"Tone: {script.get('voice_notes', {}).get('tone', '')}")
    print("="*56)
    print()
    print(script.get("body", ""))
    print("\n" + "="*56)


def _get_interrupt_payload(result: dict) -> dict | None:
    """Extract interrupt payload from graph result."""
    interrupts = result.get("__interrupt__", [])
    if interrupts:
        return interrupts[0].value if hasattr(interrupts[0], "value") else interrupts[0]
    return None


# ── Main loop ──────────────────────────────────────────────────────────────────

def run_session(platform: str = "general", user_name: str = "User"):
    """Run an interactive storytelling session."""
    _print_banner()

    # Validasi config sebelum pipeline dimulai
    validate_config(raise_on_error=True)

    graph = create_arcwright_graph()
    session_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": session_id}}

    state = make_initial_state(
        user_name=user_name,
        platform=platform,
        session_id=session_id,
    )

    print(f"  👋 Hi {user_name}! I'm Yui, your storytelling coach.")
    print(f"  🎯 Target platform: {platform}")
    print(f"  💡 Type 'quit' to exit at any time.\n")

    # Initial greeting from Story Director / Story Miner
    result = graph.invoke(state, config)

    MAX_TURNS = 50  # Safety guard — prevent infinite loops
    turn = 0
    while turn < MAX_TURNS:
        # Check if graph hit an interrupt (outline approval or story miner)
        interrupt_payload = _get_interrupt_payload(result)
    
        # Determine if we are paused at an interrupt node
        is_interrupted = False
        try:
            state_config = graph.get_state(config)
            if hasattr(state_config, "next") and state_config.next:
                is_interrupted = True
        except Exception:
            pass
        
        if is_interrupted and interrupt_payload and interrupt_payload.get("type") == "outline_approval":
            _print_outline(interrupt_payload.get("outline", {}))
            print("\n  What would you like to do?")
            print("  [1] approve — generate the full script")
            print("  [2] revise  — go back and adjust the outline")
            print("  [3] reject  — start fresh with new material")
            print()

            while True:
                choice = input("  Your choice (approve/revise/reject): ").strip().lower()
                if choice in ("approve", "1", "a"):
                    decision = "approve"
                    break
                elif choice in ("revise", "2", "r"):
                    decision = "revise"
                    break
                elif choice in ("reject", "3"):
                    decision = "reject"
                    break
                else:
                    print("  Please type 'approve', 'revise', or 'reject'")

            result = graph.invoke(Command(resume=decision), config)
            continue
            
        elif is_interrupted and interrupt_payload and interrupt_payload.get("type") == "interview_question":
            print(f"\n  🤖 Yui: {interrupt_payload.get('question', '')}\n")
            try:
                user_input = input("  You: ").strip()
            except (KeyboardInterrupt, EOFError):
                print("\n\n  Goodbye! Your session has been saved.")
                sys.exit(0)

            if user_input.lower() in ("quit", "exit", "q"):
                print("\n  Goodbye! Your session has been saved.")
                print(f"  Session ID: {session_id}")
                break

            if not user_input:
                continue

            turn += 1  # Increment turn counter

            resume_data = {"messages": [{"role": "user", "content": user_input}]}
            result = graph.invoke(Command(resume=resume_data), config)
            continue

        # Check if pipeline is complete (script generated)
        output_script = result.get("output_script")
        if output_script:
            _print_script(output_script)
            print("\n  ✅ Your story is ready! Copy the script above.")
            print("  Session ID (to resume later):", session_id)
            break

        # If not interrupted and not complete, this is an internal state transition
        # We just need to resume execution until the next interrupt
        result = graph.invoke(None, config)
        continue

    else:
        # MAX_TURNS reached — safety exit
        print(f"\n  ⚠️  Sesi mencapai batas {MAX_TURNS} turn.")
        print("  Session ID (untuk resume nanti):", session_id)


# ── Entry point ────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Arcwright — AI Storytelling Assistant"
    )
    parser.add_argument(
        "--platform",
        choices=["youtube", "tiktok", "podcast", "blog", "general"],
        default="general",
        help="Target platform for your story (default: general)",
    )
    parser.add_argument(
        "--name",
        default="User",
        help="Your name (optional)",
    )
    args = parser.parse_args()

    run_session(platform=args.platform, user_name=args.name)


if __name__ == "__main__":
    main()
