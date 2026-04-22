# Architecture: AI-Powered RFP & Proposal Generator

## System Overview

A multi-tenant SaaS RAG application. SMEs upload historical proposals and case studies; the system chunks, embeds, and indexes them. When a new RFP arrives, the system retrieves the most relevant historical context and uses Claude to generate a tailored 10-section proposal draft.

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                          Browser (React)                        │
│   Dashboard │ Doc Upload │ RFP Input │ Proposal Editor │ Export │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTPS (REST + SSE)
┌────────────────────────────▼────────────────────────────────────┐
│                     Django REST Framework                        │
│  /api/documents/  │  /api/rfps/  │  /api/proposals/  │  /auth/  │
└────┬──────────────┬──────────────┬───────────────────┬──────────┘
     │              │              │                   │
     │         Celery Worker   Claude API          SimpleJWT
     │         (async tasks)   (Sonnet 4.6)
     │              │
┌────▼──────────────▼─────────────────────────────────────────────┐
│                     PostgreSQL + pgvector                        │
│   organizations │ users │ documents │ chunks │ rfps │ proposals  │
└─────────────────────────────────────────────────────────────────┘
     │
┌────▼──────────────┐     ┌──────────────────────────┐
│   Redis (Celery   │     │      Object Storage      │
│   broker/backend) │     │       (Supabase)         │
└───────────────────┘     └──────────────────────────┘
```

---

## Directory Structure

```
rfp-generator/
├── ARCHITECTURE.md
├── docker-compose.yml
├── .env.example
│
├── backend/                        # Django project
│   ├── manage.py
│   ├── requirements.txt
│   ├── config/                     # Django settings package
│   │   ├── __init__.py
│   │   ├── settings.py
│   │   ├── urls.py
│   │   └── celery.py
│   ├── apps/
│   │   ├── accounts/               # User + Org auth
│   │   │   ├── models.py
│   │   │   ├── serializers.py
│   │   │   ├── views.py
│   │   │   └── urls.py
│   │   ├── documents/              # Upload + ingestion pipeline
│   │   │   ├── models.py
│   │   │   ├── serializers.py
│   │   │   ├── views.py
│   │   │   ├── urls.py
│   │   │   ├── tasks.py            # Celery: extract, chunk, embed
│   │   │   └── pipeline.py         # Text extraction + chunking logic
│   │   ├── proposals/              # RFP input + generation
│   │   │   ├── models.py
│   │   │   ├── serializers.py
│   │   │   ├── views.py
│   │   │   ├── urls.py
│   │   │   ├── tasks.py            # Celery: RAG + generation
│   │   │   └── generator.py        # RAG retrieval + Claude prompt
│   │   └── core/                   # Shared utilities
│   │       ├── embeddings.py       # OpenAI embedding calls
│   │       ├── storage.py          # S3/local file handling
│   │       └── permissions.py      # Org-scoped DRF permissions
│
└── frontend/                       # React app
    ├── package.json
    ├── vite.config.js
    ├── index.html
    └── src/
        ├── main.jsx
        ├── App.jsx
        ├── api/                    # Axios API client
        │   └── client.js
        ├── store/                  # Zustand global state
        │   └── auth.js
        ├── pages/
        │   ├── Login.jsx
        │   ├── Dashboard.jsx       # Document library overview
        │   ├── Documents.jsx       # Upload + manage docs
        │   ├── NewRFP.jsx          # Paste/upload RFP
        │   ├── ProposalEditor.jsx  # Edit + export generated proposal
        │   └── NotFound.jsx
        └── components/
            ├── Layout.jsx
            ├── Navbar.jsx
            ├── DocumentCard.jsx
            ├── UploadZone.jsx
            ├── ProposalSection.jsx
            └── StreamingText.jsx   # SSE streaming display
```

---

## Data Models

### Organization
| Field | Type | Notes |
|---|---|---|
| id | UUID PK | |
| name | varchar | |
| subscription_tier | enum | starter / growth / agency |
| doc_quota | int | max documents allowed |
| proposal_quota | int | max proposals/month |
| created_at | timestamptz | |

### User
| Field | Type | Notes |
|---|---|---|
| id | UUID PK | |
| org | FK → Organization | |
| email | varchar unique | |
| role | enum | admin / member |
| is_active | bool | |

### Document
| Field | Type | Notes |
|---|---|---|
| id | UUID PK | |
| org | FK → Organization | |
| uploaded_by | FK → User | |
| title | varchar | |
| file_key | varchar | Supabase object key |
| file_type | enum | pdf / docx / txt |
| status | enum | pending / processing / processed / failed |
| chunk_count | int | set after ingestion |
| created_at | timestamptz | |

### Chunk
| Field | Type | Notes |
|---|---|---|
| id | UUID PK | |
| document | FK → Document | |
| org | FK → Organization | for scoped search |
| content | text | raw chunk text |
| embedding | vector(1536) | pgvector column |
| metadata | jsonb | {page, char_offset, source_title} |
| created_at | timestamptz | |

### RFP
| Field | Type | Notes |
|---|---|---|
| id | UUID PK | |
| org | FK → Organization | |
| created_by | FK → User | |
| title | varchar | |
| raw_text | text | extracted RFP content |
| file_key | varchar | nullable |
| created_at | timestamptz | |

### Proposal
| Field | Type | Notes |
|---|---|---|
| id | UUID PK | |
| rfp | FK → RFP | |
| org | FK → Organization | |
| sections | jsonb | {section_name: content} |
| status | enum | generating / draft / final |
| created_at | timestamptz | |

---

## RAG Pipeline

### Ingestion (async, per Document)
```
Upload → Supabase Storage → Celery task triggered
  → Extract text (PyMuPDF / python-docx)
  → Split into ~500-token chunks (50-token overlap)
  → Batch embed via OpenAI text-embedding-3-small
  → INSERT chunks + vectors into pgvector
  → Mark document status = processed
```

### Generation (on POST /api/rfps/{id}/generate/)
```
RFP text → embed query vector
  → pgvector cosine similarity search (top 20, scoped to org_id)
  → Build context string from top chunks
  → Stream Claude Sonnet 4.6 with structured 10-section prompt
  → Write sections to Proposal.sections (jsonb)
  → SSE stream tokens back to frontend
```

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| POST | /api/auth/register/ | Create org + admin user |
| POST | /api/auth/token/ | JWT login |
| POST | /api/auth/token/refresh/ | Refresh JWT |
| GET | /api/documents/ | List org documents |
| POST | /api/documents/ | Upload document |
| DELETE | /api/documents/{id}/ | Delete document + chunks |
| GET | /api/rfps/ | List RFPs |
| POST | /api/rfps/ | Create RFP (text or file) |
| POST | /api/rfps/{id}/generate/ | Trigger RAG generation |
| GET | /api/proposals/ | List proposals |
| GET | /api/proposals/{id}/ | Get proposal detail |
| PATCH | /api/proposals/{id}/ | Update/finalize proposal |
| GET | /api/proposals/{id}/stream/ | SSE stream during generation |

---

## Subscription Quotas

| Tier | Price | Documents | Proposals/month | Users |
|---|---|---|---|---|
| Starter | $99/mo | 50 | 5 | 2 |
| Growth | $299/mo | 200 | 25 | 10 |
| Agency | $499/mo | Unlimited | Unlimited | Unlimited |

Enforced via `OrgQuotaPermission` middleware on upload and generate endpoints.

---

## Technology Choices

| Concern | Choice | Reason |
|---|---|---|
| Backend framework | Django + DRF | Batteries-included, rapid API dev |
| Vector DB | pgvector on Postgres | No extra infra; SQL joins with metadata |
| Embeddings | OpenAI text-embedding-3-small | Cost-efficient, 1536-dim |
| LLM | Claude Sonnet 4.6 | High quality long-form generation, streaming |
| Task queue | Celery + Redis | Async ingestion without blocking request thread |
| Auth | SimpleJWT | Stateless, easy React integration |
| File storage | Supabase Storage (S3-compatible) | Scalable object storage with local dev fallback |
| Frontend | React + Vite + Tailwind | Fast DX, no SSR needed |
| State | Zustand | Lightweight, no boilerplate |
| Containerization | Docker Compose | Local dev parity |
