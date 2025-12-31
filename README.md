# LLM Parliament 🏛️

![parliament](parliament2.png)

**LLM Parliament** is an adversarial multi-agent debate platform where AI models debate, rebut, and moderate complex topics in real-time.

Unlike a simple chatbot, this system orchestrates a structured "parliamentary" session with a **Proponent**, a **Critic**, and a neutral **Moderator** who ensures the debate stays on topic and reaches a meaningful conclusion.

---

> **Vibe Code Alert**
> This project was 99% vibe coded as a fun Christmas break project, expanding directly from **[llm-council](https://github.com/karpathy/llm-council/tree/master)** to see how constructive feedback from different LLMs can help improve results. It currently features contextual data gathering via **MCP (Web Search)** and is designed to be easily updated with more tools as needed. Code is ephemeral now ask your LLM to change it in whatever way you like.

## ✨ Features

* **Adversarial Debate Engine:** Three specialized AI agents (Proponent, Critic, Moderator) interact in a cyclic graph to explore a topic deeply.
* **Structured Moderation:** The Moderator agent dynamically summarizes arguments, enforces relevance, and pivots the conversation with challenging questions.
* **Tool-Use Capabilities:** Agents can use tools (like web search) to fact-check their arguments (powered by **FastMCP**).
* **Customizable "Members":** Choose different LLMs (via **OpenRouter**) for each role. Pit Claude 3.5 against GPT-4o!
* **Real-time Streaming:** Watch the debate unfold live with a reactive UI.
* **Final Summary:** The session concludes with a structured Markdown table comparing key arguments and a bulleted summary.

## 🛠️ Tech Stack

* **Backend:** Python, FastAPI, LangGraph (for agent orchestration), FastMCP (for tools).
* **Frontend:** React, Vite, Tailwind CSS (via custom styles).
* **AI:** OpenRouter (access to top-tier models).

---

## 🚀 Quick Start

### Prerequisites

* Python 3.10+
* Node.js & npm
* An **OpenRouter** API Key
* *(Optional)* A **Brave Search** API Key for web search capabilities.

### Installation

1. **Install Dependencies:**

    *Backend:*

    ```bash
    uv sync
    ```

    *Frontend:*

    ```bash
    cd frontend
    npm install
    cd ..
    ```

2. **Set up environment variables:**
    Create a `.env` file in the root directory:

    ```bash
    OPENROUTER_API_KEY=sk-or-your-key-here
    BRAVE_API_KEY=your-brave-key-here  # Optional, enables search tool
    ```

3. **Run the application:**

    We provide a handy start script that launches both backend and frontend:

    ```bash
    chmod +x start.sh
    ./start.sh
    ```

    **Alternatively, you can run them manually:**

    *Backend:*

    ```bash
    uv run python -m backend.main 
    # OR 
    python -m backend.main
    ```

    *Frontend:*

    ```bash
    cd frontend 
    npm install 
    npm run dev
    ```

4. **Open your browser:**
    Navigate to [http://localhost:5173](http://localhost:5173).

---

## 📖 Usage

1. **Configure the House:** Use the sidebar to select the models for the *Government* (Proponent), *Opposition* (Critic), and the *Speaker* (Moderator).
2. **Table a Motion:** Enter a debate topic in the main chat input (e.g., *"AI will do more harm than good"*).
3. **Watch the Debate:** The Moderator will open the session, and the agents will take turns arguing. You can expand/collapse their speeches to read detailed points.
4. **Review the Verdict:** At the end of the configured rounds, the Moderator will produce a summary table and key takeaways.

---

## ⚠️ Limitations & Future Improvements

While functional, this project is an active experiment in agentic orchestration. We are open to contributions to address the following engineering challenges:

### Role Confusion & Narrow Debates
* **Issue:** Occasionally, agents (Pro/Con) may lose track of their specific stance or "roleplay" the opponent if the message history becomes too long or confusing.
* **Goal:** Improve the `debate_graph.py` logic to pass selective context (e.g., only the last 3 turns + a running summary) rather than the full chat history. This will keep the agents focused on the immediate argument.

### Topic Drift
* **Issue:** Long debates can sometimes drift away from the original motion.
* **Goal:** Implement a "Relevance Scorer" node in the graph. The Moderator should automatically check if the last argument was on-topic and, if not, issue a specific instruction to "steer the debate back" to the core motion.

### Tool Usage Hallucinations
* **Issue:** Agents currently have access to tools but may hallucinate using them or fail to parse results correctly.
* **Goal:** Enhance the FastMCP integration to robustly handle tool outputs and retry logic if a tool call fails.

### Dynamic Debate Formats
* **Goal:** Allow users to dynamically select the flow (graph structure) of the debate. Future versions could support different competitive formats (e.g., British Parliamentary, Oxford-style) by swapping out the LangGraph configuration.

### Unified MLflow Tracing
* **Goal:** Integrate unified MLflow runs per conversation to trace agent thoughts, tool usage, and moderation logic across multiple turns.

### Final Judge & Voting
* **Goal:** Implement a "Judge" agent to review the debate history at the end and declare a winner based on argument strength and factual accuracy.

---

## 🤝 Contributing

Pull requests are welcome! For major changes, please open an issue first to discuss what you would like to change.
