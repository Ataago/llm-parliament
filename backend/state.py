from typing import TypedDict, List, Annotated
from langgraph.graph.message import add_messages

class DebateConfig(TypedDict):
    """Configuration passed from the Frontend User."""
    topic: str
    pro_model: str
    con_model: str
    moderator_model: str
    max_rounds: int
    enable_tools: bool

class DebateState(TypedDict):
    """The shared state of the debate graph."""
    # 'add_messages' ensures we append to history, not overwrite it
    messages: Annotated[List[dict], add_messages]
    
    # Track the current state of the game
    round_count: int
    speaker_order: List[str]  # e.g. ["pro", "con"]
    next_speaker: str
    
    # Store the user configuration
    config: DebateConfig
