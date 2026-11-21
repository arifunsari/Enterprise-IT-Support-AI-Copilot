# Enterprise-IT-Support-AI-Copilot


An end-to-end **Forward Deployed Engineer (FDE) project** that turns a notebook-style Agentic RAG workflow into a deployable internal product using **LangGraph, FastAPI, Pinecone, OpenAI, Tavily, HTML, CSS, and JavaScript**.

---

## 1. Business Problem

### Customer
**NovaRetail**, a fictional 3,000-employee retail company.

### Problem
The internal IT team maintains many documents: VPN instructions, password rules, MFA policy, software installation rules, laptop troubleshooting guides, and service-desk runbooks.

Employees still create repetitive support tickets because:

- They do not know where the correct document is.
- Traditional keyword search returns too many results.
- A normal chatbot may hallucinate an answer.
- Internal documents can be incomplete or outdated.
- Some questions require current vendor information from the public web.

### Example
An employee asks:

> **“How do I connect to the company VPN from home?”**

The answer exists in the private company KB, so the system should **not search the public internet**.

Another employee asks:

> **“What is the latest Microsoft Teams outage guidance?”**

The internal KB may not contain current outage information. The system should recognize weak private evidence, use an external search, grade that evidence, and answer with an external-source warning.

### Business Goal
Build a secure IT Support Copilot that:

1. Searches trusted private knowledge first.
2. Checks whether retrieved evidence is good enough.
3. Uses web search only when private knowledge is insufficient.
4. Rewrites weak queries and retries.
5. Generates grounded answers.
6. Shows the decision path for transparency and debugging.
7. Lets authorized staff add new company documents.

---

## 2. Why This Is an FDE Project

A Forward Deployed Engineer does more than create an LLM notebook. The FDE must turn the customer's problem into a usable product.

```text
Customer Problem
      ↓
Discovery & Requirements
      ↓
Solution Architecture
      ↓
Data / Knowledge Integration
      ↓
Agentic RAG Development
      ↓
API Development
      ↓
User Interface
      ↓
Security + Audit + Testing
      ↓
Deployment
      ↓
Observe + Improve
```

This repository demonstrates each layer.

---

## 3. Simple Architecture

```text
                   ┌─────────────────────┐
                   │   Employee / User   │
                   └──────────┬──────────┘
                              │
                              ▼
                   ┌─────────────────────┐
                   │ HTML/CSS/JavaScript │
                   │      Web UI         │
                   └──────────┬──────────┘
                              │ POST /api/chat
                              ▼
                   ┌─────────────────────┐
                   │       FastAPI       │
                   └──────────┬──────────┘
                              │
                              ▼
                   ┌─────────────────────┐
                   │     LangGraph       │
                   │ Agentic RAG Control │
                   └──────────┬──────────┘
                              │
               ┌──────────────┴──────────────┐
               │                             │
               ▼                             ▼
       ┌───────────────┐              ┌──────────────┐
       │ Private KB    │              │ Tavily Web   │
       │ Pinecone      │              │ Search       │
       └───────┬───────┘              └──────┬───────┘
               │                             │
               └──────────────┬──────────────┘
                              ▼
                     ┌────────────────┐
                     │ OpenAI LLM       │
                     │ Grounded Answer│
                     └────────────────┘
```

---

## 4. Agentic RAG Workflow

This follows the same core implementation pattern as the reference notebook.

```text
Question
   ↓
[1] Route Question
   ├── Greeting / simple chat ─────────────→ Direct Answer
   │
   └── IT support question
                ↓
[2] Retrieve from Private Pinecone KB
                ↓
[3] Grade Private Evidence
       ┌────────┴────────┐
       │                 │
     GOOD               WEAK
       │                 │
       ▼                 ▼
Generate from KB    [4] Tavily Web Search
                         ↓
                  [5] Grade Web Evidence
                    ┌────┴─────┐
                    │          │
                  GOOD        WEAK
                    │          │
                    ▼          ▼
              Generate Web  [6] Rewrite Query
                               ↓
                         Retry Private KB
                               ↓
                        Max retry reached?
                               ↓
                    Insufficient Evidence
```

### Why Agentic?

Normal RAG does approximately this:

```text
Question → Retrieve → Generate
```

This project makes decisions:

```text
Question
 → Route
 → Retrieve
 → Evaluate evidence
 → Choose KB or Web
 → Rewrite if needed
 → Retry
 → Generate grounded answer
```

The system therefore controls **what to do next** based on its current state.

---

## 5. Main Technology Stack

| Layer | Technology | Purpose |
|---|---|---|
| Agent workflow | LangGraph | Stateful routing and conditional decisions |
| Retrieval | Pinecone + SQLite FTS5 | Dense and keyword candidates, fused and lexically reranked |
| Tracing | Langfuse (optional) | LangGraph callback traces when explicitly enabled |
| LLM and embeddings | OpenAI via LangChain integrations | Routing, grading, rewriting, answer generation, and vector embeddings |
| Vector DB | Pinecone | Private enterprise knowledge base |
| External search | Tavily | Fallback when company KB is insufficient |
| API | FastAPI | Backend and REST endpoints |
| Frontend | HTML/CSS/JavaScript | Employee-facing interface |
| Audit | SQLite | Basic decision-path logging |
| Packaging | Docker | Reproducible deployment |

---

## 6. Project Structure

```text
Enterprise-IT-Support-AI-Copilot/
│
├── app/
│   ├── api/
│   │   └── routes.py              # Chat, SSE, health and ingestion APIs
│   │
│   ├── core/
│   │   ├── config.py              # Environment configuration
│   │   └── logging.py             # Logging configuration
│   │
│   ├── rag/
│   │   ├── retrieval.py           # SQLite FTS5, fusion and lexical reranking
│   │   ├── state.py               # LangGraph state + structured decisions
│   │   ├── vectorstore.py         # Pinecone + embeddings
│   │   └── workflow.py            # Complete Agentic RAG graph
│   │
│   ├── evaluation.py              # Expected-source/term evaluation CLI
│   ├── services/
│   │   ├── audit.py               # SQLite query audit
│   │   └── ingestion.py           # PDF/TXT/MD/DOCX loading + chunking
│   │
│   └── main.py                    # FastAPI application
│
├── data/
│   ├── evaluations/
│   │   └── stage2.jsonl
│   └── sample_kb/
│       ├── company_it_handbook.md
│       └── service_desk_runbook.md
│
├── static/
│   ├── css/style.css
│   └── js/app.js
│
├── templates/
│   └── index.html
│
├── tests/
|   |-- test_ingestion.py
|   |-- test_security.py
|   `-- test_vectorstore.py
│
├── uploads/
├── Dockerfile
├── ingest_sample_kb.py
├── build_local_search_index.py
├── requirements.txt
├── run.py
└── README.md
```

---

## 7. Setup

### Step 1 — Create virtual environment

```bash
python -m venv venv
```

Windows:

```bash
venv\Scripts\activate
```

macOS/Linux:

```bash
source venv/bin/activate
```

### Step 2 — Install dependencies

```bash
pip install -r requirements.txt
```

### Step 3 — Configure environment

Create a `.env` file in the project root directory with the following variables:

```env
# LLM API Key
OPENAI_API_KEY=your_openai_api_key_here

# External Search
TAVILY_API_KEY=your_tavily_api_key_here

# Vector Database (Pinecone)
PINECONE_API_KEY=your_pinecone_api_key_here
PINECONE_INDEX_NAME=industry-agentic-rag-kb-v2
PINECONE_NAMESPACE=langgraph-agentic-rag

# Models
OPENAI_MODEL=gpt-4o-mini
EMBEDDING_MODEL=text-embedding-3-small

# Security
ADMIN_API_KEY=

# Upload limit in bytes (default 10 MiB)
MAX_UPLOAD_SIZE_BYTES=10485760

# Retrieval (SQLite FTS5 keyword + Pinecone dense fusion)
HYBRID_RETRIEVAL_ENABLED=true
RETRIEVAL_CANDIDATE_K=12

# Optional Langfuse tracing (opt in; prompts and retrieved text are traced)
LANGFUSE_ENABLED=false
LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=
LANGFUSE_BASE_URL=

# Application Settings
APP_ENV=development
```

#### Environment Variable Reference

| Variable | Description | Example | Required |
|---|---|---|---|
| `OPENAI_API_KEY` | API key for chat and embeddings | `sk-...` | Needed for chat and retrieval |
| `TAVILY_API_KEY` | API key for external web search fallback | `tvly-...` | Needed only for web fallback |
| `PINECONE_API_KEY` | API key for Pinecone private knowledge retrieval | `pckey-...` | Needed for retrieval |
| `PINECONE_INDEX_NAME` | Pinecone index name | `industry-agentic-rag-kb-v2` | Optional (default: `industry-agentic-rag-kb-v2`) |
| `PINECONE_NAMESPACE` | Pinecone namespace for document isolation | `langgraph-agentic-rag` | Optional (default: `langgraph-agentic-rag`) |
| `OPENAI_MODEL` | OpenAI model identifier | `gpt-4o-mini` | ⚠️ Optional (default: `gpt-4o-mini`) |
| `EMBEDDING_MODEL` | Embedding model for vectorization | `text-embedding-3-small` | ⚠️ Optional (default: `text-embedding-3-small`) |
| `ADMIN_API_KEY` | Secret key for document ingestion | Long random secret | Required to enable ingestion; required (32+ characters) in production |
| `APP_ENV` | Application environment | `development` or `production` | Optional (default: `development`) |
| `MAX_UPLOAD_SIZE_BYTES` | Maximum uploaded document size | `10485760` | Optional (default: 10 MiB) |
| `TOP_K` | Number of private KB chunks retrieved | `4` | Optional (default: `4`) |
| `MAX_RETRIES` | Maximum web fallback rewrite retries | `1` | Optional (default: `1`) |
| `AUDIT_DB_PATH` | SQLite audit and ingestion metadata database | `data/audit.db` | Optional (default: project `data/audit.db`) |
| `UPLOAD_DIR` | Local storage directory for uploaded files | `uploads` | Optional (default: project `uploads`) |
| `SAMPLE_KB_DIR` | Folder used by the sample ingestion script | `data/sample_kb` | Optional (default: project `data/sample_kb`) |
| `HYBRID_RETRIEVAL_ENABLED` | Enable dense + SQLite FTS5 retrieval and fusion | `true` | Optional (default: `true`) |
| `RETRIEVAL_CANDIDATE_K` | Dense/keyword candidates considered before reranking | `12` | Optional (must be at least `TOP_K`) |
| `LANGFUSE_ENABLED` | Enable optional LangGraph tracing | `false` | Optional (default: disabled) |
| `LANGFUSE_PUBLIC_KEY` | Langfuse project public key | Secret-managed value | Required only when tracing is enabled |
| `LANGFUSE_SECRET_KEY` | Langfuse project secret key | Secret-managed value | Required only when tracing is enabled |
| `LANGFUSE_BASE_URL` | Langfuse endpoint/region URL | `https://cloud.langfuse.com` | Optional; use your self-hosted or regional URL as needed |

**⚠️ Important Security Notes:**

- Never commit `.env` to version control. Add it to `.gitignore`.
- In development, the app and chat can start without `ADMIN_API_KEY`, but `/api/ingest` returns `503` until a key is configured.
- In production (`APP_ENV=production`), startup fails unless `ADMIN_API_KEY` has at least 32 characters. Use a secret manager or environment variable.
- Use environment variables instead of hardcoding secrets.
- Restrict API key access to only the services that need them.

### Step 4 — Load sample company knowledge

```bash
python ingest_sample_kb.py
```

This demonstrates the RAG ingestion pipeline:

```text
Company Documents
   ↓
Load Documents
   ↓
Chunk Text
   ↓
OpenAI Embeddings
   ↓
Pinecone Vector Database
```

### Step 5 — Run the application

On Windows, from the project root:

```bash
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe run.py
```

Create and configure the project-root `.env` file before asking questions. The app uses
`OPENAI_API_KEY` for chat and embeddings, `PINECONE_API_KEY` for private knowledge
retrieval, and `TAVILY_API_KEY` when it needs external search. The home page and health
check can run without those service calls. Hybrid retrieval uses a local SQLite FTS5 index alongside Pinecone; newly ingested chunks populate it automatically. Re-uploading an already completed document backfills the local index without re-embedding it.

Open the app and check the health endpoint:

```text
http://127.0.0.1:8000
http://127.0.0.1:8000/api/health
```

FastAPI API docs:

```text
http://127.0.0.1:8000/docs
```

If port 8000 is already in use, stop the other server with `Ctrl+C`, or choose another
port in PowerShell before starting the app:

```powershell
$env:PORT = "8001"
.\.venv\Scripts\python.exe run.py
```

Then use `http://127.0.0.1:8001`. Stop the server with `Ctrl+C`.

---

## 8. Classroom Demo Scenarios

### Demo A — Private KB Success

Ask:

> **How do I connect to the company VPN from home?**

Expected path:

```text
Router → KB
Private KB Retrieval
KB Grade → GOOD
Generate from Private KB
```

Teaching point:

> Trusted internal company knowledge is preferred. No public web call is necessary.

---

### Demo B — Company Policy Question

Ask:

> **Can IT support ask me to share my MFA code?**

The internal handbook says employees must never share passwords or MFA codes with support personnel.

Expected path:

```text
Router → KB
Private KB Retrieval
KB Grade → GOOD
Private KB Answer
```

Teaching point:

> RAG allows the model to answer using company-specific information it was never trained on.

---

### Demo C — External / Current Information

Ask:

> **What is the latest Microsoft Teams outage guidance?**

Expected path when internal documents do not answer it:

```text
Router → KB
Private KB Retrieval
KB Grade → WEAK
Tavily Search
Web Grade → GOOD
Web Answer
```

Teaching point:

> Agentic RAG can choose another information source rather than blindly answering from irrelevant vectors.

---

### Demo D — Query Rewrite

Ask a deliberately vague question such as:

> **My work communication app is acting strange after the new update. What should I do?**

If both KB and first external retrieval are weak, the workflow can rewrite the query and retry.

Teaching point:

> Retrieval failure does not immediately mean failure. An agent can improve the search query and try again while using a retry guard to avoid loops.

---

### Demo E — Direct Conversation

Ask:

> **Hello!**

Expected path:

```text
Router → DIRECT
Direct Answer
```

Teaching point:

> Not every message should trigger expensive vector search or web search.

---

## 9. Document Upload Demo

The sidebar contains **Add Company Document**.

Set `ADMIN_API_KEY` in the project-root `.env` before uploading; local development without it leaves ingestion disabled.

Upload one of:

- `.pdf`
- `.txt`
- `.md`
- `.docx`

The backend performs:

```text
Upload
  ↓
Validate Type
  ↓
Load Text
  ↓
Recursive Chunking
  ↓
Embeddings
  ↓
Pinecone Indexing
  ↓
Immediately Available for Retrieval
```

This is useful in an FDE demonstration because the customer does not want to edit Python every time a new policy is published.

---

## 10. API Endpoints

### `GET /api/health`

Health check.

### `POST /api/chat`

Request:

```json
{
  "question": "How do I reset my company password?"
}
```

Response contains:

```json
{
  "answer": "...",
  "source_used": "private_kb",
  "trace": [
    "Router → KB",
    "Private KB retrieval → 4 chunks",
    "KB evidence grade → GOOD",
    "Answer generation → PRIVATE KB"
  ],
  "citations": []
}
```

### `POST /api/chat/stream`

Uses the same JSON request as `/api/chat` and returns Server-Sent Events (`text/event-stream`). Events contain answer `token` values followed by a `complete` event with the source, citations, trace, and rewritten query. The existing JSON `/api/chat` contract remains available.

### `POST /api/ingest`

Protected by the `X-Admin-Key` request header.

Uploads a document and adds its chunks to Pinecone. The API accepts PDF, TXT, MD, and DOCX files up to `MAX_UPLOAD_SIZE_BYTES` (10 MiB by default). It returns a stable `document_id` and ingestion `status`; identical content is reported as a duplicate, while changed content is ingested as a separate document. Files are stored under generated names, not the client-provided path.

---



### Tests

Run the unit suite without live OpenAI, Pinecone, or Tavily credentials:

```bash
python -m unittest discover -s tests -v
```

The prompt-injection test checks that retrieved text is explicitly framed as untrusted evidence in the model prompt. It does not prove that a language model will always resist every injection; the test uses a mocked model and makes no such guarantee.


### Evaluation harness

`data/evaluations/stage2.jsonl` contains small expected-source and expected-term examples based on the sample KB. Run the harness after configuring the OpenAI and Pinecone credentials and loading the sample KB:

```bash
python -m app.evaluation
python -m app.evaluation --output artifacts/evaluations/run.json
```

If your Pinecone index already contains the sample vectors from before Stage 2, run `python build_local_search_index.py` to build the local lexical index from sample/upload files without embedding or changing Pinecone vectors. The runner makes live workflow calls and can incur provider usage; it is not a fully offline or model-judged evaluation. It reports expected-source accuracy, answer expected-term recall, citation rate, and latency. The small fixture is a smoke/regression set, not a statistically representative benchmark.

Langfuse tracing is optional and disabled by default. When enabled, traces can include prompts and retrieved document text; configure project keys and a data-residency appropriate base URL only if that data flow is approved for your environment.
