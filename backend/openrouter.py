import os
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()

def get_chat_model(model_name: str, temperature: float = 0.7):
    """
    Returns a LangChain ChatOpenAI object configured for OpenRouter.
    """
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("CRITICAL ERROR: OPENROUTER_API_KEY not found in environment.")
        raise ValueError("OPENROUTER_API_KEY not found in .env")

    print(f"Initializing ChatOpenAI for model: {model_name}")

    return ChatOpenAI(
        model=model_name,
        openai_api_key=api_key,
        openai_api_base="https://openrouter.ai/api/v1",
        temperature=temperature,
        default_headers={
            "HTTP-Referer": "http://localhost:5173",
            "X-Title": "LLM Parliament"
        },
        max_retries=1, # Don't wait too long if it fails
        request_timeout=60 # Timeout after 60s
    )