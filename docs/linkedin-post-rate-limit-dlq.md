# Shipped: Rate Limiting + Celery Dead-Letter Queue on Draftly

Two production-hardening features I just shipped on **Draftly** (multi-tenant SaaS for AI proposal generation). Sharing the *what*, *why*, and *how* — in case anyone else is running a Django + Celery + LLM stack and skipping these.

---

## 1. Rate Limiting — Closing the Cost & Abuse Door

### The problem
The backend had **zero throttling**. Every endpoint was wide open. Three real risks:

1. **Brute-force on login** — `/api/auth/token/` accepted unlimited password attempts.
2. **Signup spam** — bots could create thousands of orgs.
3. **LLM cost runaway** — `/api/rfps/{id}/generate/` calls Claude / Gemini. One malicious user looping this endpoint could burn through hundreds of dollars before quotas caught up.

### What I built
- Configured Django REST Framework throttle classes globally (anon: 30/min, authenticated: 240/min).
- Built scoped throttles for sensitive endpoints, each with its own rate:
  - Login: **10/min**
  - Register: **5/hour**
  - Password change: **5/hour**
  - Proposal generation: **20/hour** (LLM cost cap)
  - Document upload: **30/hour**
  - Stripe checkout: **10/hour**
- Wired Redis as the cache backend so rate counters survive across multiple Django workers.
- All rates are environment variables — tunable without a redeploy.

### Tricky bit
DRF's `@api_view` decorator doesn't propagate `throttle_scope` attributes to the underlying view class. I had to subclass `ScopedRateThrottle` and pin the scope name at the class level instead.

### Impact
- Brute-force attacks on auth: dead on arrival.
- Worst-case LLM bill from a single compromised account: bounded.
- GET polling endpoints (proposals, documents) intentionally **not** throttled — frontend polls every 3–5s for status updates.

---

## 2. Celery Dead-Letter Queue + Sentry Alert Pipeline

### The problem
Background jobs (document ingestion, proposal generation) used Celery with retries. When a task failed permanently after exhausting retries, the only trace was:

- A `status="failed"` row in the database.
- A `logger.error(...)` line in worker logs (which nobody reads).

No central list of failures. No replay button. No automatic alerting. If Gemini went down for an hour and 50 proposals failed, ops would only find out when a customer complained.

### What I built

**A `DeadLetterTask` table** that captures every terminal failure:
- Task name, task ID, args, kwargs
- Exception type, message, traceback
- The org affected (so I can spot if one customer is having recurring problems)
- `resolved` flag + `resolved_at` timestamp

**Two capture paths** for full coverage:
1. **Celery `task_failure` signal handler** — auto-fires in production workers for any task.
2. **Explicit `record_failure()` call** inside each task's except block — covers `CELERY_TASK_ALWAYS_EAGER=True` mode used in tests, where signals don't fire.

The helper is idempotent on `(task_id, exception_type)` so both paths can run safely without duplicates.

**Sentry integration:**
- Tags every captured exception with `celery.task_name`, `celery.task_id`, `org_id`, and a deterministic fingerprint `["celery-dlq", task_name, exc_type]`.
- This means Sentry alert rules can route by task type — e.g., "page on-call if `ingest_document` fails 5 times in 10 minutes".

**Django admin actions:**
- "Mark as resolved" — clean up the queue after investigation.
- "Re-enqueue selected tasks" — one click to replay failed jobs with original args/kwargs. No copy-pasting task IDs into a Celery shell at 2 AM.

### Why both signal + explicit call?
This was a real "huh, that's annoying" moment. The Celery `task_failure` signal works perfectly in a real worker process, but `CELERY_TASK_ALWAYS_EAGER=True` (used in unit tests) runs tasks synchronously via `.apply()`, which bypasses the worker dispatcher entirely. So the signal **never fires in tests**. Two-layer approach guarantees coverage in both modes.

### Impact
- Failures are now visible in Django admin, not buried in logs.
- One-click replay for transient failures (network blips, API rate limits).
- Sentry alerts fire on patterns, not just on individual exceptions.
- Per-org failure tracking — if one customer's documents keep failing, I see it immediately.

---

## Lessons for anyone building on the same stack

1. **Rate limit on day one.** Adding it later means auditing every endpoint instead of designing it in. For LLM-backed apps especially — your AWS bill is the threat model.
2. **`status="failed"` is not observability.** Log-based failure tracking does not scale past one engineer. Build the DLQ table early.
3. **Test mode and worker mode behave differently.** Celery's eager mode skips a surprising number of signals. Don't trust signal-only architecture without an explicit fallback.
4. **Tag exceptions, don't just capture them.** Sentry without tags is a graveyard. Tags + fingerprints turn it into a routing layer.
5. **Make the ops UI clickable.** Django admin actions ("re-enqueue", "mark resolved") cost five lines of code each and save hours during incidents.

---

## Stack

- **Backend:** Django 5 + Django REST Framework + Celery + Redis
- **DB:** PostgreSQL + pgvector
- **LLMs:** Claude Haiku 4.5 (primary), Gemini → Groq (fallbacks), Cohere rerank
- **Observability:** Sentry (now with proper Celery tagging)
- **Hosting:** Railway (backend), Vercel (frontend)

Code lives in [Draftly](https://github.com/hassanzafarr/draftly) — happy to dig into any of this in the comments.

\#django #celery #python #saas #backend #devops #observability
