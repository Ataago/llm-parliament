"""FastAPI backend for LLM Parliament."""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import uuid
import json
import asyncio

from langchain_core.messages import HumanMessage

from . import storage
from .debate_graph import build_debate_graph
from .openrouter import get_chat_model # Import for title generation

import mlflow
from mlflow.langchain.langchain_tracer import MlflowLangchainTracer

mlflow.set_tracking_uri("http://127.0.0.1:5000")
mlflow.set_experiment("LLM Parliament")


app = FastAPI(title="LLM Parliament API")

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class CreateConversationRequest(BaseModel):
    pass

class DebateConfig(BaseModel):
    pro_model: str = "anthropic/claude-3.5-sonnet"
    con_model: str = "anthropic/claude-3.5-sonnet"
    moderator_model: str = "anthropic/claude-3.5-sonnet"
    max_rounds: int = 3
    enable_tools: bool = True

class SendMessageRequest(BaseModel):
    content: str
    config: Optional[DebateConfig] = None

async def generate_conversation_title(content: str) -> str:
    """Generate a short title for the conversation using a cheap model."""
    try:
        # Use a reliable fast model for title generation
        llm = get_chat_model("google/gemini-2.5-flash", temperature=0.7)
        messages = [
            {"role": "system", "content": "Generate a very short, 3-5 word title for this debate topic. Do not use quotes."},
            {"role": "user", "content": content}
        ]
        response = llm.invoke(messages)
        return response.content.strip().strip('"')
    except Exception as e:
        print(f"Title generation failed: {e}")
        return "New Debate"

@app.get("/")
async def root():
    return {"status": "ok", "service": "LLM Parliament API"}

@app.get("/api/conversations")
async def list_conversations():
    return storage.list_conversations()

@app.post("/api/conversations")
async def create_conversation(request: CreateConversationRequest):
    conversation_id = str(uuid.uuid4())
    conversation = storage.create_conversation(conversation_id)
    return conversation

@app.get("/api/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation

@app.post("/api/conversations/{conversation_id}/message/stream")
async def send_message_stream(conversation_id: str, request: SendMessageRequest):
    """
    Stream the debate graph execution.
    """
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    is_first_message = len(conversation["messages"]) == 0
    
    # Save User Message
    user_msg = {"role": "user", "content": request.content, "name": "User"}
    storage.add_message(conversation_id, user_msg)

    # Build Logic Graph
    graph_app = build_debate_graph()
    
    # Prepare Initial State
    # FIX: Pydantic v2 uses model_dump(), .dict() is deprecated
    config_dict = request.config.model_dump() if request.config else {
        "pro_model": "anthropic/claude-3.5-sonnet",
        "con_model": "anthropic/claude-3.5-sonnet",
        "moderator_model": "anthropic/claude-3.5-sonnet",
        "max_rounds": 3,
        "enable_tools": True,
        "topic": request.content
    }
    
    # Ensure topic is set
    config_dict["topic"] = request.content
    
    # Generate Dynamic ASCII Graph
    try:
        from langchain_core.runnables.graph import MermaidDrawMethod
        # draw_ascii() is a method on the CompiledGraph.get_graph()
        ascii_graph = graph_app.get_graph().draw_ascii()
        config_dict["ascii_graph"] = ascii_graph
    except Exception as e:
        print(f"Failed to draw ASCII graph: {e}")
        config_dict["ascii_graph"] = "[Graph Visualization Failed]"

    initial_state = {
        "messages": [HumanMessage(content=request.content)],
        "config": config_dict,
        "round_count": 0,
        "speaker_order": [],
        "next_speaker": "moderator"
    }

    async def event_generator():
        try:
            # 1. Generate Title if new
            if is_first_message:
                title = await generate_conversation_title(request.content)
                storage.update_conversation_title(conversation_id, title)
                yield f"data: {json.dumps({'type': 'title', 'data': title})}\n\n"
            
            # 2. Stream Graph Events
            # We use 'updates' mode to see what each node produces
            # Use MlflowLangchainTracer to capture async events
            config = {"callbacks": [MlflowLangchainTracer()]}
            
            with mlflow.start_run(run_name=f"Debate: {conversation_id[:8]}", nested=True):
                async for event in graph_app.astream(initial_state, config=config, stream_mode="updates"):
                    for node_name, node_output in event.items():
                        
                        # Extract message from the node output
                        if "messages" in node_output and node_output["messages"]:
                            last_msg = node_output["messages"][-1]
                            content = last_msg.content
                            sender_name = getattr(last_msg, "name", node_name)
                            
                            # Prepare payload
                            raw_msg = last_msg
                            msg_type = "message"
                            
                            # Detect Message Type
                            if raw_msg.type == "tool":
                                msg_type = "tool_output"
                                sender_name = "Tool" # Or specific tool name if available
                            elif raw_msg.type == "ai" and getattr(raw_msg, "tool_calls", None):
                                msg_type = "tool_call"
                            
                            payload = {
                                "type": msg_type,
                                "data": {
                                    "role": "assistant" if raw_msg.type == "ai" else "tool",
                                    "name": sender_name,
                                    "content": content,
                                    "tool_calls": getattr(raw_msg, "tool_calls", None),
                                    "tool_call_id": getattr(raw_msg, "tool_call_id", None)
                                }
                            }
                            
                            # Save to storage immediately
                            storage.add_message(conversation_id, payload["data"])
                            
                            # Stream to client
                            yield f"data: {json.dumps(payload)}\n\n"
                        
                        # Handle Moderator Decision events (next_speaker)
                        if "next_speaker" in node_output:
                            decision = {
                                "type": "status",
                                "data": f"Moderator decided: {node_output['next_speaker']} speaks next."
                            }
                            yield f"data: {json.dumps(decision)}\n\n"

            yield f"data: {json.dumps({'type': 'complete'})}\n\n"

        except Exception as e:
            print(f"Stream error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)