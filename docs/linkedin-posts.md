# Draftly — Build-in-Public LinkedIn Posts

Stack of ready-to-post LinkedIn updates from building **Draftly** (multi-tenant SaaS, RAG-based AI proposal generator). Each post = one problem + the fix. Mix of long-form deep-dives and short punchy posts. Comment hook at the bottom of each post — copy the whole block into LinkedIn and ship.

## Contents

1. [Generic proposals → reranker fixed retrieval](#post-1) (long)
2. [One LLM call doing too much → two-pass generation](#post-2) (long)
3. [LLM vendor risk → three-tier fallback chain](#post-3) (long)
4. [Zero throttling → DRF scoped throttles](#post-4) (long)
5. [Celery failures invisible → DLQ + Sentry fingerprints](#post-5) (long)
6. [Category labels were cosmetic → Pattern C retrieval labeling](#post-6) (short)
7. [Stripe Portal plan changes didn't sync → resolve tier from price_id](#post-7) (short)
8. [Admin panel exposed → IP allowlist + the XFF trap](#post-8) (short)
9. [Tests failed `type "vector" does not exist` → pgvector in template1](#post-9) (short)
10. [Multi-tenant leak risk → `IsOrgMember` everywhere](#post-10) (short)
11. [Quota enforcement that doesn't lie → only processed docs count](#post-11) (short)
12. [Polling without burning the API → conditional polling](#post-12) (short)
13. [JWT UX → axios 401→refresh interceptor](#post-13) (short)
14. [Schema upgrade gotcha → old chunks miss new metadata](#post-14) (short)
15. [Stripe webhook idempotency → `StripeEvent` row before processing](#post-15) (short)
16. [Railway deploy death-by-1000-cuts → CORS/CSRF/ALLOWED_HOSTS](#post-16) (short)
17. [A user pasted an API key in chat → revoke first, wire later](#post-17) (short)

---

## Post 1

**Format:** Long-form

> Our AI proposal generator was producing generic mush. The bug wasn't the model. It was the retrieval.

We use RAG to turn uploaded company docs (past proposals, case studies, profiles) into tailored proposal drafts. For weeks the output read like Wikipedia: technically on-topic but stripped of the specifics customers actually paid for.

**The problem**

Pure vector search, top-20 chunks, straight into the LLM. Semantic embeddings are great at "kinda related" but they don't know which chunks are *most useful for this exact section*. A pricing section would get pulled toward team bios because the bios mentioned past pricing models. A team section would pull case studies because both talk about "clients." Cross-section bleed everywhere.

You could see it in the drafts. Every section felt 60% relevant, 40% noise.

**The fix — a reranker**

Two-stage retrieval:

1. **Recall stage** — pgvector cosine search pulls top-50 candidates (cheap, broad).
2. **Precision stage** — Cohere Rerank v3 (cross-encoder) re-scores those 50 against the query and keeps the top 10.

A cross-encoder reads the query and the chunk *together*, so it actually understands relevance instead of just nearest-neighbor distance. The 50→10 cut throws out the chunks that were semantically nearby but contextually wrong.

We also store the rerank score per chunk so we can debug "why did this chunk make it in" later.

**Tricky bit**

Cohere's free tier is 1000 calls/month, 10 req/min. We added graceful degrade — if `COHERE_API_KEY` is missing or the call errors, we fall back to vector-only and log it. The product still works without the reranker; it just generates 2026-era drafts instead of 2027 ones.

**Lesson**

If your RAG output feels generic, your model isn't the problem. Your top-k is. A reranker is ~30 lines of code and is the highest impact-per-LOC change we've shipped this quarter.

> What's your default top-k after rerank? Anyone tried local cross-encoders (bge-reranker) instead of Cohere?

---

## Post 2

**Format:** Long-form

> We were asking one LLM call to do too much. Splitting it in half made every section measurably better.

**The problem**

Original pipeline: take the RFP → retrieve chunks → one Gemini call returns all 10 proposal sections as a single JSON blob.

It worked. But the sections were shallow. The model burned its token budget juggling structure (10 keys, schema compliance, length balance) instead of *thinking* about the RFP. Pricing felt vague. Methodology felt generic. Requirements buried in paragraph 4 of the RFP got missed entirely.

**The fix — two passes**

We split the call into two:

**Pass 1 — Analyst.** Read the RFP. Output a structured brief: key requirements, red flags, evaluation criteria, inferred tone, missing info. JSON, no prose.

**Pass 2 — Writer.** Take the brief + retrieved chunks. Generate the 10 sections, but now the model knows:
- exactly which requirements *must* appear in the proposal,
- what tone to write in (formal/casual/technical),
- what red flags to address proactively.

Same total tokens. Wildly different output quality.

**Why it works**

Asking a model to *analyze* and *write* in one shot is like asking a developer to read a Jira ticket and submit a PR in the same keystroke. The analyst pass forces the model to commit to an interpretation before writing — which means every section is conditioned on the same understanding instead of each section re-deriving requirements on its own.

**Bonus: better debugging.** When a draft misses a requirement, we look at Pass 1's output. Either it didn't extract the requirement (retrieval / prompt issue) or it did but Pass 2 ignored it (writer issue). Two narrow questions instead of one fuzzy one.

> Anyone running 3+ passes? Diminishing returns set in fast for us at 2 — curious if a separate "critic" pass actually moves the needle.

---

## Post 3

**Format:** Long-form

> Our LLM bill went from $0 to "anxiety" in a week. Then Gemini's free tier blocked us mid-demo. Here's how we de-risked the vendor.

**The problem**

We started on Gemini 2.5 Flash. Free tier is 20 requests/day. Fine for solo dev — until you demo to two prospects in the same afternoon and the third call returns 429. Worse, single-vendor LLM dependency is a single point of failure: provider outage = your product is dead.

**The fix — three-tier fallback chain**

Every proposal-generation call now flows through this order:

1. **Claude Haiku 4.5** (primary) — best quality-per-dollar in our eval, with ephemeral prompt caching on the system prompt (we cache the 10-section instructions + tone rules, only the RFP + chunks vary).
2. **Gemini 2.5 Flash** (fallback) — fires when Claude is down or rate-limited.
3. **Groq llama-3.1-8b-instant** (last resort) — fires only on Gemini 429. Lower quality but instant and free-tier friendly.

The orchestrator is one function. Each call attempt is wrapped in try/except; on failure it logs the provider + error to our `GenerationEvent` telemetry table and falls through to the next.

**The non-obvious win — telemetry**

We tag every generation with which provider actually ran. So when a customer complains "my drafts got worse this week," the first query is `SELECT provider, COUNT(*) FROM generation_events WHERE org_id = X GROUP BY provider`. If they suddenly shifted from Claude to Groq, we know Claude is rate-limited for that org's traffic pattern *before* they file a ticket.

**Lesson**

If you're building on an LLM, you're building on someone else's quota and uptime. Treat your primary provider like a hot cache: assume it'll be unavailable 1% of the time, and design the failure path before you ship the feature.

> What's your fallback strategy? Cold swap, retry-with-backoff, or full three-tier like ours?

---

## Post 4

**Format:** Long-form

> Our backend had zero rate limiting. Login, signup, expensive LLM endpoints — all wide open. Three real risks, one weekend, fixed.

**The problem**

1. **Brute-force on `/api/auth/token/`** — unlimited password attempts.
2. **Signup spam** — bots could create thousands of orgs.
3. **LLM cost runaway** — `/api/rfps/{id}/generate/` calls Claude. One looped script could burn hundreds of dollars before quotas caught up.

**The fix — DRF scoped throttles**

- Global defaults: anon 30/min, authenticated 240/min.
- Per-endpoint scoped throttles for the expensive/abusable ones:
  - Login: 10/min
  - Register: 5/hour
  - Password change: 5/hour
  - Proposal generation: 20/hour (LLM cost cap)
  - Document upload: 30/hour (POST only — GET polling unaffected)
  - Stripe checkout: 10/hour
- Redis cache backend so counters survive across workers.
- Every rate is an environment variable — tune without redeploying.

**The tricky bit (this one bit us)**

DRF's `@api_view` decorator does NOT propagate the `throttle_scope` attribute to the wrapping view class. Set `throttle_scope = "auth_login"` on a function-based view and `ScopedRateThrottle` silently no-ops — you think you're throttling, you're not.

Fix: subclass `ScopedRateThrottle`, pin `scope_name` as a class attr, override `allow_request` to set `self.scope` before delegating. Now the throttle works regardless of view style.

**Lesson**

Rate limiting on day one is cheaper than retrofitting on day 200. The threat model for an LLM-backed product isn't "user does dumb things" — it's "your AWS bill becomes the attack surface."

> What's the first endpoint you throttle in a new project? Login is the obvious one but I'd argue your most expensive endpoint matters more.

---

## Post 5

**Format:** Long-form

> "We have monitoring" used to mean "we log errors." That's not monitoring. Here's the dead-letter queue we shipped after a Celery failure ate 40 jobs.

**The problem**

Background jobs (document ingestion, proposal generation) use Celery with retries. When a task failed permanently — Gemini outage, malformed PDF, whatever — the only trace was:

- A `status="failed"` row in the relevant model.
- A `logger.error(...)` line nobody reads.

No central queue. No replay. No alerting. Gemini went down for an hour, 40 proposals failed, and we found out from a customer.

**The fix**

**`DeadLetterTask` table** capturing terminal failures: task name, ID, args, kwargs, exception type, message, traceback, the org affected, a `resolved` flag.

**Two capture paths for full coverage:**

1. Celery `task_failure` signal handler — auto-fires in real worker processes.
2. Explicit `record_failure()` call inside each task's `except` block — covers test mode.

**Why both?** This was the gotcha. `CELERY_TASK_ALWAYS_EAGER=True` (used in unit tests) runs tasks via `.apply()` synchronously, which bypasses the worker dispatcher entirely. The `task_failure` signal never fires in tests. Signal-only architecture = zero DLQ coverage in your test suite, which is exactly when you most want to catch regressions. The helper is idempotent on `(task_id, exc_type)` so both paths can run safely.

**Sentry integration:**

Every captured exception tagged with `celery.task_name`, `celery.task_id`, `org_id`, and a deterministic fingerprint `["celery-dlq", task_name, exc_type]`. Sentry alert rule: "page on-call if fingerprint contains `celery-dlq` and count > 5 in 10 min." Routes by task type — `ingest_document` spikes go to one channel, `generate_proposal_task` spikes to another.

**Django admin actions** — "Mark resolved" + "Re-enqueue selected tasks." Five lines of code each. They've saved us hours during incidents.

**Lesson**

`status="failed"` is not observability. Build the DLQ table the day you ship the first Celery task. And never trust signals without an explicit fallback for whatever execution mode your tests run in.

> What's your favorite "tests pass but production breaks" gotcha? Eager-mode signal silence is my new top entry.

---

## Post 6

**Format:** Short

> Shipped UI categories for documents (Company Profile / Past Proposal / Case Study). Realized two weeks later the categories were purely cosmetic. The retrieval pipeline ignored them.

The fix took ~50 lines and lifted output coherence noticeably.

We inject the category into the prompt context. Instead of:

```
[Source 3]
{chunk text}
```

…the LLM now sees:

```
[Source 3 | Case Study: Acme Corp 2024]
{chunk text}
```

Then the system prompt has a mapping: "for `pricing` and `methodology`, weight Past Proposal sources. For `relevant_experience` and `why_us`, weight Case Study sources. For `team_qualifications`, weight Company Profile."

This is "Pattern C" labeling — the cheapest version of category-aware retrieval. The expensive version (Pattern A) does separate vector searches per section, each filtered by category. We'll get there. For now, labels-in-prompt got 80% of the value for 5% of the effort.

> Have you found the model actually respects in-prompt source labels? Or do you need to enforce it with per-section retrieval filters?

---

## Post 7

**Format:** Short

> Two days after launching Stripe, a customer downgraded via Customer Portal. The webhook fired. Our backend ignored it. They kept full access to the paid tier.

**The bug:** we were resolving the user's tier from `subscription.metadata`. Metadata is what we set at Checkout — Stripe doesn't update it when the user changes plans in the Portal. So `metadata.tier` stayed `agency` even after they moved to `solo`.

**The fix:** resolve tier from the line-item `price.id`. We keep a static map `{stripe_price_id: tier_name}` in settings, look up the active price on the subscription, and that's the source of truth. Customer Portal plan changes now sync correctly on the next `customer.subscription.updated` webhook.

Subtle lesson: subscription metadata is what *you* wrote. Line-item price IDs are what Stripe knows. Always resolve from Stripe's source of truth, not your own breadcrumbs.

> What's your favorite Stripe gotcha? Mine used to be webhook signature verification — this one took its crown.

---

## Post 8

**Format:** Short

> Locked down our admin panel with an IP allowlist. Almost shipped it with a vulnerability that would've made the gate worse than useless.

The naive way: check `request.META["REMOTE_ADDR"]` against allowlist. Behind a reverse proxy (Railway, in our case), `REMOTE_ADDR` is the proxy's IP — so either nobody gets in, or you "fix" it by reading `X-Forwarded-For` and trusting the left-most entry.

**Trusting left-most XFF is the bug.** Attackers can set that header to any value. `X-Forwarded-For: 1.2.3.4` and they're suddenly an "allowed IP."

**Fix:** count back from the *right* end of XFF by `ADMIN_TRUSTED_PROXY_COUNT`. Railway has one proxy in front of you → count = 1 → take the second-to-last entry. The right-most XFF entries are written by infrastructure you trust; the left-most are user-supplied.

Default `ADMIN_TRUSTED_PROXY_COUNT = 0` means "XFF is ignored entirely" — safe, but breaks the gate behind any proxy until you set the env var. Documented loudly in `.env.example` so the next deploy doesn't silently lock everyone out.

> Anyone using IP allowlists on admin panels in 2026, or has WireGuard / Cloudflare Access fully replaced the pattern?

---

## Post 9

**Format:** Short

> Spent half a day debugging `type "vector" does not exist` in our test suite. The fix was one SQL statement, in the wrong database.

We use pgvector for embeddings. Our test runner uses `pytest --create-db --no-migrations` so Django syncs models directly to a fresh test DB on each run.

**The catch:** Django creates the test DB from `template1`. `pgvector` is an extension, not a default type. So unless `template1` has the extension installed, every new test DB is born without it, and any `vector(768)` column creation fails immediately.

**Fix:** install the extension in `template1` once:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

…connected to `template1`, not your dev DB. Every test DB created after that inherits the extension. Documented in our README so the next contributor doesn't lose the same half-day.

> What's the most expensive single SQL statement you've forgotten to run? Mine is now `CREATE EXTENSION` in `template1`.

---

## Post 10

**Format:** Short

> Multi-tenant data leaks aren't a "design" failure. They're a "one developer forgot `.filter(org=...)` in one queryset" failure. Here's how we made forgetting impossible.

Every model in Draftly has an `org` ForeignKey. The risk is obvious: one un-scoped queryset in one view and Org A sees Org B's proposals.

**The defense, in layers:**

1. **DRF permission class `IsOrgMember`** on every private viewset. Returns 403 if `request.user.org != obj.org`.
2. **Base viewset overrides `get_queryset()`** to apply `.filter(org=self.request.user.org)` by default. The default scope is correct; you have to *opt out* (which would show up in code review) to leak.
3. **Embedding search** is filtered by org before vector similarity even runs. No cross-tenant chunk can be a candidate.

The pattern: make the safe path the default path. Devs shouldn't have to *remember* to scope. The framework should scope, and unscoping should require an explicit, obvious action.

> What's your multi-tenant safety net? Row-level security at the Postgres layer or framework-level scoping like ours?

---

## Post 11

**Format:** Short

> Our quota system was lying to users. They'd hit "10 documents this month" and have only 4 usable ones — the other 6 were stuck in `processing` or had failed.

**The fix:** quota counts only documents with `status = processed`. Failed uploads don't count. In-flight uploads don't count. If ingestion fails partway through, the user's quota slot is automatically freed — no support ticket needed.

**Plus:** monthly quota resets at 00:00 UTC on the 1st of each month, calculated from `processed_at`, not `created_at`. A document uploaded on the 31st that finishes processing on the 1st counts against the new month — which is what you'd expect if you think about it for two seconds, and almost never what naive quota code does.

Small detail. Saves hours of "why does the dashboard say I have 4 docs but the cap shows 10?" support threads.

> What's a quota edge case you've seen that customers actually noticed? Reset timezones are my new favorite.

---

## Post 12

**Format:** Short

> Our frontend was polling the API every 3 seconds. On every page. Even when nothing was happening. We were the DDoS.

**The fix:** conditional polling. Only fire the request if there's actually something to refresh.

- Proposal editor: poll `/api/proposals/{id}/` every 3s **only while `status === "generating"`**. Once it flips to `draft` or `failed`, polling stops cold.
- Documents page: poll `/api/documents/` every 5s **only while any doc has `status === "processing"`**. All docs done? Polling stops.

Implementation is a `useEffect` with a setInterval that returns its own cleanup, gated by a status check. About 10 lines per page.

Result: our API request volume from idle users dropped to roughly zero. Database load on `SELECT proposals WHERE id = X` queries became flat instead of saw-toothed.

The bigger lesson: polling is fine, but polling forever isn't. Every interval needs an exit condition.

> SSE / WebSockets next? We keep punting on it because conditional polling does the job. Curious if anyone's regretted that call.

---

## Post 13

**Format:** Short

> We set JWT access tokens to 8 hours. Users got logged out mid-session anyway. Forgot the most important interceptor.

The first time it happened we thought the token was expiring early. It wasn't. The token was valid for 8 hours, but the user opened the app, did nothing for 8h1m, then clicked Save and got booted to the login screen with no warning.

**Fix: axios response interceptor.** On any 401 from the API:

1. Catch the 401.
2. POST to `/api/auth/refresh/` with the 7-day refresh token (stored separately).
3. Get a fresh access token, swap it into the axios default headers.
4. Retry the original request transparently.
5. If the refresh itself 401s, *then* boot to login — the refresh token actually expired.

User experience: they save the form. It works. They never knew anything happened.

It's ~20 lines and turns a fragile UX into an invisible one. The trick is making sure you don't retry the refresh call itself (infinite 401 loop) — gate it with a "request URL is the refresh endpoint" check before retrying.

> What's your token expiry pair? We landed on 8h access / 7d refresh — long enough for a workday, short enough to limit damage if access is leaked.

---

## Post 14

**Format:** Short

> Shipped a new column. All new data was correct. All old data was broken — silently. The kind of bug you only catch when a customer mentions output looks worse than before.

We added a `category` field to documents post-launch. The ingest task copies that category into each chunk's metadata, which the retrieval prompt uses to label sources ("Case Study: …", "Past Proposal: …").

Brand new uploads worked perfectly. But every document uploaded **before** the migration had chunks without `metadata.category`. The retrieval prompt fell back to a generic `Reference` label — which the LLM treated as low-signal and underweighted.

The bug wasn't loud. Proposals generated from old corpora just felt vaguer than ones from new corpora. No error, no warning — just a quiet quality regression for legacy users.

**Fix:** documented re-ingest workaround in the admin. For a permanent fix we'd backfill via a one-off Celery task that re-runs chunking on documents flagged `metadata IS NULL`. Haven't shipped it yet — most affected users hit the issue, re-uploaded, and moved on.

**Lesson:** when you add a field that downstream code depends on, ask "what about every row that existed before this migration?" Then ask it again. Then write the backfill.

> What's the worst silent-degradation bug you've shipped? The non-erroring ones are always the worst to catch.

---

## Post 15

**Format:** Short

> Stripe retries webhooks. We didn't handle that. A customer got upgraded to Agency tier *twice* on a single payment. Almost upgraded again on the third retry before we caught it.

**The problem:** Stripe re-delivers webhooks if your endpoint doesn't 200 fast enough — or just because. Our handler was idempotent on side effects (setting `org.tier = "agency"` twice is fine) but not on *all* side effects — we were also incrementing usage counters and creating audit log entries each time.

**The fix:** every incoming webhook gets an `event_id`. First action in the handler is to `INSERT` into a `StripeEvent(event_id)` table with a unique constraint. If the insert fails (duplicate key), we 200 immediately and skip processing entirely — Stripe is happy, the event is logged, the handler is a no-op.

About 15 lines including the migration. Now we can process the same webhook ten times and only one of them takes effect.

**Stripe's docs recommend this pattern explicitly.** I read past it three times because "idempotency" sounded like a thing you did at the database level, not the webhook level. It's both.

> What's the most expensive duplicate-side-effect bug you've shipped? Mine's now ~$200 in misapplied tier upgrades I had to manually unwind.

---

## Post 16

**Format:** Short

> Eight consecutive commits, all titled some variant of "fix CORS." Then four titled "fix CSRF." Then three "add ALLOWED_HOSTS." Welcome to deploying Django to Railway for the first time.

The pain isn't any single fix. It's that Django has three separate trust lists for the same concept (which domains are you), and missing any one of them returns a different error in a different place:

- `ALLOWED_HOSTS` missing → 400 with no useful frontend signal.
- `CORS_ALLOWED_ORIGINS` missing → CORS preflight fails, errors only visible in browser devtools network tab.
- `CSRF_TRUSTED_ORIGINS` missing → POST requests 403 from the admin panel only, *after* login succeeds.

**Lessons earned in commit blood:**

1. Set all three lists from the same env var if you can — one source of truth.
2. Strip trailing slashes when parsing the env var. `https://draftly.software/` is not the same string as `https://draftly.software` and Django will reject one of them silently.
3. Include both your prod domain and the Vercel/Railway preview domains.
4. WhiteNoise + a health check endpoint goes in before any other deploy fix. Otherwise you debug for an hour before realizing the container's not even up.

> What's your favorite "deployed it and immediately found a new error" story? Mine is the gap between commits `fix CORS (3rd time)` and `fix CSRF (1st time)`.

---

## Post 17

**Format:** Short

> A user pasted an Anthropic API key in chat. "Just wire it up for testing." I refused, and that's the move every time.

**Why refuse, even for $5 of credit:**

Chat transcripts are logged. They may be backed up, replicated, indexed, or visible to a third party reviewing the conversation. A key pasted in chat is effectively public the moment it's typed. Anything I build that uses that literal key value bakes the leak into history — git, logs, scrollback, screenshots.

**The actual workflow:**

1. Revoke the key in the provider console immediately. Don't try to "use it up first." It's compromised the moment it leaves a secure channel.
2. Generate a fresh key in the console.
3. Put it in `.env` (gitignored).
4. Wire the integration to read from `settings.ANTHROPIC_API_KEY` — code never sees the literal value.

The rule doesn't bend for stakes, framing, or time pressure. "Just for testing" leaks the same way "for production" does.

If you work with AI assistants: bake this into your collaboration rules. The assistant shouldn't even *offer* to use a pasted key. If yours does, that's a behavior to correct.

> What's your secret-handling discipline with AI tools? I've seen everything from "paste freely" to "block the assistant from reading `.env` entirely."

---

*All posts above are based on shipped work in Draftly as of 2026-05-23. Stack: Django + DRF + Celery + Redis + PostgreSQL/pgvector + React/Vite, deployed Railway + Vercel.*
