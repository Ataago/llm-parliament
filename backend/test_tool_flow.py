import asyncio
import os
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langchain_core.tools import StructuredTool
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from fastmcp import FastMCP

from backend.openrouter import get_chat_model
from backend.state import DebateState # We can reuse or define a simple state

# 1. Setup Environment
load_dotenv()

# 2. Define FastMCP Tool
mcp = FastMCP("TestServer")

@mcp.tool()
def add_numbers(a: int, b: int) -> int:
    """Add two numbers together."""
    print(f"   [TOOL] Executing add_numbers({a}, {b})")
    return a + b

# 3. Convert to LangChain Tool
def get_test_tools():
    # Helper to wrap the decorated function
    # FastMCP decorators might wrap the function, so we need to be careful.
    # But for a simple test, we can just use the function we defined.
    
    # NOTE: FastMCP tools are registered in mcp._tools (dict) usually, 
    # but let's just use the function directly since we defined it in this file.
    
    return [
        StructuredTool.from_function(
            func=add_numbers.fn, # Access the underlying function
            name="add_numbers",
            description="Add two numbers together."
        )
    ]

from typing import Annotated, TypedDict
from langgraph.graph.message import add_messages

class TestState(TypedDict):
    messages: Annotated[list, add_messages]

# 4. Define Graph Components
def run_test():
    print("--- Starting Tool Flow Verification ---")
    
    # Setup Tools
    tools = get_test_tools()
    tool_node = ToolNode(tools)
    
    # Setup Model
    # We use a smart model to ensure it knows how to call tools
    model = get_chat_model("openai/gpt-4o-mini") 
    model_with_tools = model.bind_tools(tools)
    
    # Define Agent Node
    def agent_node(state):
        print("   [AGENT] Thinking...")
        messages = state["messages"]
        # DEBUG PRINT
        for m in messages:
            print(f"      - Role: {m.type}, Content: {str(m.content)[:50]}...")
            if hasattr(m, 'tool_calls') and m.tool_calls:
                print(f"        Tool Calls: {m.tool_calls}")
        
        response = model_with_tools.invoke(messages)
        return {"messages": [response]}

    # Define Conditional Edge
    def should_continue(state):
        last_message = state["messages"][-1]
        if last_message.tool_calls:
            print("   [ROUTER] Tool call detected -> Going to 'tools'")
            return "tools"
        print("   [ROUTER] No tool call -> Ending")
        return END

    # Build Graph
    workflow = StateGraph(TestState) # Use TypedDict state
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", tool_node)
    
    workflow.set_entry_point("agent")
    
    workflow.add_conditional_edges("agent", should_continue)
    workflow.add_edge("tools", "agent")
    
    app = workflow.compile()
    
    # 5. Run it
    user_input = "Calculate 123 + 456. Then tell me the result."
    print(f"\nUser: {user_input}")
    
    initial_state = {"messages": [HumanMessage(content=user_input)]}
    
    for event in app.stream(initial_state):
        for key, value in event.items():
            if key == "agent":
                msg = value["messages"][0]
                print(f"   [OUTPUT] {msg.content}")
                if msg.tool_calls:
                    print(f"   [CALLS] {msg.tool_calls}")

if __name__ == "__main__":
    run_test()
