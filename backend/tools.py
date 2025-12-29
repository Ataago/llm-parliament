import os
import httpx
from fastmcp import FastMCP
from dotenv import load_dotenv
from langchain_core.tools import StructuredTool

# Load environment variables
load_dotenv()

# Initialize the FastMCP Server
# This manages the tool definitions and allows us to use @mcp.tool()
mcp = FastMCP("ParliamentLibrary")

@mcp.tool()
async def search_web(query: str, max_results: int = 3) -> str:
    """
    Search the web for facts, statistics, or recent news to support an argument.
    Use this when you need citations or evidence.
    """
    api_key = os.getenv("BRAVE_API_KEY")
    if not api_key:
        return "Error: Web Search is disabled (No BRAVE_API_KEY found in .env)."

    url = "https://api.search.brave.com/res/v1/web/search"
    headers = {
        "X-Subscription-Token": api_key,
        "Accept": "application/json"
    }
    params = {"q": query, "count": max_results}

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=headers, params=params, timeout=10.0)
            
        if resp.status_code != 200:
            return f"Search failed with status {resp.status_code}"

        data = resp.json()
        results = []
        
        # Parse Brave's specific JSON structure
        if "web" in data and "results" in data["web"]:
            for item in data["web"]["results"]:
                title = item.get('title', 'No Title')
                url = item.get('url', 'No URL')
                desc = item.get('description', 'No Description')
                results.append(f"SOURCE: {title}\nLINK: {url}\nSUMMARY: {desc}\n")
        
        if not results:
            return "No results found."
            
        return "\n".join(results)
    
    except Exception as e:
        return f"Search error: {str(e)}"

@mcp.tool()
def get_debate_rules() -> str:
    """
    Retrieve the official Standing Orders (Rules of Debate) for the current session.
    The Moderator uses this to verify if an agent is breaking protocol.
    """
    return """
    STANDING ORDERS OF THE LLM PARLIAMENT:
    1. Stay on Topic: All arguments must directly address the motion.
    2. No Ad Hominem: Attack the argument, not the opponent.
    3. Citations: Use 'search_web' to backup statistical claims.
    4. Brevity: Speak efficiently (under 150 words preferred).
    5. Decorum: Maintain a formal but passionate tone.
    """

def get_tools_list():
    """
    Returns the FastMCP tools converted to LangChain StructuredTools.
    
    This fixes the 'Unsupported function' error. LangChain's bind_tools() expects
    callable objects (functions) or Pydantic models. FastMCP's internal tool
    representation is wrapped, so we must extract the underlying function 
    and wrap it in StructuredTool to make it compatible with ChatOpenAI.
    """
    langchain_tools = []
    
    # Iterate over all tools registered with the FastMCP server
    for tool in mcp.list_tools():
        # FastMCP's tool.fn holds the original function with signature
        # We wrap it in StructuredTool to make it compatible with LangChain
        lc_tool = StructuredTool.from_function(
            func=tool.fn,
            name=tool.name,
            description=tool.description
        )
        langchain_tools.append(lc_tool)
        
    return langchain_tools