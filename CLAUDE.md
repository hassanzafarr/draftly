# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Draftly** is a multi-tenant SaaS application that uses RAG (Retrieval-Augmented Generation) to automate proposal generation. Organizations upload reference documents (past proposals, case studies, company profiles), which are chunked and embedded into a pgvector store. When a new RFP is submitted, the system retrieves the most relevant chunks via semantic search and feeds them to an LLM to produce a structured 10-section proposal draft that users can edit and finalize.

---

## Commands

### Docker (recommended)

```bash
docker compose up --build                                          # Start all services
docker compose exec backend python manage.py migrate               # Run DB migrations
docker compose exec backend python manage.py createsuperuser       # Create admin user
docker compose exec backend python manage.py makemigrations        # Create new migrations
```

Frontend is served at `http://localhost:5173`, API at `http://localhost:8000/api/`, Django admin at `http://localhost:8000/admin/`.

### Local dev (without Docker)

```bash
# Terminal 1 – Django API
cd backend && source .venv/bin/activate && python manage.py runserver

# Terminal 2 – Celery worker (required for document ingestion + proposal generation)
cd backend && source .venv/bin/activate && celery -A config worker --loglevel=info

# Terminal 3 – React frontend
cd frontend && npm run dev
```

### Frontend

```bash
npm run dev        # Vite dev server on port 5173
npm run build      # Production build
npm run preview    # Preview production build
```

No test suite is currently configured for either backend or frontend.

---

## Architecture

### System Topology

```
React SPA (Vite, port 5173)
    │  REST + JSON polling
    ▼
Django REST API (port 8000)
    │                │
    ▼                ▼
Celery Worker  ←  Redis (broker + result backend)
    │
    ▼
PostgreSQL (Supabase) + pgvector extension
    (documents, chunks+embeddings, rfps, proposals)

External APIs:
  Google AI  → models/text-embedding-004 (768-dim vectors for chunks)
  Google AI  → gemini-2.0-flash-exp (proposal section generation)

File storage: local disk in dev (/media/), Supabase S3-compatible in prod
```

### Multi-Tenancy

Every model (Document, Chunk, RFP, Proposal) has an `org` FK. The `IsOrgMember` DRF permission class is applied on all private endpoints and scopes all querysets to `request.user.org`. Embedding similarity search is always filtered to the org's chunks.

Subscription quotas are enforced by `OrgDocQuotaPermission` and `OrgProposalQuotaPermission`:

| Tier    | Docs (processed) | Proposals/month |
|---------|-----------------|----------------|
| starter | 50              | 5              |
| growth  | 200             | 25             |
| agency  | unlimited       | unlimited      |

Monthly quota resets on the 1st of each month (UTC). Only `status=processed` documents count toward the doc quota.

### Key Async Flows

**Document ingestion** (`apps/documents/tasks.py → ingest_document`):
1. Extract text via PyMuPDF (PDF), python-docx (DOCX), or raw read (TXT)
2. Chunk into ~500-word segments with 50-word overlap (word-based, not token-based)
3. Embed each chunk via Google AI `models/text-embedding-004` (task type: `retrieval_document`), batched 100 per call
4. Bulk-insert `Chunk` rows with 768-dim vectors into pgvector
5. Set `Document.status = processed`; on error → `failed` with `error_message`

**Proposal generation** (`apps/proposals/tasks.py → generate_proposal_task`):
1. Embed the full RFP text via Google AI (task type: `retrieval_query`)
2. pgvector cosine distance search → top 20 chunks scoped to the org
3. Build context string: `[Source N: {doc_title}]\n{chunk_content}` for all 20 chunks
4. Call Gemini 2.0 Flash with system + user prompt; expect JSON with 10 keys
5. Parse JSON (fallback: regex search for `{...}` pattern) → store in `Proposal.sections` (JSONField); set `status = draft`
6. On error → `status = failed`

Both tasks use Celery retry (max 2 retries, 30-second countdown).

**Frontend polling**: `ProposalEditor` polls `GET /api/proposals/{id}/` every 3 seconds while `status === "generating"` until complete.

### Proposal Sections

The 10 JSON keys the LLM must produce:

```
executive_summary, understanding_requirements, proposed_solution,
relevant_experience, team_qualifications, project_timeline,
methodology, pricing, why_us, appendix
```

These keys are rendered as individual Tiptap rich-text editors in `ProposalEditor`. Display labels are mapped in `ProposalSection.jsx`.

---

## Backend Layout (`backend/`)

| Path | Purpose |
|------|---------|
| `config/settings.py` | Django settings; `GEMINI_MODEL`, `EMBEDDING_MODEL`, `EMBEDDING_DIMS` constants |
| `config/celery.py` | Celery app config wired to Redis |
| `apps/accounts/` | `Organization`, `User` (custom AbstractBaseUser), JWT registration/login |
| `apps/documents/` | `Document`, `Chunk` models; `ingest_document` Celery task; `pipeline.py` text extraction |
| `apps/proposals/` | `RFP`, `Proposal` models; `generate_proposal_task` Celery task; `generator.py` core logic |
| `apps/core/` | Shared utilities: embedding helpers, custom DRF permissions, storage backends |

Django apps are declared under `apps/` namespace (e.g., `apps.accounts`).

## Frontend Layout (`frontend/src/`)

| Path | Purpose |
|------|---------|
| `api/` | Axios instance with JWT request interceptor and 401→refresh response interceptor |
| `store/` | Zustand `useAuthStore` (user, login, logout, fetchMe); tokens persisted in `localStorage` |
| `pages/` | `Login`, `Register`, `Dashboard`, `Documents`, `NewRFP`, `ProposalEditor` |
| `components/` | `Navbar`, `Layout`, `DocumentCard`, `UploadZone`, `ProposalSection` |

Vite proxies `/api` requests to the backend in development (target set via `VITE_API_URL` env var).

---

## Configuration

Copy `.env.example` to `.env` and fill in at minimum:

```
GOOGLE_AI_API_KEY    # for both chunk embeddings and proposal generation (Gemini)
SECRET_KEY           # Django secret key
DATABASE_URL         # Supabase Postgres connection string (includes pgvector)
```

For local dev outside Docker set `DB_HOST=localhost`. Database defaults target Docker service names.

JWT tokens: 8-hour access, 7-day refresh (rotate-refresh enabled via `SIMPLE_JWT` in settings).

---

## Known Gaps

- **No SSE streaming**: Frontend uses polling (every 3s); no streaming endpoint is implemented.
- **No tests**: Neither pytest nor Jest is configured.
- **No CI/CD**: No GitHub Actions workflows exist.
- **No PDF/DOCX export** for generated proposals.
- **No multi-user org onboarding**: Only one admin per org; no invitation flow.
- **Chunking is word-based**, not token-based — chunk size may vary significantly for non-English or code-heavy documents.
