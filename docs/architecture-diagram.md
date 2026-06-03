# Draftly Architecture Diagram

Draftly is a multi-tenant proposal generation SaaS. Teams upload reusable company knowledge, Draftly extracts and embeds that content, then new RFPs retrieve the most relevant chunks before an LLM drafts a structured proposal.

## System Context

```mermaid
flowchart TB
    user[User]
    spa[React SPA<br/>Vite, Tailwind, Zustand<br/>routes for generator, knowledge, proposals, analytics, billing]
    api[Django REST API<br/>DRF, SimpleJWT, org-scoped permissions<br/>throttles and quota checks]
    admin[Django Admin<br/>IP allowlist middleware]
    worker[Celery Worker<br/>document ingestion and proposal generation]
    redis[(Redis<br/>Celery broker/result backend<br/>DRF throttle cache)]
    db[(PostgreSQL + pgvector<br/>orgs, users, documents, chunks<br/>RFPs, proposals, generation telemetry)]
    storage[(File Storage<br/>local media in dev<br/>Supabase S3-compatible in prod)]
    claude[Anthropic Claude<br/>primary proposal analysis/generation]
    gemini[Google Gemini<br/>embeddings and fallback generation]
    cohere[Cohere Rerank<br/>optional chunk reranking]
    groq[Groq<br/>small fallback when usable]
    stripe[Stripe<br/>checkout, portal, webhooks]
    sentry[Sentry<br/>frontend, API, worker]

    user --> spa
    spa -->|REST JSON over /api<br/>JWT access token + refresh flow| api
    spa -->|polls proposal/document status| api
    spa --> sentry

    api --> admin
    api <--> db
    api <--> storage
    api -->|enqueue async jobs| redis
    redis --> worker
    worker <--> db
    worker <--> storage

    worker -->|RFP analysis and generation| claude
    worker -->|document and query embeddings<br/>fallback generation/title extraction| gemini
    worker -->|rerank top vector matches| cohere
    worker -->|rate-limit fallback for small prompts| groq

    api -->|checkout, portal, subscription status| stripe
    stripe -->|signed webhook| api
    api --> sentry
    worker --> sentry
```

## Runtime Boundaries

```mermaid
flowchart LR
    subgraph Frontend["frontend/src"]
        routes[App routes<br/>Generator, Knowledge, Analytics<br/>Proposals, Editor, Settings, Pricing]
        apiClient[api/client.js<br/>Axios base URL, JWT attach<br/>401 refresh interceptor]
        auth[store/auth.js<br/>current user/session state]
    end

    subgraph Backend["backend/apps"]
        accounts[accounts<br/>Organization, User<br/>auth/profile/org settings]
        documents[documents<br/>Document, Chunk<br/>upload, validation, extraction]
        proposals[proposals<br/>RFP, Proposal, GenerationEvent<br/>RAG retrieval, generation, export, analytics]
        billing[billing<br/>Stripe checkout, portal<br/>webhook idempotency]
        core[core<br/>permissions, throttling<br/>embeddings, admin IP gate, DLQ]
    end

    routes --> apiClient
    routes --> auth
    auth --> apiClient
    apiClient --> accounts
    apiClient --> documents
    apiClient --> proposals
    apiClient --> billing

    documents --> core
    proposals --> core
    billing --> accounts
    proposals --> documents
```

## Document Ingestion Flow

```mermaid
sequenceDiagram
    actor User
    participant SPA as React SPA
    participant API as Django REST API
    participant Store as File Storage
    participant Redis
    participant Worker as Celery Worker
    participant Gemini as Google Gemini Embeddings
    participant DB as PostgreSQL + pgvector

    User->>SPA: Upload PDF, DOCX, or TXT
    SPA->>API: POST /api/documents/
    API->>API: Validate JWT, org membership, upload throttle, quota
    API->>Store: Save uploaded file
    API->>DB: Create Document(status=pending)
    API->>Redis: Enqueue ingest_document(document_id)
    API-->>SPA: Return document record

    SPA->>API: Poll GET /api/documents/
    Redis->>Worker: Run ingest_document
    Worker->>DB: Set Document(status=processing)
    Worker->>Store: Read uploaded file
    Worker->>Worker: Sanitize PDF when needed
    Worker->>Worker: Extract text and split into overlapping chunks
    Worker->>Gemini: Batch embed chunk text
    Gemini-->>Worker: 768-dimension vectors
    Worker->>DB: Replace Chunk rows for document
    Worker->>DB: Set Document(status=processed, chunk_count)
    API-->>SPA: Updated processing state
```

## Proposal Generation Flow

```mermaid
sequenceDiagram
    actor User
    participant SPA as React SPA
    participant API as Django REST API
    participant Redis
    participant Worker as Celery Worker
    participant Claude as Anthropic Claude
    participant Gemini as Google Gemini
    participant DB as PostgreSQL + pgvector
    participant Cohere as Cohere Rerank
    participant Groq as Groq

    User->>SPA: Submit RFP text/file, tone, length, optional sections
    SPA->>API: POST /api/rfps/
    API->>API: Validate JWT, org membership, RFP checks, proposal quota
    API->>DB: Create RFP and Proposal(status=generating, stage=queued)
    API->>Redis: Enqueue generate_proposal_task(proposal_id)
    API-->>SPA: Return proposal id

    SPA->>API: Poll GET /api/proposals/{id}/
    Redis->>Worker: Run generate_proposal_task
    Worker->>DB: Set stage=analyzing
    Worker->>Claude: Analyze RFP into structured brief
    alt Claude analyzer unavailable
        Worker->>Gemini: Analyze RFP fallback
    end

    Worker->>DB: Set stage=retrieving
    Worker->>Gemini: Embed RFP query
    Gemini-->>Worker: Query vector
    Worker->>DB: Org-scoped pgvector cosine search
    DB-->>Worker: Top matching chunks
    Worker->>Cohere: Optional rerank top matches
    Cohere-->>Worker: Ordered context chunks or fallback to vector order

    Worker->>DB: Set stage=drafting
    alt Claude generation enabled and available
        Worker->>Claude: Generate proposal JSON from RFP brief + context
    else Claude unavailable
        Worker->>Gemini: Generate proposal fallback
        opt Gemini rate-limited and prompt is small enough
            Worker->>Groq: Generate proposal fallback
        end
    end

    Worker->>DB: Save sections, labels, provider, status=draft
    Worker->>DB: Persist GenerationEvent telemetry and quality signals
    API-->>SPA: Draft is ready
```

## Billing Flow

```mermaid
sequenceDiagram
    actor User
    participant SPA as Pricing/Settings UI
    participant API as Django REST API
    participant Stripe
    participant DB as PostgreSQL

    User->>SPA: Choose tier and billing cadence
    SPA->>API: POST /api/billing/checkout/
    API->>API: Validate org membership and checkout throttle
    API->>Stripe: Create or reuse Customer
    API->>Stripe: Create Checkout Session
    API-->>SPA: Return checkout URL
    SPA->>Stripe: Redirect user to hosted checkout

    Stripe->>API: POST /api/billing/webhook/
    API->>API: Verify signature and record StripeEvent id
    API->>DB: Update Organization subscription tier/status

    SPA->>API: GET /api/billing/subscription/
    API-->>SPA: Current billing state and publishable key
```

## Deployment Topology

```mermaid
flowchart LR
    subgraph Local["Local development"]
        localSpa[frontend container<br/>Vite on :5173]
        localApi[backend container<br/>Django on :8000]
        localWorker[worker container<br/>Celery]
        localRedis[(redis:7-alpine<br/>:6379)]
        localDb[(optional localdb profile<br/>pgvector Postgres :5432)]
        localMedia[(media_vol<br/>/app/media)]

        localSpa -->|Vite proxy /api| localApi
        localApi --> localRedis
        localRedis --> localWorker
        localApi --> localDb
        localWorker --> localDb
        localApi --> localMedia
        localWorker --> localMedia
    end

    subgraph Production["Production"]
        vercel[Vercel<br/>React static build]
        railway[Railway or Django host<br/>REST API + admin]
        prodWorker[Celery worker process]
        prodRedis[(Managed Redis)]
        supabaseDb[(Supabase Postgres<br/>pgvector)]
        supabaseStorage[(Supabase Storage<br/>S3-compatible bucket)]

        vercel -->|HTTPS /api| railway
        railway --> prodRedis
        prodRedis --> prodWorker
        railway --> supabaseDb
        prodWorker --> supabaseDb
        railway --> supabaseStorage
        prodWorker --> supabaseStorage
    end
```

## Data Ownership

| Area | Owns | Notes |
| --- | --- | --- |
| `accounts` | `Organization`, `User` | Subscription tier determines document, proposal, and seat quotas. |
| `documents` | `Document`, `Chunk` | Chunks carry `org_id`, source metadata, category, and 768-dimension Gemini embeddings. |
| `proposals` | `RFP`, `Proposal`, `GenerationEvent` | Generation stores stage metadata, selected provider, retrieval telemetry, and quality signals. |
| `billing` | `StripeEvent` | Stripe event ids make webhook processing idempotent. |
| `core` | shared infrastructure | Permission checks, throttles, embeddings client, admin IP allowlist, and task failure recording. |

## Important Constraints

- Tenant isolation is enforced through `org` foreign keys, org-scoped querysets, and `IsOrgMember` permissions.
- Vector search filters by `org_id` before ranking chunks by pgvector cosine distance.
- Proposal status is exposed through polling; there is no active SSE or WebSocket path in the current code.
- Claude is the primary proposal provider when enabled and configured; Gemini is used for embeddings and fallback generation.
- Cohere rerank is optional and safely falls back to vector order when disabled or unavailable.
- File storage is local by default and switches to Supabase S3-compatible storage with `USE_SUPABASE_STORAGE=True`.
