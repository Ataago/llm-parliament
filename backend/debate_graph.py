from typing import Literal
from langgraph.graph import StateGraph, END
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from langgraph.prebuilt import ToolNode

from backend.state import DebateState
from backend.openrouter import get_chat_model
from backend.tools import get_tools_list

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
        
        Include this ASCII Flowchart in your first message to explain the process:
        ```
        {config.get('ascii_graph', '[Graph not available]')}
        ```
        
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
        1. **Closing Statement**: A brief, polite closing (max 50 words).
        2. **Debate Overview (Table)**: A Markdown table comparing arguments.
           Columns: | Theme | Proponent's Evidence/Citations | Critic's Rebuttal/Facts |
        3. **Key Conflicts & Consensus**: 
           - Use bullet points.
           - **Bold** key terms.
           - Explicitly cite sources if tools were used (e.g., "Proponent cited X").
        4. **Winner Declaration** (Optional): declare a winner based on fact usage and logical consistency.

        Speak ONLY as the Moderator. Do NOT continue the debate. Ensure the output is visually rich and easy to read.
        """
        
        response = llm.invoke([SystemMessage(content=sys_msg)] + messages)
        response.name = "Moderator"
        return {"messages": [response], "next_speaker": "finish"}

    # Case 3: Transitioning between speakers
    last_message = messages[-1]
    last_speaker_name = getattr(last_message, "name", "Unknown")

    # RELEVANCE CHECK & SUMMARY GENERATION
    # The moderator reviews the history to keep things on track
    
    # Check if last message was a Tool Message (orphan or forced handover)
    if last_message.type == "tool":
        # Look back for the agent who spoke
        found_speaker = False
        for i in range(len(messages)-1, -1, -1):
            if messages[i].type == "ai" and messages[i].name in ["Proponent", "Critic", "Government", "Opposition"]:
                last_speaker_name = messages[i].name
                last_message_content = messages[i].content # Use their last spoken words
                found_speaker = True
                break
        if not found_speaker:
            last_speaker_name = "Unknown"
            last_message_content = "..."
    else:
        last_message_content = last_message.content

    relevance_prompt = f"""
    Review the last argument by the {last_speaker_name}:
    "{last_message_content}"
    
    Original Topic: "{topic}"
    
    Task:
    1. **Score the Performance**: Evaluate {last_speaker_name} on a scale of 1-5.
       Create a small Markdown table with these columns:
       | Metric | Score (1-5) | Comment |
       |--------|-------------|---------|
       | **Relevance** | ... | ... |
       | **Evidence** (Facts/Tools) | ... | ... |
       | **Logic** | ... | ... |
       | **Rhetoric** | ... | ... |
       
    2. **Transitions**: 
       - Summarize the debate so far (1 sentence).
       - Formulate a pivoting question/instruction for the NEXT speaker.
    
    Output format:
    [Score Table]
    
    [Summary]
    
    [Instruction for Next Speaker]
    """
    
    # We construct a specific instruction based on who spoke
    # We construct a specific instruction based on who spoke
    # And we increment the round count when the Critic finishes (completing a full pair)
    
    increment_round = 0
    
    if last_speaker_name == "Proponent":
        next_speaker = "con"
        role_instruction = "Pivot to the Critic. Ask them to challenge the Proponent's specific point."
    elif last_speaker_name == "Critic":
        next_speaker = "pro"
        role_instruction = "Pivot to the Proponent. Ask them to defend against the Critic's point."
        increment_round = 1 # Round complete
    else:
        # Default start or catch-all
        next_speaker = "pro" if current_round == 0 else "con"
        role_instruction = "Move the debate forward."

    final_sys_msg = f"""
    {relevance_prompt}
    
    {role_instruction}
    
    **Style Guidelines for Moderator:**
    1. **Structure**: Table first, then text.
    2. **Citations**: Explicitly mention if they used tools.
    3. **Tone**: Impartial but critical. 
    
    CRITICAL: Speak ONLY as the Moderator. Do NOT roleplay as the next speaker.
    """

    first_message = messages[0] if messages else None
    context_messages = [first_message] + messages[-5:] if len(messages) > 10 else messages
    
    # We pass more context now to allow the Moderator to cite past points
    # But we still want to be efficient. 
    # Let's try passing the FULL history if it's not huge.
    # Given this is a text debate, full history is usually best for context.
    
    response = llm.invoke(messages + [SystemMessage(content=final_sys_msg)])
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
    
    # Bind Tools
    tools = get_tools_list()
    llm_with_tools = llm.bind_tools(tools)
    
    # Only see the Moderator's last instruction to prevent hallucination
    # But we include the original topic to keep them grounded
    last_message = state["messages"][-1]
    
    # If the last message is a Tool Call result, we need to pass the context of that call
    # so the model knows what happened.
    # Otherwise, it's a fresh turn from the Moderator.
    
    if last_message.type == "tool":
        # We are continuing a turn.
        # We need to find the original system instruction from the Moderator (or reconstruct it)
        # AND include the tool call + tool output.
        # Simplest way: Pass the last 3 messages: [Moderator/Sys, Agent(Call), Tool(Result)]
        # However, the Moderator/Sys wasn't a real message in the list, it was a SystemMessage passed in invoke.
        
        # We reconstruct the System Message
        sys_msg_content = f"""
        You are the PROPONENT in a debate about: "{config['topic']}"
        Your Stance: Support the topic.
        
        You have just used a tool to gather information.
        Incorporating these findings, please complete your argument.
        
        Instructions:
        1. Use the tool output to strengthen your point.
        2. Keep your argument focused on the original topic.
        3. Be conversational but factual.
        4. Keep it under 150 words.
        """
        sys_msg = SystemMessage(content=sys_msg_content)
        
        # We retrieve the recent history of this turn
        # The history in 'messages' has everything.
        # We really just need the last few messages that led here.
        # But passing all messages since the last Moderator turn is safer.
        
        # Let's pass the FULL messages to avoid orphaned tool calls (Anthropic Error 400)
        # We assume the state["messages"] is a valid conversation history.
        # We append the System Message to the list for the API call.
        # Ideally, SystemMessage should be first. 
        # But since we can't easily insert at 0 without copying the whole list,
        # and LangChain handles a list of messages...
        # A SystemMessage at the end is sometimes treated as a "User/System" instruction.
        
        context_messages = [sys_msg] + state["messages"]
        response = llm_with_tools.invoke(context_messages)
        
    else:
        # Fresh Instruction from Moderator
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
        response = llm_with_tools.invoke([sys_msg])

    response.name = "Proponent"
    
    return {"messages": [response]}

def con_agent_node(state: DebateState):
    """The Critic (Against the topic)."""
    config = state["config"]
    llm = get_chat_model(config.get("con_model", "anthropic/claude-3.5-sonnet"))

    # Bind Tools
    tools = get_tools_list()
    llm_with_tools = llm.bind_tools(tools)
    
    last_message = state["messages"][-1]
    
    if last_message.type == "tool":
        sys_msg_content = f"""
        You are the CRITIC in a debate about: "{config['topic']}"
        Your Stance: Oppose or Critically Analyze the topic.
        
        You have just used a tool to gather information.
        Incorporating these findings, please complete your argument.
        
        Instructions:
        1. Use the tool output to strengthen your point.
        2. Keep your argument focused.
        3. Be conversational, skeptical, and sharp.
        4. Keep it under 150 words.
        """
        sys_msg = SystemMessage(content=sys_msg_content)
        context_messages = [sys_msg] + state["messages"]
        response = llm_with_tools.invoke(context_messages)
        
    else:
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
        response = llm_with_tools.invoke([sys_msg])

    response.name = "Critic"
    
    return {"messages": [response]}

def build_debate_graph():
    workflow = StateGraph(DebateState)
    
    workflow.add_node("moderator", moderator_node)
    workflow.add_node("pro_agent", pro_agent_node)
    workflow.add_node("con_agent", con_agent_node)
    
    # Add ToolNode
    tools = get_tools_list()
    workflow.add_node("tools", ToolNode(tools))
    
    workflow.set_entry_point("moderator")
    
    # CONDITIONAL EDGES
    
    def router(state):
        last_message = state["messages"][-1]
        
        # 1. Check for Tool Calls
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
        
        # 2. Check for Moderator Routing
        # If the last message was from an Agent (Pro/Con) and NOT a tool call, 
        # it means they finished their turn. We MUST go back to Moderator.
        
        last_sender = getattr(last_message, "name", "Unknown")
        if last_sender in ["Proponent", "Critic"]:
            return "moderator"

        # Otherwise, follow the set speaker order (usually for entering the node first time)
        if state.get("next_speaker") == "finish":
            return END
        elif state.get("next_speaker") == "pro":
            return "pro_agent"
        elif state.get("next_speaker") == "con":
            return "con_agent"
        
        return "moderator" # Default fallback
            
    workflow.add_conditional_edges("moderator", router)
    workflow.add_conditional_edges("pro_agent", router)
    workflow.add_conditional_edges("con_agent", router)
    
    # Tool output always returns to the agent who called it?
    # Actually, in a multi-agent graph, we need to know who called it to send it back.
    # But usually, the "messages" history preserves the conversation flow.
    # The simplest way is to route tools back to the Moderator to keep order,
    # OR route back to the agent if we want a ReAct loop.
    # let's try routing back to the moderator for simplicity in this turn-based game,
    # UNLESS the agent hasn't finished their turn.
    
    # For now: Tools -> Moderator. The Moderator will see the tool output and the agent's attempt.
    # Actually, standard ReAct is Agent -> Tool -> Agent.
    # Let's support Agent -> Tool -> Agent (simple ReAct) by checking the last sender name.
    
    def tool_router(state):
        messages = state["messages"]
        last_tool_msg = messages[-1] # This is the ToolMessage
        
        # Find who called the tool
        caller = "unknown"
        for i in range(len(messages)-1, -1, -1):
            if messages[i].type == "ai" and messages[i].tool_calls:
                caller = messages[i].name
                break
        
        # LOOP PROTECTION
        # Check if we have too many tool calls in a row for this speaker
        # We look back to see how many (AI -> Tool) pairs exist recently
        tool_chain_count = 0
        for i in range(len(messages)-1, 0, -1):
            msg = messages[i]
            prev_msg = messages[i-1]
            if msg.type == "tool" and prev_msg.type == "ai" and prev_msg.name == caller:
                tool_chain_count += 1
            elif msg.type == "ai" and msg.name != caller:
                break # Different speaker took a turn
        
        # If agent has called tools more than twice in a row, force handover to Moderator
        if tool_chain_count >= 2:
            return "moderator"

        if caller == "Proponent":
            return "pro_agent"
        elif caller == "Critic":
            return "con_agent"
        
        return "moderator"

    workflow.add_conditional_edges("tools", tool_router)
    
    return workflow.compile()