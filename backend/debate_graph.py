from typing import Literal
from langgraph.graph import StateGraph, END
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from backend.state import DebateState
from backend.openrouter import get_chat_model

def moderator_node(state: DebateState):
    """
    The Moderator.
    1. Sets the stage.
    2. Checks relevance (Scoring).
    3. Summarizes context.
    4. Asks the next speaker a relevant question.
    """
    config = state["config"]
    messages = state["messages"]
    current_round = state.get("round_count", 0)
    topic = config['topic']
    
    # Initialize Moderator LLM
    llm = get_chat_model(config.get("moderator_model", "anthropic/claude-3.5-sonnet"))
    
    # --- LOGIC: DECIDE WHAT TO DO ---
    
    # Case 1: Start of Conversation (Only User topic exists)
    if len(messages) == 1 and messages[0].type == "human":
        sys_msg = f"""
        You are the Moderator of a friendly but intellectual debate.
        Topic: "{topic}"
        
        Your Task: Kick off the discussion.
        1. Briefly introduce the topic in 1 sentence.
        2. Ask the Proponent to share their opening thoughts.
        
        Keep it conversational and inviting.
        """
        response = llm.invoke([SystemMessage(content=sys_msg)])
        response.name = "Moderator"
        return {"messages": [response], "next_speaker": "pro", "round_count": 0}

    # Case 2: Max Rounds Reached - FINAL SUMMARY
    if current_round >= config["max_rounds"]:
        sys_msg = """The discussion has concluded. 
        
        Your Task: Provide a structured final summary of the entire conversation.
        
        Format Requirements:
        1. Start with a brief closing statement thanking the participants.
        2. Create a MARKDOWN TABLE comparing the key arguments of the Proponent and the Critic.
           Columns: | Theme | Proponent's View | Critic's View |
        3. Provide a list of 3-5 Bullet Points summarizing the main consensus or conflict areas.
        
        Speak ONLY as the Moderator. Do NOT continue the debate."""
        
        response = llm.invoke([SystemMessage(content=sys_msg)] + messages)
        response.name = "Moderator"
        return {"messages": [response], "next_speaker": "finish"}

    # Case 3: Transitioning between speakers
    last_message = messages[-1]
    last_speaker_name = getattr(last_message, "name", "Unknown")

    # RELEVANCE CHECK & SUMMARY GENERATION
    # The moderator reviews the history to keep things on track
    relevance_prompt = f"""
    Review the last argument by the {last_speaker_name}:
    "{last_message.content}"
    
    Original Topic: "{topic}"
    
    Task:
    1. Is this on topic? (Yes/No)
    2. Summarize the debate so far in 1-2 sentences to orient the next speaker.
    3. Formulate a pivoting question for the NEXT speaker.
    
    Output format: Just the question/instruction for the next speaker. 
    If off-topic, gently steer them back.
    """
    
    # We construct a specific instruction based on who spoke
    if last_speaker_name == "Proponent":
        next_speaker = "con"
        role_instruction = "Pivot to the Critic. Ask them to challenge the Proponent's specific point."
        increment_round = 0
    elif last_speaker_name == "Critic":
        next_speaker = "pro"
        role_instruction = "Pivot to the Proponent. Ask them to defend against the Critic's point."
        increment_round = 1
    else:
        next_speaker = "pro" if current_round == 0 else "con"
        role_instruction = "Move the debate forward."
        increment_round = 0

    final_sys_msg = f"""
    {relevance_prompt}
    
    {role_instruction}
    
    CRITICAL: Speak ONLY as the Moderator. Do NOT roleplay as the next speaker.
    """

    # Generate the transition speech using recent context
    response = llm.invoke(messages[-3:] + [SystemMessage(content=final_sys_msg)])
    response.name = "Moderator"
    
    return {
        "messages": [response], 
        "next_speaker": next_speaker, 
        "round_count": current_round + increment_round
    }

def pro_agent_node(state: DebateState):
    """The Proponent (For the topic)."""
    config = state["config"]
    llm = get_chat_model(config.get("pro_model", "anthropic/claude-3.5-sonnet"))
    
    # Only see the Moderator's last instruction to prevent hallucination
    # But we include the original topic to keep them grounded
    last_message = state["messages"][-1]
    
    sys_msg = SystemMessage(content=f"""
    You are the PROPONENT in a debate about: "{config['topic']}"
    Your Stance: Support the topic.
    
    The Moderator has just asked you:
    "{last_message.content}"
    
    Instructions:
    1. Address the Moderator's question directly.
    2. Keep your argument focused on the original topic: "{config['topic']}".
    3. Be conversational but factual.
    4. Keep it under 150 words.
    """)
    
    response = llm.invoke([sys_msg])
    response.name = "Proponent"
    
    return {"messages": [response]}

def con_agent_node(state: DebateState):
    """The Critic (Against the topic)."""
    config = state["config"]
    llm = get_chat_model(config.get("con_model", "anthropic/claude-3.5-sonnet"))
    
    last_message = state["messages"][-1]
    
    sys_msg = SystemMessage(content=f"""
    You are the CRITIC in a debate about: "{config['topic']}"
    Your Stance: Oppose or Critically Analyze the topic.
    
    The Moderator has just asked you:
    "{last_message.content}"
    
    Instructions:
    1. Address the Moderator's question directly.
    2. Keep your argument focused on the original topic: "{config['topic']}".
    3. Be conversational, skeptical, and sharp.
    4. Keep it under 150 words.
    """)
    
    response = llm.invoke([sys_msg])
    response.name = "Critic"
    
    return {"messages": [response]}

def build_debate_graph():
    workflow = StateGraph(DebateState)
    
    workflow.add_node("moderator", moderator_node)
    workflow.add_node("pro_agent", pro_agent_node)
    workflow.add_node("con_agent", con_agent_node)
    
    workflow.set_entry_point("moderator")
    
    def route_speaker(state):
        if state["next_speaker"] == "finish":
            return END
        elif state["next_speaker"] == "pro":
            return "pro_agent"
        elif state["next_speaker"] == "con":
            return "con_agent"
            
    workflow.add_conditional_edges("moderator", route_speaker)
    
    workflow.add_edge("pro_agent", "moderator")
    workflow.add_edge("con_agent", "moderator")
    
    return workflow.compile()