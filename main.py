"""
Arcwright CLI — main entry point.
Interactive storytelling session via terminal.

Usage:
    python main.py
    python main.py --platform tiktok
"""

import os
import sys
import argparse
from langchain_core.messages import HumanMessage

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from graph.pipeline import create_arcwright_graph, get_initial_state


PLATFORMS = ["youtube", "tiktok", "podcast", "blog", "general"]

BANNER = """
╔══════════════════════════════════════════════════════╗
║          🎭  ARCWRIGHT — Storytelling AI              ║
║    "Everyone has a story. You just need to find it." ║
╚══════════════════════════════════════════════════════╝
"""

PLATFORM_DESCRIPTIONS = {
    "youtube":  "YouTube (3-10 menit video)",
    "tiktok":   "TikTok (60-90 detik, punchy)",
    "podcast":  "Podcast (5-15 menit audio)",
    "blog":     "Blog / tulisan panjang",
    "general":  "Format bebas",
}


def print_outline(outline: dict):
    """Pretty-print story outline for user approval."""
    print("\n" + "═" * 55)
    print(f"  📖 STORY OUTLINE: {outline.get('title', 'Untitled')}")
    print("═" * 55)
    print(f"\n🎣 Hook:\n   {outline.get('hook', '')}")
    print(f"\n📍 Setup:\n   {outline.get('setup', '')}")
    print(f"\n⚡ Turning Point:\n   {outline.get('turning_point', '')}")
    print(f"\n🔥 Struggle:\n   {outline.get('struggle', '')}")
    print(f"\n✅ Resolution:\n   {outline.get('resolution', '')}")
    print(f"\n💡 Punchline:\n   {outline.get('punchline', '')}")
    print(f"\n📱 Platform: {outline.get('platform', '')}  |  ⏱️  {outline.get('estimated_duration', '')}")
    print("\n" + "═" * 55)


def print_script(script: dict):
    """Pretty-print final output script."""
    print("\n" + "═" * 55)
    print(f"  🎬 FINAL SCRIPT: {script.get('title', 'Untitled')}")
    print(f"  Platform: {script.get('platform', '')} | Words: {script.get('word_count', 0)}")
    print("═" * 55)
    print()
    print(script.get("body", ""))
    print("\n" + "═" * 55)


def run_session(platform: str = "general"):
    """Run an interactive storytelling session."""
    print(BANNER)

    # Check OpenAI key
    if not os.environ.get("OPENAI_API_KEY"):
        print("⚠️  OPENAI_API_KEY not set. Export it first:")
        print("   export OPENAI_API_KEY='sk-...'")
        sys.exit(1)

    print(f"📱 Platform: {PLATFORM_DESCRIPTIONS.get(platform, platform)}")
    print("💬 Type 'quit' to exit at any time.\n")

    # Build graph and initial state
    graph = create_arcwright_graph()
    state = get_initial_state(platform)
    config = {"configurable": {"thread_id": state["session_id"]}}

    print("🎭 Yui: Hi! Gue Yui, storytelling coach lo. Gue bakal bantu lo nemuin cerita menarik dari kehidupan sehari-hari lo.")
    print("       Gak perlu cerita yang dramatis — hal kecil sekalipun bisa jadi konten yang relatable.\n")

    # ── Main interaction loop ──────────────────────────────────────
    try:
        for event in graph.stream(state, config, stream_mode="values"):

            # Get last message from agent (if any)
            messages = event.get("messages", [])
            if messages:
                last_msg = messages[-1]
                if hasattr(last_msg, "content") and last_msg.content:
                    # Only print AI messages (not the user's own input)
                    if last_msg.__class__.__name__ == "AIMessage":
                        print(f"🎭 Yui: {last_msg.content}\n")

            # Check if we hit the user_approval interrupt
            if event.get("story_outline") and not event.get("outline_approved"):
                outline = event["story_outline"]
                if outline:
                    print_outline(outline)
                    print("\n💬 Approve outline ini? (y = lanjut ke naskah, n = revisi, q = keluar)")
                    choice = input(">>> ").strip().lower()

                    if choice == "q":
                        print("\n👋 Session ended. See you next time!")
                        break
                    elif choice == "y":
                        # Resume graph with approval
                        state = graph.update_state(
                            config,
                            {"outline_approved": True, "current_phase": "scripting"}
                        )
                        # Continue streaming
                        for final_event in graph.stream(None, config, stream_mode="values"):
                            output_script = final_event.get("output_script")
                            if output_script:
                                print_script(output_script)
                                print("\n🎉 Naskah lo siap! Tinggal copy dan pake.")
                                return
                    else:
                        # Send revision request
                        print("\n💬 Oke, cerita apa yang mau diubah?")
                        revision = input(">>> ").strip()
                        # Continue with revised direction
                        graph.update_state(
                            config,
                            {"messages": [HumanMessage(content=revision)]}
                        )
                        continue

            # Check if complete
            if event.get("current_phase") == "complete" and event.get("output_script"):
                print_script(event["output_script"])
                print("\n🎉 Done! Naskah lo siap.")
                break

        # If we're still in mining phase, get user input
        phase = event.get("current_phase", "mining") if 'event' in dir() else "mining"
        if phase == "mining":
            # Interactive input loop
            while True:
                user_input = input(">>> ").strip()
                if user_input.lower() in ("quit", "exit", "q"):
                    print("\n👋 Bye! Cerita lo ada di sini, tinggal digali.")
                    break
                if not user_input:
                    continue

                # Send user message and continue
                state_update = {"messages": [HumanMessage(content=user_input)]}
                for event in graph.stream(state_update, config, stream_mode="values"):
                    messages = event.get("messages", [])
                    if messages:
                        last_msg = messages[-1]
                        if hasattr(last_msg, "content") and last_msg.content:
                            if last_msg.__class__.__name__ == "AIMessage":
                                print(f"\n🎭 Yui: {last_msg.content}\n")

                    if event.get("current_phase") == "complete":
                        if event.get("output_script"):
                            print_script(event["output_script"])
                        break

    except KeyboardInterrupt:
        print("\n\n👋 Session interrupted. Your progress is saved.")


def main():
    parser = argparse.ArgumentParser(description="Arcwright — Storytelling AI")
    parser.add_argument(
        "--platform",
        choices=PLATFORMS,
        default="general",
        help="Target platform for your story"
    )
    args = parser.parse_args()
    run_session(platform=args.platform)


if __name__ == "__main__":
    main()
