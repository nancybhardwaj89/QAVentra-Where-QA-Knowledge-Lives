# QAVentra
### Where QA Knowledge Lives.

A self-hosted, multi-source **Hybrid RAG** (Retrieval-Augmented Generation) system built for QA teams. Ask one question in plain English — get one cited answer, grounded in your team's actual test cases, automation code, JIRA tickets, PRDs, and meeting notes. Never general internet knowledge.

---

## Why

Every QA team loses real hours to the same problem: knowledge scattered across a test case spreadsheet, JIRA, a PRD nobody re-reads after sprint planning, and automation logic buried three folders deep in a Selenium or Playwright repo. QAVentra collapses all of that into a single, cited search.

## What it does

- **Unified knowledge base** — test cases, Selenium/Playwright automation code, JIRA tickets, PRDs/SRS/BRD/FRD, company docs, and meeting notes, all searchable together
- **Cited, grounded answers** — every claim in an answer links back to the exact source that supports it; if the answer isn't in the knowledge base, QAVentra says so instead of guessing
- **Hybrid retrieval** — dense + sparse embeddings fused with reranking, so both semantic meaning and exact keyword matches are captured
- **Metadata-aware retrieval** — a bug-related question is biased toward JIRA results, a requirements question toward PRDs, instead of treating every artifact type as equally relevant
- **Continuous ingestion** — an hourly background sweep detects new, changed, *and deleted* content across every source, so the knowledge base never goes stale
- **MCP server** — query QAVentra directly from Claude or any MCP-compatible client, not just the web UI

---

## Architecture

```
Knowledge Sources                          Pipeline
──────────────────                         ────────
JIRA ───────────┐
Test Cases ─────┤
Test Plans ─────┤
SRS / PRDs ─────┤
Company Docs ───┼──→ Continuous Ingestion
Jenkins Logs ───┤           ↓
Playwright ─────┤       BGE-M3 (dense + sparse embeddings)
Selenium ───────┘           ↓
                         Qdrant (hybrid vector search)
                           ↓
                    Metadata-aware filtering/boosting
                           ↓
                    bge-reranker-v2-m3
                           ↓
                    Groq (grounded generation)
                           ↓
                 Answer + Citations
```

---

## Chunking Strategy

Different content types need different chunking, so nothing important gets cut in half:

| Source | Strategy | Size | Overlap |
|---|---|---|---|
| Test cases | Never split — 1 row = 1 chunk | Whole row | None |
| JIRA tickets | 1 ticket = 1 chunk; long comment threads become linked sub-chunks | ~600 tokens (comments) | 100 tokens |
| Code (Selenium/Playwright) | Split at function/class boundaries | ~500–800 tokens | 50–100 tokens |
| PRDs / company docs | Heading/paragraph-aware | ~500–800 tokens | 100–150 tokens |
| Meeting notes | Paragraph-aware, longer blocks | ~800–1,000 tokens | 150–200 tokens |

---

## Tech Stack

All embedding, search, and reranking components are **open source**.

| Layer | Technology |
|---|---|
| Embeddings | [BAAI/bge-m3](https://huggingface.co/BAAI/bge-m3) — hybrid dense + sparse |
| Reranker | [bge-reranker-v2-m3](https://huggingface.co/BAAI/bge-reranker-v2-m3) via `sentence-transformers` |
| Vector database | [Qdrant](https://qdrant.tech/) — self-hosted |
| Generation | [Groq](https://groq.com/) running Llama-family / GPT-OSS open-weight models |
| Backend | Python, FastAPI |
| Frontend | HTML/CSS/JS chat UI, `marked.js` for markdown rendering |
| Ingestion | `pandas`, `python-docx`, `pypdf`, `langchain-text-splitters` |
| Scheduling | APScheduler (hourly auto-ingestion + deletion cleanup) |
| Integrations | JIRA REST API, MCP (Model Context Protocol) |
| Infrastructure | Docker, Docker Compose |

---

## Getting Started

**Prerequisites:** Docker Desktop, a Groq API key, JIRA API access (optional, for JIRA ingestion).

```bash
# clone the repo
git clone https://github.com/nancybhardwaj89/QAVentra-Where-QA-Knowledge-Lives.git
cd QAVentra-Where-QA-Knowledge-Lives

# add your credentials
cp .env.example .env   # then fill in JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN, GROQ_API_KEY

# drop your data into the matching folders under data_sources/

# start everything (Qdrant + API + hourly ingestion scheduler)
docker compose up --build
```

Open **http://localhost:8000** and start asking questions.

**To stop:** `docker compose down`
**To run in the background:** `docker compose up -d --build`

---

## Project Structure

```
├── api/                  # FastAPI backend (hybrid search, rerank, generation)
├── ui/                   # Chat interface
├── ingestion/            # Per-source ingestion scripts + hourly scheduler
├── mcpserver/            # MCP server (query QAVentra from Claude/MCP clients)
├── data_sources/         # Drop your test cases, code, docs, etc. here
├── docker/               # Dockerfile + Qdrant storage volume
└── docker-compose.yml
```

---

## Continuous Ingestion

A background scheduler runs every hour and:
- Re-embeds any test case, code file, or document that changed
- Pulls JIRA tickets updated in the last hour
- **Detects and removes deleted content** — a removed test case, retired code file, or superseded doc gets cleaned out of the knowledge base automatically, not left as a stale orphan

---

## MCP Server — Use QAVentra from Claude

QAVentra also runs as an [MCP](https://modelcontextprotocol.io) server, so it can be queried directly from Claude Desktop (or any MCP-compatible client) as a native tool — no browser tab needed.

**Tools exposed:**
- `ask_qaventra(question, filter)` — the main tool; returns a cited answer plus source list, same as the web UI
- `qaventra_stats()` — returns how many artifacts are currently indexed

**Run it:**
```bash
python mcpserver/server.py
```
This starts the MCP server on port `8001`, using `streamable-http` transport at the `/mcp` path. It wraps the existing FastAPI backend rather than duplicating any retrieval logic — the same fixes and improvements that apply to the web UI apply here automatically.

**Add it as a connector in Claude Desktop:**
1. Go to Settings → Connectors → Add custom connector
2. Enter the server's HTTPS address (see note below) with `/mcp` appended
3. Choose "None" for authentication (no auth layer is set up by default)

> **Note:** Claude Desktop's connector setup requires an HTTPS address — a plain local `http://localhost` URL won't be accepted. For local testing, a tunnel like [ngrok](https://ngrok.com/) (`ngrok http 8001`) provides a temporary HTTPS URL. For team-wide, always-on access, this needs a real deployment with a stable domain and TLS certificate.

**Tested and confirmed working:** asked Claude Desktop *"Use the QAVentra connector to check if there's a bug related to login"* — it correctly called `ask_qaventra` and returned the exact cited ticket, matching the web UI's answer.

---



**Built and working:**
- ✅ Multi-source ingestion (test cases, code, JIRA, docs, meeting notes)
- ✅ Hybrid search + reranking + metadata-aware retrieval
- ✅ Cited, grounded chat interface
- ✅ Hourly auto-ingestion with deletion handling
- ✅ MCP server, tested end-to-end via Claude Desktop

**In progress:**
- 🔲 Retrieval/faithfulness evaluation with DeepEval

---

## License

This is a personal project built for learning and demonstration purposes.
