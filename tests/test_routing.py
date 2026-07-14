import pytest
from graph.edges import story_director_routing, validator_debate_routing
from agents.state import ArcwrightState
from graph.pipeline import make_initial_state

def test_story_director_routing_mining():
    """Test routing di fase mining."""
    state = make_initial_state()
    state["current_phase"] = "mining"
    
    # 1. Belum ada RAG context -> ke Librarian
    assert story_director_routing(state) == "rag_librarian"
    
    # 2. RAG context sudah ada -> ke Miner
    state["rag_context"] = ["Framework 1"]
    assert story_director_routing(state) == "story_miner"

def test_story_director_routing_enriching():
    """Test routing di fase enriching dengan logic paralel."""
    state = make_initial_state()
    state["current_phase"] = "enriching"
    
    # 1. Keduanya belum jalan -> return Send objects (parallel)
    routes = story_director_routing(state)
    assert isinstance(routes, list)
    assert len(routes) == 2
    assert {r.node for r in routes} == {"deep_dive", "web_researcher"}
    
    # 2. Deep Dive sudah, Web Research belum -> dispatch Web Research
    state["deep_dive_analysis"] = {"theme": "hero"}
    routes = story_director_routing(state)
    assert isinstance(routes, list)
    assert len(routes) == 1
    assert routes[0].node == "web_researcher"
    
    # 3. Keduanya sudah -> return ke story_director
    state["web_research"] = ["Data 1"]
    assert story_director_routing(state) == "story_director"
    
def test_story_director_routing_outlining():
    """Test routing dari outline ke approval."""
    state = make_initial_state()
    state["current_phase"] = "outlining"
    
    # Belum ada outline
    assert story_director_routing(state) == "outline_writer"
    
    # Sudah ada outline, minta user approval
    state["story_outline"] = "Act 1: Beginning..."
    assert story_director_routing(state) == "user_approval"

def test_validator_debate_routing():
    """Test routing saat proses debate validator."""
    state = make_initial_state()
    
    # 1. Outline belum approve -> revisi outline
    state["outline_approved"] = False
    assert validator_debate_routing(state) == "outline_writer"
    
    # 2. Outline approve tapi validation fail -> back to director
    state["outline_approved"] = True
    state["validation_result"] = {"pass": False}
    assert validator_debate_routing(state) == "story_director"
    
    # 3. Validation pass
    state["outline_approved"] = True
    state["validation_result"] = {"pass": True}
    assert validator_debate_routing(state) == "story_director"
