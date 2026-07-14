import pytest
from agents.state import ArcwrightState
from graph.pipeline import make_initial_state

def test_initial_state():
    """Test pembuatan initial state yang benar."""
    state = make_initial_state(user_name="Budi", platform="youtube")
    
    assert state["user_profile"]["name"] == "Budi"
    assert state["user_profile"]["platform_target"] == "youtube"
    assert state["current_phase"] == "mining"
    assert state["story_fragments"] == []
    assert state["outline_approved"] is False
    assert state["error_count"] == 0
    assert "session_id" in state
    
def test_state_immutability_and_types():
    """Memastikan TypedDict terdefinisi dengan struktur yang diharapkan."""
    # Walaupun TypedDict di Python tidak memaksakan runtime type checking secara strict,
    # kita memvalidasi struktur key-nya
    state = make_initial_state()
    expected_keys = {
        "session_id", "current_phase", "user_profile", "messages",
        "story_fragments", "interview_questions_asked", "agent_notes",
        "rag_context", "web_research", "deep_dive_analysis", "validation_result",
        "debate_rounds", "debate_log", "story_outline", "output_script",
        "outline_approved", "error_count"
    }
    
    assert set(state.keys()) == expected_keys
