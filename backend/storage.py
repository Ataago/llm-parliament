"""JSON-based storage for conversations."""

import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
from .config import DATA_DIR

def ensure_data_dir():
    """Ensure the data directory exists."""
    Path(DATA_DIR).mkdir(parents=True, exist_ok=True)

def get_conversation_path(conversation_id: str) -> str:
    return os.path.join(DATA_DIR, f"{conversation_id}.json")

def create_conversation(conversation_id: str) -> Dict[str, Any]:
    ensure_data_dir()
    conversation = {
        "id": conversation_id,
        "created_at": datetime.utcnow().isoformat(),
        "title": "New Debate",
        "messages": [] # Simple list of {role, name, content, type}
    }
    path = get_conversation_path(conversation_id)
    with open(path, 'w') as f:
        json.dump(conversation, f, indent=2)
    return conversation

def get_conversation(conversation_id: str) -> Optional[Dict[str, Any]]:
    path = get_conversation_path(conversation_id)
    if not os.path.exists(path):
        return None
    with open(path, 'r') as f:
        return json.load(f)

def save_conversation(conversation: Dict[str, Any]):
    ensure_data_dir()
    path = get_conversation_path(conversation['id'])
    with open(path, 'w') as f:
        json.dump(conversation, f, indent=2)

def list_conversations() -> List[Dict[str, Any]]:
    ensure_data_dir()
    conversations = []
    for filename in os.listdir(DATA_DIR):
        if filename.endswith('.json'):
            path = os.path.join(DATA_DIR, filename)
            try:
                with open(path, 'r') as f:
                    data = json.load(f)
                    conversations.append({
                        "id": data["id"],
                        "created_at": data["created_at"],
                        "title": data.get("title", "New Debate"),
                        "message_count": len(data["messages"])
                    })
            except Exception:
                continue
    conversations.sort(key=lambda x: x["created_at"], reverse=True)
    return conversations

def add_message(conversation_id: str, message: Dict[str, Any]):
    """
    Generic add message function.
    Message should have: role, content, name (optional), type (optional)
    """
    conversation = get_conversation(conversation_id)
    if conversation is None:
        raise ValueError(f"Conversation {conversation_id} not found")
    
    conversation["messages"].append(message)
    save_conversation(conversation)

def update_conversation_title(conversation_id: str, title: str):
    conversation = get_conversation(conversation_id)
    if conversation:
        conversation["title"] = title
        save_conversation(conversation)
        