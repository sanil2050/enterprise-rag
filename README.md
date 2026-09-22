# Enterprise AI Knowledge & Decision Copilot

A production-oriented enterprise RAG platform for secure question answering over internal company knowledge.

The system combines:

- Hybrid semantic + keyword retrieval
- Reciprocal Rank Fusion (RRF)
- Cross-encoder reranking
- Query rewriting for conversational retrieval
- Agentic routing between Document RAG and GraphRAG
- Permission-aware retrieval using RBAC
- Citation and evidence validation
- Conversation memory
- PostgreSQL + pgvector
- Structured observability
- Security and evaluation test suites
- NVIDIA Nemotron generation through OpenRouter

The project is designed around an enterprise requirement:

> **Retrieve only information the current user is authorized to access, reason over the retrieved evidence, and return an answer with traceable citations.**

---

## Architecture

```mermaid
flowchart TB

    U[User / Frontend]

    U --> API[FastAPI API]

    API --> AUTH[JWT Authentication + RBAC]
    API --> CONV[Conversation Store]
    API --> AGENT[Agent Planner]

    AGENT --> DOC[Document RAG]
    AGENT --> GRAPH[GraphRAG]

    DOC --> SEM[Semantic Search]
    DOC --> KEY[Keyword Search]

    SEM --> RRF[RRF Fusion]
    KEY --> RRF

    RRF --> RERANK[Cross-Encoder Reranker]

    GRAPH --> GE[Graph Evidence Retrieval]

    RERANK --> EVID[Evidence + Citation Validation]
    GE --> EVID

    EVID --> GEN[Nemotron Generation<br/>via OpenRouter]

    GEN --> RESP[Answer + Citations]

    DB[(PostgreSQL + pgvector)]

    DB --> SEM
    DB --> KEY
    DB --> GE
    DB --> CONV

    OBS[Structured Observability]

    API --> OBS
    AGENT --> OBS
    EVID --> OBS
```

---

## 1. System Overview

The platform accepts a natural-language enterprise question and processes it through a controlled retrieval and generation pipeline.

A typical request flows through:

```text
User Question
      |
      v
JWT Authentication
      |
      v
RBAC / Permission Filtering
      |
      v
Conversation History
      |
      v
Query Rewriting
      |
      v
Agent Planner
      |
      +----------------------+
      |                      |
      v                      v
Document RAG              GraphRAG
      |                      |
      v                      v
Hybrid Retrieval         Graph Retrieval
      |                      |
      v                      |
RRF Fusion                  |
      |                      |
      v                      |
Cross-Encoder               |
Reranking                   |
      |                      |
      +----------+-----------+
                 |
                 v
        Evidence Layer
                 |
                 v
       Citation Validation
                 |
                 v
        Nemotron Generation
                 |
                 v
       Answer + Citations
```

---

## 2. Core RAG Pipeline

### Document Ingestion

Enterprise documents are processed through a document ingestion pipeline:

```text
PDF / DOCX
   |
   v
Document Extraction
   |
   v
Page-Aware Chunking
   |
   v
Embedding Generation
   |
   v
PostgreSQL + pgvector
```

The current knowledge base contains six primary enterprise documents:

- `company_policy.pdf`
- `employee_handbook.pdf`
- `leave_policy.pdf`
- `product_manual.pdf`
- `quarterly_report.pdf`
- `security_policy.pdf`

The current database contains approximately:

- 6 documents
- 2,352 document chunks
- 3,072-dimensional embeddings

---

## 3. Hybrid Retrieval

The document retrieval layer combines two complementary retrieval strategies.

### Semantic Retrieval

Uses vector similarity against Gemini embeddings stored in pgvector.

### Keyword Retrieval

Uses lexical matching for exact terms and enterprise-specific terminology.

### Reciprocal Rank Fusion

The two result sets are combined using Reciprocal Rank Fusion:

```text
Semantic Results
       +
Keyword Results
       |
       v
RRF Fusion
       |
       v
Candidate Documents
```

This provides a stronger retrieval signal than relying on semantic similarity alone.

---

## 4. Cross-Encoder Reranking

After hybrid retrieval, candidate chunks are reranked using:

`cross-encoder/ms-marco-MiniLM-L-6-v2`

The reranker evaluates the relationship between:

```text
User Query <-> Retrieved Chunk
```

and assigns a relevance score.

The highest-scoring chunks are passed to the generation layer as evidence.

---

## 5. Conversational Retrieval

The system supports multi-turn conversations.

For follow-up questions such as:

> **User:** How many vacation days do employees receive?  
> **User:** How much can I roll over?

the second question can be rewritten using conversation history into a self-contained retrieval query.

The system stores:

- Conversation
- User ownership
- User messages
- Assistant messages
- Timestamps

Conversation access is restricted to the owning user.

---

## 6. Agentic Retrieval

The system contains a bounded agent layer responsible for deciding which retrieval tools are required.

Current tools:

- **Document RAG**
- **GraphRAG**

The planner uses deterministic routing rules and can execute additional retrieval steps when the initial evidence is insufficient.

The agent is intentionally bounded:

```python
MAX_AGENT_STEPS = 3
```

This prevents uncontrolled tool execution.

**Example 1:**
```text
"What is the vacation policy?"
        |
        v
Document RAG
```

**Example 2 (Relationship-oriented questions):**
```text
"What benefits does 37signals provide?"
        |
        v
GraphRAG
```

The API records the tools executed and their retrieval metrics for observability.

---

## 7. GraphRAG

GraphRAG is implemented using PostgreSQL-backed entity and relationship tables.

The graph contains:

```text
Entities
   |
   +--> entity type
   |
   +--> normalized name

Relationships
   |
   +--> subject
   +--> predicate
   +--> object
   +--> source document
   +--> source chunk
```

The graph retrieval layer searches for relevant entities and relationships and returns source-backed graph evidence.

Graph retrieval is also permission-aware. Unauthorized document relationships are filtered before graph evidence is returned to the generation layer.

---

## 8. Enterprise Security

Security is treated as a retrieval-layer concern rather than only an API concern.

### Authentication

The API uses JWT-based authentication.

### Role-Based Access Control

Documents can be restricted by role. Current roles include:

- `employee`
- `finance`
- `hr`
- `security`
- `admin`

**Example:**
```text
employee
   |
   +--> company_policy.pdf
   +--> employee_handbook.pdf
   +--> leave_policy.pdf
   +--> product_manual.pdf

finance
   |
   +--> quarterly_report.pdf
```

The role is passed into retrieval so unauthorized documents are excluded before ranking and generation.

---

## 9. Prompt Injection Defense

The generation layer treats retrieved documents as evidence rather than instructions.

The system is explicitly designed to prevent retrieved content from overriding system behavior.

Security tests cover cases such as:

- Attempts to reveal system prompts
- Instructions embedded inside retrieved documents
- Attempts to bypass citation requirements
- Fabricated citation IDs
- Unauthorized document access
- Unauthorized conversation access
- Malicious role parameters

---

## 10. Citation and Evidence Validation

Document evidence receives deterministic citation identifiers:

- `S1`
- `S2`
- `S3`
- ...

The generation model is instructed to cite factual claims using these evidence IDs.

The citation validation layer then verifies that generated citation IDs correspond to retrieved evidence. Invalid citation IDs are discarded.

If relevant document evidence exists but the model produces no valid citations, the system falls back to a safe response rather than presenting the generated answer as properly supported.

Graph evidence uses separate graph identifiers such as:

- `G1`
- `G2`
- `G3`
- ...

---

## 11. Generation

Final answer generation uses:

**NVIDIA Nemotron 3 Ultra 550B A55B** through OpenRouter.

The generation layer receives:

- Current question
- Conversation history
- Document evidence
- Graph evidence

and is instructed to produce structured JSON containing:

```json
{
  "answer": "...",
  "citations": [
    {
      "citation_id": "S1",
      "document": "leave_policy.pdf",
      "page": 3,
      "chunk": 7
    }
  ]
}
```

The generation temperature is kept low to encourage deterministic evidence-grounded responses.

---

## 12. Observability

The API records structured request information including:

- Request ID
- User ID
- User role
- Conversation ID
- Original question
- Rewritten query
- Agent steps
- Executed tools
- Document result count
- Graph result count
- Citation count
- Query rewrite latency
- Generation latency
- Total request latency
- Request status

This provides a foundation for production monitoring and debugging.

---

## 13. Evaluation

The project contains separate retrieval and answer-quality evaluation suites.

### Retrieval Evaluation

The conversational retrieval benchmark currently contains five test cases.

**Baseline results:**

| Metric | Result |
| --- | --- |
| Recall@1 | 80% |
| Recall@3 | 100% |
| Recall@5 | 100% |
| MRR | 0.900 |

> *Note:* These results represent the current five-case benchmark and should not be interpreted as a general accuracy estimate for the complete system.

### Answer Evaluation

The current five-case golden-answer benchmark measures:

- Fact coverage
- Citation accuracy
- Citation completeness

**Current baseline:**

| Metric | Result |
| --- | --- |
| Fact coverage | 70% |
| Citation accuracy | 86.67% |
| Citation completeness | 100% |

The answer benchmark currently uses deterministic fact matching and expected-source matching, so it is intended as an engineering baseline rather than a comprehensive semantic evaluation.

---

## 14. Security Test Suite

The project contains automated security tests covering:

```text
tests/
└── security/
    ├── test_citation_security.py
    ├── test_input_validation.py
    └── test_rbac.py
```

**Current result:**
```text
9 passed
```

The tests cover:

- Citation validation
- Invalid citation rejection
- Uncited evidence fallback
- Role-aware retrieval
- SQL parameterization
- Input length limits
- Required question validation
- Extra-field rejection

Run the security suite with:

```bash
python -m pytest tests/security -q
```

---

## 15. Project Structure

```text
enterprise-rag/
│
├── app/
│   ├── api/
│   │   ├── auth.py
│   │   ├── chat.py
│   │   └── conversations.py
│   │
│   ├── agent/
│   │   ├── planner.py
│   │   ├── service.py
│   │   └── tools.py
│   │
│   ├── config/
│   │   └── settings.py
│   │
│   ├── database/
│   │   └── database.py
│   │
│   ├── generation/
│   │   └── gemini_generator.py
│   │
│   ├── graph/
│   │   ├── extractor.py
│   │   ├── retriever.py
│   │   └── ...
│   │
│   ├── ingestion/
│   │   ├── embedder.py
│   │   ├── pdf_loader.py
│   │   ├── page_chunker.py
│   │   └── chunker.py
│   │
│   ├── models/
│   │   └── ...
│   │
│   ├── observability/
│   │   └── ...
│   │
│   └── retrieval/
│       ├── access_control.py
│       ├── hybrid_search.py
│       ├── keyword_search.py
│       ├── reranker.py
│       └── vector_search.py
│
├── data/
│   ├── raw/
│   └── processed/
│
├── scripts/
│   ├── init_db.py
│   ├── setup_users.py
│   ├── setup_permissions.py
│   ├── ingest_documents.py
│   ├── setup_graph.py
│   └── evaluation scripts
│
├── tests/
│   ├── security/
│   └── evaluation/
│
├── docker-compose.yml
├── pytest.ini
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

## 16. Technology Stack

| Layer | Technology |
| --- | --- |
| API | FastAPI |
| Server | Uvicorn |
| Language | Python |
| Database | PostgreSQL |
| Vector Search | pgvector |
| ORM / DB Access | SQLAlchemy |
| Embeddings | Gemini Embedding |
| Hybrid Retrieval | Semantic + Keyword + RRF |
| Reranking | Sentence Transformers Cross-Encoder |
| Generation | NVIDIA Nemotron |
| Model Gateway | OpenRouter |
| Authentication | JWT |
| Password Hashing | Argon2 |
| Graph Storage | PostgreSQL |
| Testing | Pytest |
| Containerization | Docker / Docker Compose |

---

## 17. Local Setup

### 1. Clone the repository

```bash
git clone <repository-url>
cd enterprise-rag
```

### 2. Create a virtual environment

**Windows:**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

**Linux/macOS:**
```bash
python -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create `.env` from `.env.example`.

Required configuration includes:

```env
GEMINI_API_KEY=
GEMINI_API_KEY_2=
GEMINI_API_KEY_3=
GEMINI_API_KEY_4=
GEMINI_API_KEY_5=

OPENROUTER_API_KEY=

DATABASE_URL=postgresql+psycopg://rag_user:rag_password@localhost:5432/enterprise_rag

JWT_SECRET_KEY=
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
```

> [!WARNING]
> Never commit `.env`.

---

## 18. Start PostgreSQL

The project uses PostgreSQL with pgvector:

```bash
docker compose up -d
```

Initialize the database:

```bash
python scripts/init_db.py
```

Set up authentication tables:

```bash
python scripts/setup_users.py
```

Set up document permissions:

```bash
python scripts/setup_permissions.py
```

---

## 19. Start the API

```bash
uvicorn app.main:app --reload
```

The API is available locally through the FastAPI server.

- **Health check:** `GET /health`
- **Interactive API docs:** Available through FastAPI's generated Swagger/OpenAPI interface at `/docs`.

---

## 20. Evaluation Commands

**Conversational retrieval evaluation:**
```bash
python -m scripts.evaluate_conversational_retrieval
```

**Answer-quality evaluation:**
```bash
python -m scripts.evaluate_answers
```

**Security tests:**
```bash
python -m pytest tests/security -q
```

---

## 21. Design Principles

The project follows several production-oriented principles:

- **Security before generation:** Authorization happens during retrieval rather than relying on the language model to ignore unauthorized evidence.
- **Evidence before answers:** The model receives retrieved evidence and is required to ground factual responses in that evidence.
- **Bounded agent execution:** Agentic behavior is explicitly limited to a small number of tool calls (`MAX_AGENT_STEPS = 3`).
- **Observable decisions:** Retrieval, agent execution, citations, and latency are logged.
- **Deterministic validation:** Important security boundaries such as citation IDs, permissions, and API input validation are enforced programmatically.
- **Evaluation-driven development:** Retrieval and answer-quality benchmarks are maintained separately from application code.

---

## 22. Current Status

**Implemented:**

- [x] Enterprise document ingestion
- [x] Page-aware chunking
- [x] Gemini embeddings
- [x] PostgreSQL + pgvector
- [x] Semantic retrieval
- [x] Keyword retrieval
- [x] RRF hybrid retrieval
- [x] Cross-encoder reranking
- [x] Conversational query rewriting
- [x] Conversation persistence
- [x] JWT authentication
- [x] RBAC-aware retrieval
- [x] GraphRAG
- [x] Agentic routing
- [x] Citation validation
- [x] Prompt-injection defenses
- [x] Structured observability
- [x] Security test suite
- [x] Retrieval evaluation
- [x] Answer evaluation

**Planned:**

- [ ] Production Docker image for the API
- [ ] Enterprise chat frontend
- [ ] Streaming responses
- [ ] Production deployment
- [ ] Expanded evaluation dataset
- [ ] More advanced multimodal document support

---

## 23. Project Goal

This project is intended to demonstrate how an enterprise RAG system can move beyond a basic:

```text
PDF -> Embeddings -> Vector Search -> LLM
```

pipeline toward a more production-oriented architecture:

```text
Authentication
      +
Authorization
      +
Hybrid Retrieval
      +
Reranking
      +
Agentic Routing
      +
GraphRAG
      +
Evidence Validation
      +
Conversation Memory
      +
Observability
      +
Evaluation
```

The emphasis is on building a system that is not only capable of answering questions, but also considers security, traceability, evaluation, and operational behavior.
