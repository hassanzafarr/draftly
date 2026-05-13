# Future Enhancements — Proposal Quality Roadmap

Living list of ideas to improve proposal generation quality. Ranked by impact ÷ effort.
Last updated: 2026-05-14

---

## Current State (baseline)

- Two-pass generation: RFP analysis → context retrieval → 10-section JSON
- Pure semantic search, top-20 chunks, single Gemini call returning all 10 sections at once
- Pattern C category labeling in prompt (chunks tagged Company Profile / Past Proposal / Case Study)
- Tone inferred from RFP analysis
- Groq llama-3.1-8b fallback on Gemini 429

---

## Tier S — High Impact, Low Effort

### 1. Pattern A retrieval (per-section search)
- **Current:** one global search → 20 chunks shared by all 10 sections
- **Change:** 10 vector searches, each scoped to a relevant category, smaller top-k each
- **Effort:** ~80 LOC in `generator.py`
- **Cost:** 10× embed calls per proposal (~$0.0001 — negligible)
- **Win:** pricing section sees only pricing chunks; no cross-section bleed

### 2. Few-shot examples in prompt
- Inject 1-2 "gold standard" past sections into system prompt so LLM mimics house voice
- **Effort:** flag exemplar chunks in DB, inject by section
- **Win:** consistent tone, on-brand language

### 3. Hybrid search (BM25 + vector)
- Pure semantic misses exact-match keywords (client names, product codes, acronyms)
- Add Postgres `tsvector` keyword search, merge scores with vector results
- **Effort:** 1 day, Postgres native
- **Win:** catches "must mention HIPAA" type literal requirements

### 4. Reranker
- Pull top-50 chunks → rerank with cross-encoder (Cohere Rerank or local `bge-reranker-base`) → keep top-10
- **Effort:** API integration, ~30 LOC
- **Win:** massive precision lift; industry standard for RAG

---

## Tier A — Big Quality Lift, More Work

### 5. Section-by-section generation
- **Current:** one Gemini call returns all 10 sections — token budget split thin
- **Change:** 10 calls, each with section-specific prompt + targeted context; stream sections as they complete
- **Effort:** refactor generator + frontend SSE
- **Win:** longer/deeper sections, faster perceived response, single-section retry on failure

### 6. RFP requirements checklist enforcement
- Pass 1 already extracts `key_requirements` + `red_flags`
- After generation, validator checks: did each requirement appear? If not → patch missing ones with targeted retry
- **Effort:** ~50 LOC validator + retry loop
- **Win:** never miss "must include SOC 2 details" type asks

### 7. Citation tracking
- Track which chunks contributed to each section
- Show source-attribution in editor ("This paragraph drew from `case_study_03`")
- **Effort:** ~150 LOC — prompt asks LLM to emit citations, frontend renders
- **Win:** user trust, hallucination spotting, audit trail

### 8. Pricing tables / numeric anchoring
- Pricing section currently free-text
- Extract numeric ranges from past proposals at ingest → constrain new pricing to historical bands → render real table in editor
- **Effort:** structured extraction in ingest, table editor in frontend
- **Win:** stop AI inventing numbers

---

## Tier B — Quality of Life

### 9. Tone presets per industry / client
- RFP analyzer already infers `tone_preference`
- Expose as user-selectable + remember per client across proposals
- **Effort:** ~20 LOC backend, dropdown in frontend

### 10. Chunk quality scoring at ingest
- Currently every chunk has equal weight
- Filter junk: page headers, ToCs, signatures, repeated boilerplate
- **Effort:** heuristic skip (very short, all-caps, repeated patterns)
- **Win:** less noise in retrieval

### 11. Token-aware chunking
- Currently word-based (~500 words, 50 overlap) — chunks cut mid-sentence
- Switch to `tiktoken` / Gemini token counter; respect sentence boundaries
- **Effort:** 1 day, can use `langchain-text-splitters`
- **Win:** cleaner chunks, better embeddings

### 12. Multi-turn refinement
- After draft, user clicks "make pricing more aggressive" or "add HIPAA emphasis" → targeted regen of one section with edit instruction
- **Effort:** section-level regen endpoint + UI buttons
- **Win:** huge UX upgrade, sticky feature

---

## Tier C — Plumbing

### 13. Embedding cache
- RFP edited and re-submitted → re-embeds full text
- Cache by content hash in Redis
- **Effort:** ~10 LOC
- **Win:** faster iteration on repeated submissions

### 14. Streaming response
- Currently 3s frontend polling
- Switch Gemini to `stream=True` → SSE endpoint → frontend EventSource
- **Effort:** backend SSE endpoint, frontend EventSource client
- **Win:** perceived speed

### 15. Eval harness
- Hold-out set of (RFP → winning proposal) pairs
- Score new generations on: section coverage, requirement-hit rate, length, ROUGE vs winners
- **Effort:** ~1 week
- **Win:** measurable progress — without this every "improvement" is vibes

---

## Recommended Sequencing

| Budget | Stack |
|--------|-------|
| 1 day | #4 reranker (biggest quality jump per LOC) |
| 3 days | #4 + #6 requirements checklist (catch red-flag misses) |
| 1 week | #4 + #6 + #5 section-by-section + #15 eval harness |
| 1 month | All of Tier S + Tier A |

**Non-negotiable eventually:** #15 eval harness. Without it, no objective signal that any change actually helps.

---

## Already Shipped (related context)

- 2026-05-14 — `Document.category` field + Knowledge UI filter ([backend/apps/documents/models.py:18-22](backend/apps/documents/models.py#L18-L22))
- 2026-05-14 — Pattern C source-type labeling in retrieval prompt ([backend/apps/proposals/generator.py:59-79](backend/apps/proposals/generator.py#L59-L79))
- Two-pass RFP analysis ([backend/apps/proposals/generator.py:90](backend/apps/proposals/generator.py#L90))
- Tone-aware system prompt ([backend/apps/proposals/generator.py:111](backend/apps/proposals/generator.py#L111))
