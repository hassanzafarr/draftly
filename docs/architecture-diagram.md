# Draftly Architecture Diagram

Draftly is a multi-tenant SaaS app for RAG-assisted proposal generation. Users upload reference documents, the backend extracts and embeds chunks into pgvector, and new RFPs are used to retrieve relevant context before an LLM writes a structured proposal draft.

## System Overview

```mermaid
flowchart TB
    user[User]
    browser[Browser]
    frontend[React SPA<br/>Vite + Tailwind<br/>Zustand auth state]
    api[Django REST API<br/>DRF + SimpleJWT<br/>org-scoped permissions]
    admin[Django Admin]
    redis[Redis<br/>Celery broker + result backend]
    worker[Celery Worker<br/>document ingestion<br/>proposal generation]
    db[(PostgreSQL + pgvector<br/>organizations, users<br/>documents, chunks<br/>rfps, proposals)]
    storage[(File Storage<br/>local media in dev<br/>Supabase S3-compatible in prod)]
    google[Google AI<br/>Gemini generation<br/>Gemini embeddings]
    groq[Groq API<br/>fallback generation]
    sentry[Sentry<br/>frontend, backend, worker]

    user --> browser
    browser --> frontend
    frontend -->|REST JSON over /api<br/>JWT access + refresh| api
    frontend -->|polls processing state| api
    api --> admin
    api -->|enqueue async jobs| redis
    redis --> worker
    api <--> db
    worker <--> db
    api <--> storage
    worker <--> storage
    worker -->|embed documents and RFPs| google
    worker -->|generate proposal JSON| google
    worker -->|on Gemini rate limit| groq
    frontend --> sentry
    api --> sentry
    worker --> sentry
```

## Document Ingestion Flow

```mermaid
sequenceDiagram
    actor User
    participant Frontend as React SPA
    participant API as Django REST API
    participant Storage as File Storage
    participant Redis
    participant Worker as Celery Worker
    participant Google as Google AI Embeddings
    participant DB as PostgreSQL + pgvector

    User->>Frontend: Upload PDF, DOCX, or TXT
    Frontend->>API: POST /api/documents/
    API->>API: Validate JWT, org membership, document quota
    API->>Storage: Save uploaded file
    API->>DB: Create Document(status=pending)
    API->>Redis: Enqueue ingest_document(document_id)
    API-->>Frontend: Return document record

    Frontend->>API: Poll GET /api/documents/
    Redis->>Worker: Run ingest_document
    Worker->>DB: Set Document(status=processing)
    Worker->>Storage: Read uploaded file
    Worker->>Worker: Extract text and chunk with overlap
    Worker->>Google: Batch embed chunks
    Google-->>Worker: 768-dim vectors
    Worker->>DB: Replace Chunk rows for document
    Worker->>DB: Set Document(status=processed, chunk_count)
    API-->>Frontend: Updated processing status
```

## Proposal Generation Flow

```mermaid
sequenceDiagram
    actor User
    participant Frontend as React SPA
    participant API as Django REST API
    participant Redis
    participant Worker as Celery Worker
    participant Google as Google AI
    participant Groq as Groq Fallback
    participant DB as PostgreSQL + pgvector

    User->>Frontend: Submit RFP text or file
    Frontend->>API: POST /api/rfps/
    API->>API: Validate JWT, org membership, proposal quota
    API->>DB: Create RFP and Proposal(status=generating)
    API->>Redis: Enqueue generate_proposal_task(proposal_id)
    API-->>Frontend: Return proposal id

    Frontend->>API: Poll GET /api/proposals/{id}/
    Redis->>Worker: Run generate_proposal_task
    Worker->>Google: Analyze RFP into structured brief
    Worker->>Google: Embed RFP query
    Google-->>Worker: Query vector
    Worker->>DB: Search org-scoped chunks by cosine distance
    DB-->>Worker: Top matching context chunks
    Worker->>Google: Generate 10-section proposal JSON
    alt Gemini rate limit or quota error
        Worker->>Groq: Generate proposal JSON fallback
        Groq-->>Worker: Proposal sections
    else Gemini succeeds
        Google-->>Worker: Proposal sections
    end
    Worker->>DB: Save Proposal(status=draft, sections)
    API-->>Frontend: Draft is ready
```

## Deployment Topology

```mermaid
flowchart LR
    subgraph Local Development
        localFrontend[frontend container<br/>Vite on :5173]
        localBackend[backend container<br/>Django on :8000]
        localWorker[worker container<br/>Celery]
        localRedis[redis container<br/>:6379]
        localDb[(optional localdb profile<br/>pgvector Postgres :5432)]
        localMedia[(media volume)]

        localFrontend -->|/api proxy| localBackend
        localBackend --> localRedis
        localRedis --> localWorker
        localBackend --> localDb
        localWorker --> localDb
        localBackend --> localMedia
        localWorker --> localMedia
    end

    subgraph Production
        vercel[Vercel<br/>React build]
        railway[Railway or Django host<br/>REST API]
        prodWorker[Celery worker]
        prodRedis[Redis]
        supabaseDb[(Supabase Postgres<br/>pgvector)]
        supabaseStorage[(Supabase Storage<br/>S3-compatible)]

        vercel -->|HTTPS /api| railway
        railway --> prodRedis
        prodRedis --> prodWorker
        railway --> supabaseDb
        prodWorker --> supabaseDb
        railway --> supabaseStorage
        prodWorker --> supabaseStorage
    end
```

## Core Boundaries

| Boundary | Responsibility |
| --- | --- |
| `frontend/src` | Authenticated SPA, document upload, RFP submission, proposal editing, PDF export, polling for async status. |
| `backend/apps/accounts` | Organizations, users, roles, JWT-facing auth views, subscription tier quota metadata. |
| `backend/apps/documents` | Uploaded document models, extraction, chunking, embedding, chunk persistence. |
| `backend/apps/proposals` | RFP and proposal models, proposal generation task, RAG retrieval, LLM prompt and fallback handling. |
| `backend/apps/core` | Shared embeddings client and DRF permission classes for org scope and quota enforcement. |

## Important Notes

- Tenant isolation is enforced through `org` foreign keys and org-scoped querysets/permissions.
- Vector search is filtered by `org_id` before ranking chunks by pgvector cosine distance.
- The frontend currently polls async status rather than using SSE or WebSockets.
- The current embedding dimension is 768, configured for Google Gemini embeddings.
- Gemini is the primary generation provider; Groq is only used as a rate-limit fallback.
