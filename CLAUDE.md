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
  Google AI  → gemini-2.5-flash (proposal section generation, primary)
  Groq       → llama-3.1-8b-instant (fallback on Gemini 429)

File storage: local disk in dev (/media/), Supabase S3-compatible in prod
Error monitoring: Sentry (frontend + backend + Celery)
```

### Multi-Tenancy

Every model (Document, Chunk, RFP, Proposal) has an `org` FK. The `IsOrgMember` DRF permission class is applied on all private endpoints and scopes all querysets to `request.user.org`. Embedding similarity search is always filtered to the org's chunks.

Subscription quotas are enforced by `OrgDocQuotaPermission` and `OrgProposalQuotaPermission`:

| Tier    | Docs (processed) | Proposals/month |
|---------|-----------------|----------------|
| starter | 50              | 5              |
| growth  | 200             | 25             |
| agency  | unlimited       | unlimited      |

Monthly quota resets on the 1st of each month (UTC). Only `status=processed` documents count toward the doc quota. **No payment/billing integration exists** — tiers are set manually.

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
4. Call Gemini 2.5 Flash with domain-aware system prompt; expect JSON with 10 keys
5. On Gemini 429 → fall back to Groq `llama-3.1-8b-instant`
6. Parse JSON (fallback: regex search for `{...}` pattern) → store in `Proposal.sections` (JSONField); set `status = draft`
7. On error → `status = failed`; quota errors skip Celery retry

Both tasks use Celery retry (max 2 retries, 30-second countdown).

**Frontend polling**:
- `ProposalEditor` polls `GET /api/proposals/{id}/` every 3 seconds while `status === "generating"`
- `Documents` page polls `GET /api/documents/` every 5 seconds while any doc is `status === "processing"`

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
| `config/settings.py` | Django settings; `GEMINI_MODEL`, `EMBEDDING_MODEL`, `EMBEDDING_DIMS` constants; Sentry init |
| `config/celery.py` | Celery app config wired to Redis |
| `apps/accounts/` | `Organization` (tiers + quotas), `User` (admin/member roles), JWT register/login/me |
| `apps/documents/` | `Document`, `Chunk` models; `ingest_document` Celery task; `pipeline.py` text extraction + chunking |
| `apps/proposals/` | `RFP`, `Proposal` models; `generate_proposal_task` Celery task; `generator.py` RAG + Gemini/Groq logic |
| `apps/core/` | `embeddings.py` (Google AI batch embed); `permissions.py` (IsOrgMember, quota permissions) |

Django apps are declared under `apps/` namespace (e.g., `apps.accounts`).

## Frontend Layout (`frontend/src/`)

| Path | Purpose |
|------|---------|
| `api/client.js` | Axios instance with JWT request interceptor and 401→refresh response interceptor |
| `store/auth.js` | Zustand `useAuthStore` (user, login, logout, fetchMe); tokens in `localStorage` |
| `instrument.js` | Sentry frontend initialization |
| `lib/mock-data.js` | Mock data for Analytics and Templates pages |
| `pages/Login.jsx` | Login form |
| `pages/Register.jsx` | Registration form |
| `pages/Dashboard.jsx` | Home: doc/proposal counts, recent proposals, org info, subscription tier |
| `pages/Documents.jsx` | Upload zone, document list with status polling (5s while processing), delete |
| `pages/NewRFP.jsx` | Create RFP (title + text or file upload), triggers proposal generation |
| `pages/ProposalEditor.jsx` | 10-section proposal editor, polling while generating, PDF export (jsPDF), save/finalize |
| `pages/Editor.jsx` | Alternative/enhanced proposal editor (similar structure to ProposalEditor) |
| `pages/Analytics.jsx` | Mock analytics dashboard with Recharts (monthly perf, win rate, proposals by category) |
| `pages/Templates.jsx` | Template gallery with category filtering (mock data only) |
| `pages/knowledge.jsx` | Knowledge base management (similar to Documents, adds category badges) |
| `pages/NotFound.jsx` | 404 page |
| `components/AppShell.jsx` | Main app wrapper with sidebar + navbar layout |
| `components/Sidebar.jsx` | Left nav sidebar |
| `components/Navbar.jsx` | Top navigation bar |
| `components/AuthShell.jsx` | Auth page wrapper (no sidebar) |
| `components/AuthForm.jsx` | Reusable login/signup form |
| `components/Generator.jsx` | Proposal generation wizard UI |
| `components/UploadZone.jsx` | Drag-drop file upload |
| `components/DocumentCard.jsx` | Single document card (status, delete) |
| `components/ProposalSection.jsx` | Editable proposal section with Tiptap |
| `components/ThemeProvider.jsx` | Dark/light theme context |

### Frontend Routes (`App.jsx`)

| Route | Component |
|-------|-----------|
| `/login` | Login |
| `/register` | Register |
| `/` | Dashboard |
| `/templates` | Templates |
| `/knowledge` | Knowledge (doc management with categories) |
| `/analytics` | Analytics (mock) |
| `/rfps/new` | NewRFP |
| `/proposals/:id` | ProposalEditor |

Vite proxies `/api` requests to the backend in development (target set via `VITE_API_URL` env var).

---

## Configuration

Copy `.env.example` to `.env` and fill in at minimum:

```
GOOGLE_AI_API_KEY    # chunk embeddings + Gemini proposal generation
GROQ_API_KEY         # fallback LLM on Gemini rate limit
SECRET_KEY           # Django secret key
DATABASE_URL         # Supabase Postgres connection string (includes pgvector)
SENTRY_DSN           # optional — Sentry error monitoring
```

For local dev outside Docker set `DB_HOST=localhost`. Database defaults target Docker service names.

JWT tokens: 8-hour access, 7-day refresh (rotate-refresh enabled via `SIMPLE_JWT` in settings).

---

## Implemented Features

- Multi-tenant orgs with subscription tiers (starter / growth / agency)
- User auth: JWT register, login, refresh, `/me` endpoint; admin/member roles per org
- Document management: PDF/DOCX/TXT upload, async ingestion, chunking, pgvector embedding, quota enforcement
- RFP submission: text input or file upload (text extracted server-side)
- AI proposal generation: RAG (top-20 chunks) → Gemini 2.5 Flash → domain-aware 10-section JSON
- Groq fallback on Gemini 429 rate limit
- Proposal editing: 10-section Tiptap editors, save draft, finalize
- PDF export via jsPDF (client-side)
- Conditional frontend polling (docs + proposals)
- Sentry error monitoring (React + Django + Celery)
- Docker Compose for local dev; Railway (backend) + Vercel (frontend) for prod

---

## Known Gaps

- **No Stripe/billing**: Subscription tiers enforced by permissions but no payment flow.
- **No team invitations**: User model supports admin/member roles and multiple users per org, but no invite endpoint or UI exists.
- **No SSE/WebSocket**: Frontend uses polling (3s proposals, 5s docs); no streaming endpoint.
- **No tests**: Neither pytest nor Jest is configured.
- **No CI/CD**: Dockerfiles and Railway/Vercel configs exist but no GitHub Actions workflows.
- **No DOCX export**: PDF export only (jsPDF, client-side).
- **Analytics/Templates are mock**: No real data — uses `lib/mock-data.js`.
- **Knowledge page is duplicate**: `knowledge.jsx` overlaps with `Documents.jsx`; no backend distinction.
- **Word-based chunking**: Chunk sizes vary for non-English or code-heavy docs.
- **Editor.jsx vs ProposalEditor.jsx**: Two similar editor pages — unclear which is canonical.
