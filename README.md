# LLM Parliament 🏛️

![parliament](parliament.png)

**LLM Parliament** is an adversarial multi-agent debate platform where AI models debate, rebut, and moderate complex topics in real-time.

Unlike a simple chatbot, this system orchestrates a structured "parliamentary" session with a **Proponent**, a **Critic**, and a neutral **Moderator** who ensures the debate stays on topic and reaches a meaningful conclusion.

---

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

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/yourusername/llm-parliament.git](https://github.com/yourusername/llm-parliament.git)
    cd llm-parliament
    ```

2.  **Set up environment variables:**
    Create a `.env` file in the root directory:
    ```bash
    OPENROUTER_API_KEY=sk-or-your-key-here
    BRAVE_API_KEY=your-brave-key-here  # Optional, enables search tool
    ```

3.  **Run the application:**
    
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

4.  **Open your browser:**
    Navigate to [http://localhost:5173](http://localhost:5173).

---

## 📖 Usage

1.  **Configure the House:** Use the sidebar to select the models for the *Government* (Proponent), *Opposition* (Critic), and the *Speaker* (Moderator).
2.  **Table a Motion:** Enter a debate topic in the main chat input (e.g., *"AI will do more harm than good"*).
3.  **Watch the Debate:** The Moderator will open the session, and the agents will take turns arguing. You can expand/collapse their speeches to read detailed points.
4.  **Review the Verdict:** At the end of the configured rounds, the Moderator will produce a summary table and key takeaways.

---

## 📂 Project Structure

```text
llm-parliament/
├── backend/
│   ├── debate_graph.py    # The LangGraph logic (Pro -> Mod -> Con loop)
│   ├── tools.py           # FastMCP tool definitions (Search, Rules)
│   ├── main.py            # FastAPI server & streaming endpoints
│   ├── state.py           # Shared state definition
│   └── openrouter.py      # LLM client wrapper
├── frontend/
│   ├── src/
│   │   ├── components/    # React components (ChatInterface, Sidebar)
│   │   └── api.js         # API client
│   └── package.json
├── start.sh               # Startup script
└── pyproject.toml         # Python dependencies