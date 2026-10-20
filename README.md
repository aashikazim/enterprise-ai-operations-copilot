# Enterprise AI Operations Copilot

**A multi-tenant, production-oriented AI backend for enterprise
knowledge retrieval, grounded question answering, and asynchronous
quality evaluation.**

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-API-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-pgvector-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
![Status](https://img.shields.io/badge/Status-Active%20Development-orange)

> **Development milestone: Day 10 of a 30-day build.** This repository
> is an evolving engineering portfolio project, not a
> production-deployed service. The features below describe the
> implementation through Day 10; future integrations are listed
> separately.

## Overview

Enterprise teams need answers from internal knowledge sources, but a
useful AI assistant must do more than generate plausible text. It must
retrieve relevant evidence, respect tenant boundaries, identify
unsupported claims, and remain reliable when evaluation workloads fail
or take time.

**Enterprise AI Operations Copilot** explores these requirements through
a FastAPI backend combining PostgreSQL, hybrid retrieval,
evidence-grounded generation, claim-level faithfulness evaluation, and a
durable database-backed worker queue.

The project is designed to demonstrate practical skills relevant to
**Forward Deployed Engineering (FDE)**, **backend/infrastructure
engineering**, and **applied AI engineering**: connecting customer needs
to working APIs, building reliable data workflows, enforcing isolation,
and evaluating AI quality with measurable signals.

## Architecture

``` mermaid
flowchart TD
    Client[API Client] --> API[FastAPI]
    API --> Auth[JWT Authentication / Tenant RBAC]
    Auth --> Knowledge[Knowledge Ingestion]
    Auth --> RAG[RAG Question Answering]
    Knowledge --> Chunk[Chunking + Embeddings]
    Chunk --> DB[(PostgreSQL + pgvector)]
    RAG --> Dense[Dense Vector Retrieval]
    RAG --> Sparse[BM25 Retrieval]
    Dense --> DB
    Sparse --> DB
    Dense --> Fusion[Reciprocal Rank Fusion]
    Sparse --> Fusion
    Fusion --> Rerank[Cross-Encoder Reranking]
    Rerank --> LLM[OpenAI Responses API]
    LLM --> Validate[Citation Validation + Abstention]
    Validate --> Client
    EvalSubmit[Explicit Evaluation Submission / Demo Script] --> Queue[(PostgreSQL Evaluation Jobs)]
    Queue --> Worker[Separate Evaluation Worker]
    Worker --> Faith[Claim-Level Faithfulness Assessment]
    Faith --> Queue
    API --> JobStatus[Tenant-Scoped Evaluation Status]
    JobStatus --> Queue
```

**Important:** As of Day 10, evaluation jobs are submitted through an
internal queue function and a demo script. A public job-submission
endpoint and automatic RAG evaluation sampling are **not yet
implemented**.

## Implemented Features (Days 1--10)

  -----------------------------------------------------------------------
  Area                                Implemented capability
  ----------------------------------- -----------------------------------
  API foundation                      FastAPI application, health
                                      endpoint, automated tests

  Data modeling                       PostgreSQL models for customers,
                                      documents, and support tickets;
                                      Alembic migrations

  Security                            JWT authentication, tenant-scoped
                                      access, role-based authorization,
                                      invitation-only registration, login
                                      rate limiting

  Local infrastructure                Dockerized API and PostgreSQL with
                                      pgvector; Docker Compose
                                      development setup

  Knowledge ingestion                 Document ingestion, text chunking,
                                      384-dimensional
                                      sentence-transformer embeddings

  Semantic retrieval                  Vector similarity search over
                                      PostgreSQL/pgvector

  Grounded generation                 Retrieval-augmented answering
                                      through the OpenAI Responses API,
                                      with returned sources

  Retrieval quality                   BM25 lexical search, dense
                                      retrieval, reciprocal rank fusion
                                      (RRF), cross-encoder reranking

  Answer safeguards                   Citation validation, abstention
                                      behavior, evaluation cases,
                                      observability-oriented metrics

  Faithfulness evaluation             Structured, claim-level assessment
                                      with supported / unsupported /
                                      contradicted verdicts and evidence
                                      attribution

  Evaluation persistence              RAG evaluation metrics stored in
                                      PostgreSQL

  Background processing               Durable PostgreSQL evaluation jobs,
                                      separate polling worker, retries
                                      with exponential backoff,
                                      lease-based recovery, tenant-scoped
                                      status lookup

  Testing                             Pytest coverage across APIs,
                                      database behavior,
                                      retrieval/evaluation logic, retry
                                      policy, and tenant isolation
  -----------------------------------------------------------------------

### Retrieval and Answering Pipeline

1.  **Ingest:** Store enterprise documents and split them into
    retrievable chunks.
2.  **Embed:** Generate vector representations with
    `sentence-transformers/all-MiniLM-L6-v2` (384 dimensions).
3.  **Retrieve:** Run dense vector similarity and BM25 keyword
    retrieval.
4.  **Fuse:** Combine ranked results using reciprocal rank fusion,
    `1 / (60 + rank)`.
5.  **Rerank:** Apply `cross-encoder/ms-marco-MiniLM-L-6-v2` to improve
    evidence relevance.
6.  **Generate:** Ask `gpt-4.1-mini` to answer using the retrieved
    context.
7.  **Validate:** Check citations and apply abstention safeguards when
    evidence is insufficient.
8.  **Evaluate:** Measure retrieval quality (including Recall@K and MRR)
    and assess answer faithfulness at the claim level.

### Durable Asynchronous Evaluation

The Day 10 worker decouples faithfulness evaluation from interactive API
requests:

-   Jobs are persisted in PostgreSQL with `pending`, `running`,
    `completed`, or `failed` status.
-   Workers claim eligible jobs using
    `SELECT ... FOR UPDATE SKIP LOCKED` to reduce duplicate concurrent
    claims.
-   Each claimed job receives an execution lease; expired leases can be
    reclaimed.
-   Transient failures are retried with capped exponential backoff and a
    maximum attempt count.
-   Completion and failure updates verify the expected attempt number to
    guard against stale worker updates.
-   Job-status lookups filter by both job ID and customer ID to maintain
    tenant isolation.

**Current limitations:** This is a database-backed polling queue rather
than a dedicated broker. Lease renewal, operational alerting, automatic
evaluation sampling, and fully containerized worker deployment remain
future hardening work.

## Technology Stack

  -----------------------------------------------------------------------
  Layer                               Technology
  ----------------------------------- -----------------------------------
  Language                            Python 3.11

  API                                 FastAPI, Pydantic

  Database                            PostgreSQL, pgvector

  ORM / migrations                    SQLAlchemy, Alembic

  Authentication                      JWT, tenant-scoped RBAC

  Embeddings                          Sentence Transformers
                                      (`all-MiniLM-L6-v2`)

  Lexical retrieval                   `rank-bm25`

  Ranking                             Reciprocal Rank Fusion;
                                      CrossEncoder
                                      (`ms-marco-MiniLM-L-6-v2`)

  Generation / evaluation             OpenAI Responses API
                                      (`gpt-4.1-mini` for answer
                                      generation)

  Background jobs                     PostgreSQL-backed queue and
                                      standalone Python worker

  Infrastructure                      Docker, Docker Compose

  Testing                             pytest
  -----------------------------------------------------------------------

## Getting Started

The commands below assume **Windows PowerShell**, with Docker Desktop
running. Paths and configuration may need adjustment for your local
environment.

### 1. Clone the repository

``` powershell
git clone https://github.com/aashikazim/enterprise-ai-operations-copilot.git
cd enterprise-ai-operations-copilot
```

### 2. Start the local services

``` powershell
docker compose up -d --build
```

Review `compose.yaml` or `docker-compose.yml` in the repository for
service names, exposed ports, and database credentials. If you prefer
running FastAPI directly on Windows, you can use Docker only for
PostgreSQL.

### 3. Set up the Python backend

``` powershell
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

### 4. Configure environment variables

Create `backend/.env` using the environment variables expected by the
application. A typical local configuration includes:

``` dotenv
DATABASE_URL=postgresql+psycopg://<user>:<password>@localhost:5432/copilot_db
OPENAI_API_KEY=<your-openai-api-key>
```

The project also requires the JWT configuration used by its existing
authentication settings. **Use the exact variable names defined by your
settings module.** Never commit `.env`, API keys, passwords, or real
customer documents.

> When running Python directly on Windows, `localhost` usually connects
> to a published PostgreSQL container port. When running inside Docker
> Compose, use the configured database service hostname instead.

### 5. Apply database migrations

``` powershell
alembic upgrade head
```

The `evaluation_jobs` table is introduced by the Day 10 migration. Do
not substitute `drop_all()` for migrations; it can destroy existing
data.

### 6. Start the API

If running the API directly from the `backend` directory:

``` powershell
python -m uvicorn app.main:app --reload
```

Open the interactive API documentation at **http://localhost:8000/docs**
(assuming the default port and application entry point).

### 7. Start the evaluation worker

In a second PowerShell terminal:

``` powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m app.workers.evaluation_worker
```

The worker loads the backend environment configuration and polls the
evaluation job table. An OpenAI API key is required for evaluations that
call the model.

### 8. Run tests

``` powershell
python -m pytest tests/ -v
```

Tests use an isolated PostgreSQL database (`copilot_test_db`), not the
development database. Make sure the test database and required
extensions are available before running integration tests.

## API Surface

Representative endpoints implemented during the first ten days:

  -----------------------------------------------------------------------------
  Method                  Endpoint                      Purpose
  ----------------------- ----------------------------- -----------------------
  GET                     `/health`                     Service health check

  POST                    `/knowledge/documents`        Ingest a knowledge
                                                        document

  POST                    `/knowledge/search`           Search document chunks

  POST                    `/rag/ask`                    Generate an
                                                        evidence-grounded
                                                        answer

  GET                     `/rag/evaluations/{job_id}`   Retrieve an evaluation
                                                        job's status within the
                                                        authenticated tenant
  -----------------------------------------------------------------------------

Authentication, customer, document, and ticket CRUD endpoints are also
part of the backend; refer to `/docs` for the exact request and response
schemas. **The Day 10 evaluation queue does not yet expose a public POST
submission endpoint.**

### Example: Ask a Knowledge Question

``` http
POST /rag/ask
Authorization: Bearer <JWT_TOKEN>
Content-Type: application/json

{
  "question": "What does the company's MFA policy require?"
}
```

The response includes an answer and supporting sources; additional
citation-validation and abstention fields are produced by the RAG
service. Check the generated OpenAPI schema for the precise response
shape in the current revision.

## Evaluation and Reliability

This project treats AI quality as an engineering concern rather than a
demo-only feature.

**Retrieval evaluation** - Recall@K: whether relevant evidence appears
in the retrieved top-K results. - Mean Reciprocal Rank (MRR): how highly
the first relevant result is ranked. - Hybrid retrieval and reranking
experiments to compare retrieval strategies.

**Answer evaluation** - Citation validation: check whether cited sources
match available evidence. - Abstention: avoid presenting unsupported
answers as established facts. - Claim-level faithfulness: classify
claims as `supported`, `unsupported`, or `contradicted`, with supporting
evidence references. - Structured evaluation results and persistence for
later analysis.

**Worker reliability** - Durable jobs survive API process restarts. -
Row-level locks support concurrent worker claiming. - Lease expiry
supports recovery from interrupted workers. - Bounded retries and
recorded errors make failures inspectable. - Tenant-scoped job access
limits cross-customer information exposure.

## Development Progress

  --------------------------------------------------------------------------
  Day                     Milestone                  Status
  ----------------------- -------------------------- -----------------------
  1                       FastAPI, health check,     Complete
                          PostgreSQL, pytest         

  2                       Customer/document/ticket   Complete
                          models, CRUD, Alembic      

  3                       JWT authentication and     Complete
                          tenant RBAC                

  3.5                     Invitation-only            Complete
                          registration, login rate   
                          limiting, isolated test DB 

  4                       Dockerized backend and     Complete
                          pgvector                   

  5                       Chunking, embeddings,      Complete
                          vector search              

  6                       RAG answering and          Complete
                          retrieval metrics          

  7                       BM25 + dense retrieval,    Complete
                          RRF, cross-encoder         
                          reranking                  

  8                       Citation validation,       Complete
                          abstention, evaluation     
                          cases, observability       

  9                       Claim-level faithfulness   Complete
                          and persistent RAG metrics 

  10                      Durable background         Complete
                          evaluation jobs and worker 
  --------------------------------------------------------------------------

## Roadmap

The following capabilities are **planned, not yet implemented**:

-   [ ] Connect automatic evaluation sampling to real `/rag/ask`
    traffic.
-   [ ] Add an authenticated evaluation-submission API and worker health
    checks.
-   [ ] Containerize and operationalize the worker in Docker Compose.
-   [ ] Add dashboards, tracing, latency/error metrics, and alerting.
-   [ ] Build customer-facing connectors and external API integrations.
-   [ ] Implement agentic workflows and tool calling (potentially with
    LangGraph).
-   [ ] Add a React interface for enterprise users and operators.
-   [ ] Add CI/CD, deployment documentation, and production security
    hardening.

## Engineering Decisions and Trade-offs

**Why PostgreSQL + pgvector?** A single database can store tenant
metadata, operational entities, vectors, evaluation metrics, and durable
job state, simplifying an early-stage deployment. At larger scale,
dedicated search infrastructure may become useful.

**Why hybrid retrieval?** Dense embeddings capture semantic similarity;
BM25 helps with exact terms, identifiers, and keyword-heavy enterprise
queries. Reciprocal rank fusion combines their complementary rankings
before cross-encoder reranking.

**Why asynchronous faithfulness evaluation?** A model-based evaluator
adds latency and external API cost. Running it in a separate worker
keeps the interactive request path independent of slower
quality-assurance tasks.

**Why database-backed jobs?** PostgreSQL transactions and row locking
provide a straightforward durable queue for a portfolio-scale system. A
production workload may justify a dedicated broker, distributed
scheduler, and stronger monitoring.

**Why explicit tenant filtering?** Authentication identifies the user;
tenant-scoped queries enforce data separation. Both are required in
multi-customer enterprise software.

## Lessons from Implementation

Day 10 exposed practical integration issues that informed the system
design:

-   Standalone workers must explicitly load the same database and API
    configuration as the web application.
-   Creating an Alembic migration does not apply it;
    `alembic upgrade head` is required.
-   Integration tests must create valid parent records before inserting
    rows with foreign keys.
-   Test fixtures must satisfy schema constraints such as required
    customer email fields.
-   Development and test databases must remain isolated to avoid
    accidental data loss.

These are the kinds of deployment, integration, and reliability details
that matter when delivering AI systems into real customer environments.

## Security and Data Handling

-   JWT-protected routes and tenant-aware data access are implemented.
-   Local secrets belong in environment configuration, not source
    control.
-   Evaluation jobs persist questions, answers, and retrieved evidence;
    use synthetic data for demonstrations and establish retention/access
    policies before handling sensitive customer content.
-   This project has not undergone a production security review and
    should not be treated as compliance-certified.

## Repository and Contributions

This is an independently developed, actively evolving portfolio project.
Development is tracked on the **`main`** branch. Issues and constructive
feedback are welcome.

**Repository:**
[github.com/aashikazim/enterprise-ai-operations-copilot](https://github.com/aashikazim/enterprise-ai-operations-copilot)

------------------------------------------------------------------------

*Built to explore the engineering required to move enterprise AI from a
promising prototype toward a reliable, measurable, multi-tenant
product.*
