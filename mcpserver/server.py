import os
import requests
from mcp.server.mcpserver import MCPServer

# Talks to your existing QAVentra API — reuses all the retrieval logic
# you already built, tested, and fixed. Nothing is duplicated here.
QAVENTRA_API_URL = os.getenv("QAVENTRA_API_URL", "http://localhost:8000")

mcp = MCPServer("QAVentra")


@mcp.tool()
def ask_qaventra(question: str, filter: str = "all") -> dict:
    """
    Ask QAVentra a question grounded in the QA team's knowledge base:
    test cases, Selenium/Playwright automation code, JIRA tickets, PRDs,
    company docs, and meeting notes. Returns a cited, grounded answer —
    never general internet knowledge.

    Args:
        question: The question to ask, in plain English.
        filter: Optional search scope — "all" (default), "jira",
            "playwright", or "prd".

    Returns:
        A dict with "answer" (the cited answer text) and "sources"
        (a list of citation labels and relevance scores).
    """
    response = requests.post(
        f"{QAVENTRA_API_URL}/ask",
        json={"question": question, "filter": filter},
        timeout=60
    )
    response.raise_for_status()
    return response.json()


@mcp.tool()
def qaventra_stats() -> dict:
    """Returns how many artifacts (test cases, code chunks, JIRA tickets,
    docs, meeting notes) are currently indexed in QAVentra's knowledge base."""
    response = requests.get(f"{QAVENTRA_API_URL}/stats", timeout=10)
    response.raise_for_status()
    return response.json()


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8001)
