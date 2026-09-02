# Prompt: Build QAVentra — A Self-Hosted Hybrid RAG System for QA Teams

Copy the prompt below and give it to an AI coding assistant (Claude, ChatGPT, etc.) to build a system like QAVentra from scratch. It reflects the actual architecture decisions that were made and proven working — not just an initial idea.

---

## The Prompt

```
Act as a senior AI engineer. Design and build a self-hosted, multi-source
Hybrid RAG (Retrieval-Augmented Generation) system for a QA team.

GOAL
A QA engineer asks one question in plain English and gets back a single,
cited answer grounded in the team's actual QA knowledge — not general
internet knowledge. If the answer isn't in the knowledge base, the system
should say so rather than guess.

DATA SOURCES TO SUPPORT
1. Test automation framework code (e.g. Selenium/Java, Playwright/TypeScript
   repos)
2. Test case repository (CSV/XLSX, potentially thousands of rows)
3. JIRA tickets (via REST API + JQL query, including comments)
4. Company documents (PDF, Markdown, or Word docs — onboarding guides,
   policies, PRDs/SRS/BRD/FRD)
5. Meeting notes / transcripts (text or Word docs)

USE CASES TO SUPPORT
- Onboarding: new team members self-serve answers instead of asking around
- QA knowledge base / "one-stop" search across code + tickets + docs
- Test failure analysis and root cause analysis (RCA)
- Test design: finding coverage gaps, drafting new test cases
- Framework coding help and best-practices lookup

ARCHITECTURE DECISIONS TO USE (proven working)
- Embedding model: BAAI/bge-m3 (open source) — produces both dense and
  sparse vectors in one pass, enabling true hybrid search without a
  separate BM25 pipeline. Load via the FlagEmbedding library
  (BGEM3FlagModel) for genuine hybrid dense+sparse output.
- Reranker: BAAI/bge-reranker-v2-m3 (open source) — load via
  sentence-transformers' CrossEncoder class specifically (NOT
  FlagEmbedding's FlagReranker — it has a known compatibility bug with
  recent transformers library versions involving tokenizer.
  prepare_for_model).
- Vector database: Qdrant (open source) — supports native hybrid search
  (dense + sparse in one query via Reciprocal Rank Fusion) and rich
  payload/metadata filtering, which matters when mixing many source types
  in one collection. Run via Docker.
- Generation LLM: Groq (fast inference on open-weight models like
  Llama 3.3) — the only non-open-source-required piece; swap for a fully
  local model via Ollama if zero external calls is required.
- Backend: Python + FastAPI, exposing a POST /ask endpoint and a GET
  /stats endpoint (live point count in the vector DB).
- Frontend: a single self-contained HTML/CSS/JS chat page served directly
  by FastAPI — no separate frontend deployment needed for a small
  internal tool.
- Scheduler: APScheduler running an hourly sweep, wrapped as its own
  container in docker-compose.

CHUNKING STRATEGY (source-aware — do not use one strategy for everything)
- Code: split on function/class boundaries using a language-aware
  splitter (e.g. LangChain's RecursiveCharacterTextSplitter.from_language),
  ~500-800 tokens with 50-100 token overlap. Falls back to size-based
  splitting only for unusually long functions.
- Test case rows: 1 row = 1 chunk, never split mid-row. No overlap between
  rows (they're independent units). Concatenate all columns into one
  readable text block per chunk, and carry key columns as metadata
  (ID, module, priority, etc.) for filtering.
- JIRA tickets: 1 ticket = 1 chunk (summary + description + status +
  priority). Long comment threads become their own linked sub-chunks
  (~600 tokens each) rather than being crammed into the main chunk or
  dropped.
- PDFs/Word docs: heading/paragraph-aware chunking, 500-800 tokens,
  100-150 token overlap.
- Meeting notes/transcripts: slightly larger chunks than other docs
  (800-1000 tokens, 150-200 overlap) since they read better in longer
  continuous blocks.

METADATA & CITATIONS
Every chunk must carry a source_type field (test_case, code, jira_ticket,
jira_comment, document, meeting_notes) plus a source-specific identifier
(file path, test case ID, ticket ID). The generation prompt must instruct
the LLM to cite every claim with a bracketed number [1], [2] tied to the
specific retrieved chunk that supports it, and to say so plainly if the
provided context doesn't answer the question — never fill gaps from
general knowledge.

RETRIEVAL FLOW
1. Embed the user's question with BGE-M3 (dense + sparse)
2. Run hybrid search in Qdrant (RRF fusion of dense + sparse), retrieving
   ~25 candidates
3. Rerank all candidates against the actual question with the
   CrossEncoder reranker
4. Take the top 5-8 reranked chunks as context
5. Send that context to the LLM with a strict "only answer from this,
   cite everything" system prompt
6. Return the answer plus a structured sources list (index, label, score)

CONTINUOUS INGESTION (hourly)
Wrap each source's ingestion script into a callable run() function rather
than a top-to-bottom script. Track a small JSON state file of per-file
modification times. Each hourly sweep should only re-embed files that
actually changed since the last run (skip untouched ones), and for JIRA,
narrow the JQL to "updated >= -65m" instead of a full re-pull each time.
Run this as its own always-on container.

CONSTRAINTS
- Embedding model and vector database must be open source
- Self-hosted via Docker (Docker Compose: one service for the vector DB,
  one for the API+UI, one for the hourly scheduler)
- Token-efficient: retrieve only the relevant context per question, not
  the whole knowledge base

DELIVERABLE ORDER
1. Present the full architecture and reasoning first — justify the
   embedding model, vector DB, and chunk size/overlap choices — and wait
   for approval before writing code.
2. Build ingestion for one source at a time (test cases first — fastest
   to prove the pipeline end-to-end), confirming retrieval quality after
   each source before moving to the next.
3. Build the chatbot layer last, once all sources are ingested and
   individually verified.
4. Add the hourly auto-ingestion scheduler after the core system is
   confirmed working.
```

---

## Notes for Whoever Uses This Prompt

- Swap the specific data sources, tech names (e.g. "SCRUM" JIRA project key), and use cases in the prompt for your own team's actual sources before using it.
- The reranker library note (`CrossEncoder`, not `FlagReranker`) came from a real compatibility bug hit during QAVentra's build — worth keeping in the prompt even though it looks like a minor detail, since it saves real debugging time.
- Known open item not covered by this prompt: handling **deleted** source files (the described system detects new/changed files but not removals) — mention this explicitly if it matters for your use case.
