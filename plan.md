# QAVentra
### Where QA Knowledge Lives.

---

## What is QAVentra?

Imagine every QA engineer on the team had one place to ask any question about the product — and got back a straight, trustworthy answer with proof of where it came from. That's QAVentra.

Instead of separately digging through test case spreadsheets, JIRA tickets, PRDs, code repositories, and meeting notes, a QA engineer just **asks a question in plain English** — like *"What test cases cover new patient registration?"* or *"Is there an automated test for the login timeout bug?"* — and QAVentra searches across all of that at once, then answers with **citations**, so you can always verify exactly where the information came from.

It's not a generic chatbot. It only answers using your team's actual QA knowledge — test cases, code, tickets, and documents — not general internet knowledge. If the answer isn't in there, it says so, instead of guessing.

---

## The Problem It Solves

New QA engineers spend weeks figuring out where everything lives. Even experienced engineers waste time jumping between five different tools to answer one question. QAVentra collapses all of that into a single search box.

| Without QAVentra | With QAVentra |
|---|---|
| Search JIRA, then the test case sheet, then the code repo, then ask a teammate | Ask one question, get one answer |
| No way to know if you found *everything* relevant | Answer is grounded across all sources at once |
| Knowledge lives in people's heads | Knowledge lives in one searchable system |
| New hires take weeks to get oriented | New hires can self-serve from day one |

---

## What It Actually Does (in plain terms)

1. **It reads everything.** Test case spreadsheets, Selenium and Playwright test automation code, JIRA tickets, PRDs, company docs, and meeting notes all get fed in.
2. **It breaks that into small, meaningful pieces** — a test case stays whole, a JIRA ticket stays whole, a chunk of code stays whole — so nothing gets awkwardly cut in half.
3. **It "understands" each piece** by converting it into a mathematical representation (an embedding) that captures its meaning, not just its exact wording.
4. **It stores all of that in a searchable database**, tagged with where it came from.
5. **When you ask a question**, it finds the most relevant pieces — using both meaning-based search and exact keyword matching together (this combination is called "hybrid search") — then double-checks which ones are actually most relevant (this second pass is called "reranking").
6. **It hands the best matches to an AI model**, which writes a clear answer and cites exactly which piece of evidence backed each part of it.
7. **It keeps itself up to date automatically** — checking every hour for new or changed test cases, code, documents, and JIRA tickets, so the knowledge base never goes stale.

---

## Chunking Strategy (How Content Gets Broken Up)

Different types of content need to be split differently, so nothing important gets cut in half or lost. QAVentra uses a different approach for each source type:

| Source | How it's split | Chunk size | Overlap |
|---|---|---|---|
| Test cases | Never split — one whole test case = one piece | Whole row | None |
| JIRA tickets | Never split the ticket itself; long comment threads become their own linked pieces | Whole ticket / ~600 tokens per comment piece | 100 tokens (comments only) |
| Selenium/Playwright code | Split at function/class boundaries, not random line counts | ~500–800 tokens | 50–100 tokens |
| PRDs / company docs | Split by heading and paragraph | ~500–800 tokens | 100–150 tokens |
| Meeting notes | Split by paragraph, in slightly longer blocks (reads better as continuous text) | ~800–1,000 tokens | 150–200 tokens |

**Why this matters:** a test case only makes sense as a whole — the steps are meaningless without knowing the expected result. Splitting it in half would return a fragment instead of a usable answer. Code is split at natural boundaries (a whole function) so it stays readable and cite-able, instead of being cut off mid-line. Documents and meeting notes use "overlap" — a bit of repeated text between consecutive pieces — so an idea that spans a paragraph break doesn't get lost between two separate pieces.

---



Everything below is open source or freely available, self-hosted, and runs without depending on any single company's proprietary infrastructure.

### Core AI Components
| Component | What it is | Why it's used |
|---|---|---|
| **BAAI/bge-m3** | Open-source embedding model | Converts text into a searchable numeric representation — supports both meaning-based and keyword-based search in one model |
| **BAAI/bge-reranker-v2-m3** | Open-source reranking model | Double-checks and re-scores search results for true relevance before they reach the AI |
| **Qdrant** | Open-source vector database | Stores and searches all the embedded knowledge efficiently, with hybrid (meaning + keyword) search built in |
| **Groq (Llama 3.3)** | AI answer-generation | Writes the final answer, strictly grounded in retrieved evidence with citations |

### Application Layer
| Component | What it is | Why it's used |
|---|---|---|
| **Python / FastAPI** | Backend server | Handles the "ask a question" logic: search → rerank → generate answer |
| **HTML / CSS / JavaScript** | Chat interface | The actual screen QA engineers type questions into |
| **APScheduler** | Task scheduler | Runs the hourly auto-update check in the background |

### Data Ingestion
| Component | What it is | Why it's used |
|---|---|---|
| **pandas** | Spreadsheet reader | Reads the test case CSV |
| **python-docx / pypdf** | Document readers | Reads Word docs and PDFs (PRDs, policies, meeting notes) |
| **langchain-text-splitters** | Smart text chunker | Splits code by function/class, and documents by heading/paragraph, instead of cutting text at arbitrary points |
| **JIRA REST API** | Ticket data source | Pulls tickets and comments directly from JIRA Cloud |

### Infrastructure
| Component | What it is | Why it's used |
|---|---|---|
| **Docker & Docker Compose** | Containerization | Packages the whole system (database, backend, scheduler) so it runs identically anywhere |
| **DigitalOcean droplet** *(planned, v2)* | Cloud hosting | Where the system will run 24/7 so the whole team can access it, not just one laptop |

---

## How the Pieces Fit Together

```
Your QA Knowledge                     What QAVentra Does With It
─────────────────                     ───────────────────────────
Test Cases (CSV)      ─┐
Selenium/Playwright     │
  Code                  │
JIRA Tickets            ├──▶  Read → Understand → Store  ──▶  [ Searchable Knowledge Base ]
PRDs / Docs             │                                              │
Meeting Notes          ─┘                                              │
                                                                        ▼
                                                          "What test cases cover X?"
                                                                        │
                                                                        ▼
                                                    Search (meaning + keyword) → Double-check
                                                    relevance → AI writes cited answer
                                                                        │
                                                                        ▼
                                                         Answer + Sources, in the chat UI
```

---

## How to Run It

Everything runs through Docker, so there's nothing to install or configure by hand beyond the initial setup.

**One-time setup (already done, listed for reference):**
- Docker Desktop installed and running
- A `.env` file in the project root with your JIRA, Groq, and Qdrant credentials

**To start QAVentra:**
1. Open a terminal in the project folder (`QAVentra-TheQAKnowledgeIntelligencePlatform`)
2. Make sure Docker Desktop is running
3. Run:
   ```bash
   docker compose up --build
   ```
   This starts all three services together: the vector database (Qdrant), the chatbot backend, and the hourly auto-ingestion scheduler.
4. Once you see `Uvicorn running on http://0.0.0.0:8000` in the terminal, open a browser and go to:
   ```
   http://localhost:8000
   ```
5. Ask a question — that's it.

**To stop it:** press `Ctrl+C` in the terminal, or run `docker compose down` from the project folder.

**To run it in the background** (so it keeps working without a terminal window open):
```bash
docker compose up -d --build
```

**To check it's healthy anytime:**
```bash
docker ps
```
You should see three containers running: `qaventra-qdrant`, `qaventra-app`, and `qaventra-scheduler`.

## Continuous Ingestion (Stays Up to Date Automatically)

QAVentra doesn't go stale. A background process checks every hour for anything new or changed across all your sources, and automatically re-indexes just that — no manual re-running of scripts needed.

**What it checks each hour:**
- **Test cases** — if the CSV file was modified, it re-processes it
- **Code (Selenium/Playwright)** — only files that actually changed since the last check get re-indexed; untouched files are skipped
- **Documents** (PRDs, company docs, meeting notes) — same per-file change check
- **JIRA** — pulls only tickets updated in the last hour, instead of re-fetching everything

This runs as its own always-on container (`qaventra-scheduler`) alongside the database and chatbot — it starts automatically the moment you run `docker compose up`, does an initial sweep right away, and then repeats every hour on its own. You don't need to trigger it manually.

**Known limitation (v2 item):** it currently only picks up new and modified files — if a test case or file is *deleted* from a source folder, its old entry stays in the knowledge base until that's addressed in v2.

---

## Current Status

**✅ Built and working:**
- All data sources ingested (test cases, Selenium/Playwright code, JIRA tickets, PRDs/docs, meeting notes)
- Hybrid search with reranking and cited answers
- Full chat interface with search scope filters (JIRA / Playwright / PRDs / All) and live knowledge base stats
- Hourly automatic re-ingestion of new/changed content

**📋 Planned for v2:**
- Handling deleted source files (currently, deleting a test case or file doesn't remove its old entry from the knowledge base)
- Deployment to a live, always-on cloud server with a shareable link

