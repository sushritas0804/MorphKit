# Morphkit

**Visual, testable building blocks for LLM infrastructure, that adapt to your code.**

> Status: pre-MVP. This README is the single source of truth for what we are building, why, and how. It is a living document: update it whenever a decision changes.
> Team: 2 people (one main builder, one part-time co-builder). No external deadline; long-term build.
> Name note: "Morphkit" has NOT yet been checked for domain / GitHub / npm / PyPI / trademark conflicts. See section 19.

---

## 1. What exactly are we building? (plain explanation)

Morphkit has a **short-term product** and a **long-term vision**. Both are one product, built in stages.

**Short-term product (Phases 1-5): an LLM cost-control layer.**
A proxy that sits between an app and its LLM providers (OpenAI, Anthropic, Google, open-source models...). The customer changes one URL. From then on we:

1. **See** - log every request and show where the money goes (cost dashboard).
2. **Save** - reduce the bill using caching and routing easy requests to cheaper models.
3. **Prove** - measure that answer quality did not drop, so savings are trustworthy.
4. **Control** - let users arrange these behaviours as visual, drag-and-drop **blocks** (cache, budget cap, PII filter, router, fallback...), called **segments**.

**Long-term vision (Phase 6+): adaptive blocks inside a code editor.**
A graphical interface with drag-and-drop segments for common code that nearly every program needs (middleware, routes, auth, rate limiting...), plus a built-in AI-assisted code editor. When a user drops a segment into their project, it **adjusts itself to their code**: framework, naming, structure, existing config. Think of it as "libraries that fit your project instead of you fitting the library".

**Why this order?**
The LLM cost layer gives us real users, real data and a clear, measurable value (dollars saved) quickly. The segment system built for it becomes the foundation of the editor vision. Building the editor first would mean guessing what people want.

**One-line pitch:** *"Morphkit is the visual, testable control layer for LLM infrastructure, with blocks that adapt to your codebase."*

---

## 2. The problem

- Teams building on LLMs overspend and cannot easily see why (which feature, user, model, or agent run).
- Cost-cutting techniques exist (caching, routing to cheaper models, budgets) but teams avoid them because nobody can prove quality stayed the same.
- Agent workloads make it worse: one task can trigger dozens or hundreds of model calls, so per-token price is the wrong unit; **cost per task** is what matters.
- Reusable code "blocks" today are either rigid libraries or generic snippets/scaffolds that do not adapt to the project they land in.

## 3. Product layers

| Layer | Question it answers | Phase |
|---|---|---|
| See | Where is my LLM money going? | 1 |
| Save | How do I spend less, automatically? | 2-3 |
| Prove | Did quality stay the same? | 3 |
| Control | Can I arrange these behaviours visually and safely? | 4 |
| Agents | What does each agent task cost? Which runs are wasteful? | 5 |
| Adapt | Can blocks fit my own codebase and be edited in-app? | 6 |

## 4. Who it is for (initial users)

Start with small, reachable users, not enterprises:
- Indie developers and small startups shipping LLM features.
- College clubs, hackathon teams, student startups.
- Small teams with a monthly LLM bill big enough to care (validate with interviews in Phase 0).

Enterprises (SSO, compliance, private cloud) come in Phase 7.

## 5. Scope

### In scope for the MVP (Phase 1)
- OpenAI-compatible `/v1/chat/completions` proxy with streaming.
- 2-3 providers.
- API keys per project, request logging, cost calculation.
- Dashboard: spend by model / endpoint / day / tag, top expensive requests.
- One-command self-hosting via Docker Compose.

### Explicitly out of scope for the MVP
Routing, semantic caching, evaluation, visual pipeline builder, hosting/billing, code editor, multi-language support, embeddings endpoints, fine-tuning, image/audio APIs. These come later; do not build them early.

---

## 6. Architecture

```
          +------------------+
          |  Customer app    |   (changes only base URL + API key)
          +--------+---------+
                   | OpenAI-compatible HTTP (+ SSE streaming)
                   v
+------------------------------------------------------+
|                   Morphkit Gateway                   |
|  1. Auth + project lookup                            |
|  2. Pipeline runner (ordered segments)               |
|       [pre]  guardrails/PII -> budget cap -> cache   |
|       [core] router -> provider adapter              |
|       [post] cache write -> logging -> metrics       |
+---------+----------------+----------------+----------+
          |                |                |
          v                v                v
   LLM providers      PostgreSQL         Redis
 (OpenAI, Anthropic,  (logs, config,   (exact cache, rate
  Google, local)      prices, evals,    limits, locks)
                      pgvector for
                      semantic cache)
                           ^
                           |
                  +--------+---------+
                  | Admin API        |
                  +--------+---------+
                           ^
                  +--------+---------+
                  | Dashboard (web)  |  -> later: pipeline builder -> editor
                  +------------------+
```

Key design rules:
1. **The pipeline config is the source of truth.** The visual editor reads and writes the config (YAML/JSON); it never holds hidden state.
2. **Segments are the unit of reuse.** Every behaviour (cache, router, budget...) is a segment with a typed manifest and its own tests.
3. **Logging must never break a request.** Log asynchronously; if logging fails, the user's request still succeeds.
4. **Provider adapters are thin and replaceable.** Our code depends on an internal interface, not on any one provider SDK.
5. **Fail open.** If an optimization segment errors, fall back to the plain provider call.

## 7. Tech stack (initial decisions; confirm in Phase 0)

| Area | Choice | Why |
|---|---|---|
| Gateway | Python 3.12, FastAPI, httpx (async), uvicorn | Fast to build; large LLM ecosystem; fine performance for MVP |
| Provider layer | Thin internal adapter interface; optionally use an existing open-source library for provider translation in Phase 1 (pin and review versions) | Saves weeks; keep it swappable |
| Database | PostgreSQL + SQLAlchemy 2 + Alembic | Reliable, relational, migrations |
| Cache | Redis (exact cache, rate limits); pgvector (semantic cache) | Fewer moving parts than a separate vector DB |
| Embeddings | Small local sentence-embedding model by default; API embeddings optional | No extra cost, no data leaves the box |
| Dashboard | React + TypeScript + Vite + Tailwind + Recharts | Standard, fast to iterate |
| Pipeline builder (Phase 4) | React Flow | Node-graph UI |
| Code editor (Phase 6) | Monaco Editor | The editor behind VS Code |
| Code transforms (Phase 6) | tree-sitter (parsing), LibCST (Python), ts-morph/jscodeshift (TS/JS) | Structure-aware edits |
| Tooling | Docker Compose, GitHub Actions, pytest, ruff, mypy, pre-commit, ESLint, Vitest | Quality and repeatability |
| Later (volume) | ClickHouse for logs, Prometheus + Grafana for infra metrics | Only when Postgres becomes a bottleneck |

## 8. Repository structure (monorepo)

```
morphkit/
  README.md
  docker-compose.yml
  .env.example
  gateway/                  # FastAPI proxy
    app/
      main.py
      api/                  # /v1 routes, /admin/v1 routes, /healthz
      core/                 # config, auth, errors, logging
      providers/            # base.py + openai.py, anthropic.py, ...
      pipeline/             # runner, config loader, segment interface
      segments/             # built-in segments (one folder each)
        cache_exact/
        cache_semantic/
        budget_cap/
        pii_filter/
        router_rules/
        router_learned/
        fallback/
      cost/                 # price table, cost calculator
      db/                   # models, migrations
      eval/                 # evaluation harness (Phase 3)
    tests/
  dashboard/                # React app
    src/
  segments-spec/            # JSON Schema for segment manifests + pipeline config
  docs/                     # guides, ADRs (architecture decision records)
  scripts/                  # dev helpers, load tests, seed data
  benchmarks/               # reproducible cost/quality benchmarks
```

---

## 9. Core specifications

### 9.1 Request lifecycle

1. Receive `POST /v1/chat/completions` with `Authorization: Bearer <morphkit_key>`.
2. Authenticate, load the project and its active pipeline version.
3. Run **pre** segments in order (PII filter, budget check, cache lookup). Any segment may short-circuit (e.g. cache hit returns immediately).
4. Run **core**: router picks the model/provider; provider adapter calls it (streaming passthrough).
5. Run **post** segments (cache write after the full response is assembled, logging, metrics).
6. Return the response. Add response headers: `x-morphkit-request-id`, `x-morphkit-cache: hit|miss|bypass`, `x-morphkit-model-served`.

Streaming rule: forward chunks to the client as they arrive; assemble the full text in the background for cache writes and token accounting. If the stream breaks, log it with status `partial` and do not cache it.

### 9.2 Public API (MVP)

- `POST /v1/chat/completions` - OpenAI-compatible request/response, including `stream: true`.
- `GET /healthz` - liveness; `GET /readyz` - dependencies reachable.
- Optional request headers: `x-morphkit-tags: feature=search,user_tier=free` (cost attribution), `x-morphkit-task-id` and `x-morphkit-trace-id` (agent grouping, used from Phase 5).

### 9.3 Admin API (MVP, used by the dashboard)

- `GET /admin/v1/usage?group_by=model|tag|day&from=&to=`
- `GET /admin/v1/requests?limit=&cursor=&filters=`
- `GET /admin/v1/requests/{id}`
- `POST /admin/v1/projects`, `POST /admin/v1/projects/{id}/keys`
- `GET/PUT /admin/v1/projects/{id}/pipeline` (Phase 2+)

### 9.4 Data model (initial)

| Table | Key columns |
|---|---|
| `projects` | id, name, created_at |
| `api_keys` | id, project_id, key_hash, label, created_at, revoked_at |
| `requests` | id, project_id, ts, provider, model_requested, model_served, prompt_tokens, completion_tokens, cached_input_tokens, latency_ms, ttft_ms, status, cost_usd, cache_status, route_decision (jsonb), tags (jsonb), trace_id, task_id, error (nullable) |
| `request_payloads` | request_id, prompt (encrypted/optional), response (encrypted/optional) - **off by default**, see section 15 |
| `prices` | provider, model, input_per_mtok, output_per_mtok, cached_input_per_mtok, effective_from |
| `cache_entries` | key, project_id, model, params_hash, response, embedding (vector, nullable), created_at, expires_at, hits |
| `eval_sets` / `eval_items` / `eval_runs` | golden examples, judgments, results (Phase 3) |
| `pipelines` / `pipeline_versions` | project_id, config (jsonb), version, created_at (Phase 2+) |
| `segments` / `segment_versions` | name, manifest (jsonb), version (Phase 4+) |

Rules: store API keys only as hashes; never log provider keys; index `requests` on (project_id, ts) and on tags used for grouping.

### 9.5 Cost calculation

```
cost_usd = (prompt_tokens - cached_input_tokens) * input_price
         +  cached_input_tokens * cached_input_price
         +  completion_tokens * output_price
```
- Prices live in a **versioned price table** (`effective_from`), never hard-coded.
- Use provider-reported token counts when available; fall back to a local tokenizer otherwise and flag the row as `estimated`.
- **Acceptance test:** over a test week, our total must match the provider invoice within a small tolerance. Do this check before telling anyone the numbers are right.

### 9.6 Pipeline config (source of truth)

```yaml
# pipeline.yaml
version: 1
project: demo
steps:
  - id: pii
    segment: pii_filter
    params:
      mode: redact            # redact | block
      entities: [email, phone]
  - id: budget
    segment: budget_cap
    params:
      daily_usd: 25
      on_exceed: block        # block | downgrade_model
  - id: cache
    segment: cache_exact
    params:
      ttl_seconds: 86400
      only_if_temperature_zero: true
  - id: route
    segment: router_rules
    params:
      rules:
        - when: { max_prompt_tokens: 400, tag: "feature=autocomplete" }
          use_model: small-model
      default_model: large-model
  - id: fallback
    segment: fallback
    params:
      on_error: [provider_timeout, rate_limit]
      chain: [large-model, backup-model]
```

### 9.7 Segment manifest (the reusable block format)

```yaml
# segments/cache_exact/manifest.yaml
name: cache_exact
version: 0.1.0
stage: pre                   # pre | core | post
description: Return a stored response for identical requests.
params:
  ttl_seconds:
    type: integer
    default: 86400
    min: 60
  only_if_temperature_zero:
    type: boolean
    default: true
inputs: [request]
outputs: [response?]         # optional: may short-circuit
metrics: [cache_hit, cache_miss, tokens_saved, usd_saved]
tests:
  - tests/test_cache_exact.py
safety:
  never_cache_when: [tools_present, user_specific_marker]
```

Rules: every segment has typed params with defaults and limits, declares its stage, emits named metrics, and **ships tests**. This format is what Phase 4 renders as draggable blocks and Phase 6 extends to adapt to external projects.

---

## 10. Components in detail

### 10.1 Gateway and providers
- OpenAI-compatible in; provider adapters translate to each provider's API and back.
- Support streaming, timeouts, retries with backoff, and clean error mapping to OpenAI-style errors.
- Adapter interface (sketch): `complete(request) -> Response`, `stream(request) -> AsyncIterator[Chunk]`, `usage(response) -> Usage`.

### 10.2 Logging and metrics
- Write request rows via an async queue (batch inserts). Never block the response.
- Attribution comes from tags header + project; store tags as jsonb.
- Prompt/response bodies are not stored by default (privacy); a project may opt in.

### 10.3 Dashboard (MVP)
- Spend over time; spend by model, tag, endpoint.
- Top 20 most expensive requests; latency percentiles (p50/p95); error rate.
- Request detail view (metadata; payload only if opted in).
- Auth: simple admin login for self-hosted; real orgs/roles in Phase 5.

### 10.4 Caching (Phase 2)
- **Exact cache:** key = hash(model + messages + params). Redis with TTL.
- **Provider prompt caching:** help users structure prompts with stable prefixes so provider-side caching applies; show it in the dashboard.
- **Semantic cache:** embed the prompt, search pgvector, return a hit only above a similarity threshold. Start conservative; tune with the eval harness.
- Safety defaults: cache only low-randomness requests; never cache requests with tools or user-specific content unless the project opts in; key includes system prompt hash and params; per-route on/off switch.
- **Shadow mode:** compute and log "would have hit the cache / would have saved $X" without serving it.
- Dashboard shows `usd_saved` versus baseline with the baseline clearly stated.

### 10.5 Routing (Phase 3)
1. **Rules router:** route by tags, prompt length, task type, user tier.
2. **Learned router:** predict whether a cheap model is good enough for a given prompt (strong-vs-weak), trained on labeled outcomes from the eval harness.
3. **Quality floor:** user sets the minimum acceptable quality; the router must stay above it, otherwise it uses the strong model.
4. **Fallbacks:** retry on errors/timeouts across a model chain.
5. **Shadow mode first:** log routing decisions without applying them; apply gradually (e.g. 5% -> 25% -> 100%).
6. **Experiments:** output-length-aware routing (quality can vary with expected output length).

### 10.6 Evaluation harness (Phase 3, the key differentiator)
- **Golden set:** user supplies examples (input + ideal output or rubric); we also help sample from real traffic.
- **Judging:** pairwise comparison of cheap-model output vs strong-model output using an LLM judge with position-swapping (to reduce bias), plus periodic human spot-checks on a sample.
- **Signals from production:** thumbs up/down, regenerate/retry rate, downstream success events.
- **Report:** win/tie/loss rate versus the strong model, with confidence intervals, per task type.
- **Acceptance rule (set in Phase 3):** a route is allowed only if its measured quality is within an agreed tolerance of the strong model on that workload.
- Keep every benchmark reproducible in `benchmarks/` (data, script, results, date, model versions).

### 10.7 Budgets and guardrails (Phase 2-5)
- Per project / per tag / per task budgets with actions: alert, block, or downgrade model.
- PII filter segment (redact or block configured entities).
- Rate limits per key.

### 10.8 Agent cost-per-task (Phase 5)
- Group requests by `task_id` / `trace_id` into runs.
- Report cost, call count and duration per task; flag loops (repeated near-identical calls), runaway tasks, and idle/duplicate workloads.
- Per-task budgets (stop a run that exceeds its cap).

### 10.9 Visual pipeline builder (Phase 4)
- Node-graph UI (React Flow) that reads/writes `pipeline.yaml`.
- Palette of segments generated from their manifests; param forms auto-generated from the typed params.
- Validate before deploy (types, ordering by stage, required params); preview what changes; version and roll back.
- Per-segment test runner and a "dry run" on sample requests.

---

## 11. Phase plan, deliverables and exit gates

Dates are targets; expect up to 1.5x slippage and plan slower weeks around exams. Today is 3 Nov 2026.

| Phase | Target window | Deliverable | Exit gate |
|---|---|---|---|
| 0. Validate + set up | Nov 2026 (2-3 weeks) | Interview notes, problem statement, stack and repo, roles, project skeleton | 10+ interviews done, 1-page problem statement, 5 people willing to try an early version |
| 1. MVP gateway + dashboard | Dec 2026 - Jan 2027 | Section 5 MVP, Docker one-liner, README quickstart | Stable 2 weeks on our own app; 3 outside users send real traffic |
| 2. Caching + savings | Feb - Mar 2027 | Exact + semantic cache, shadow mode, savings card | 3 users with measured savings; first public write-up |
| 3. Routing + evaluation | Mar - Jun 2027 | Rules + learned router, fallbacks, eval harness, quality floor | Cost down at held quality on 2 real workloads; published benchmark |
| 4. Visual pipeline + segments v1 | mid 2027 - late 2027 | Pipeline builder, segment manifest v1, 8-10 segments | Users deploy a pipeline without hand-editing files |
| 5. Agents + hosted cloud | late 2027 - early 2028 | Cost per task, budgets, multi-tenant hosting, billing | First paying customers |
| 6. Editor + adaptation | 2028 | Monaco editor, code/visual sync, codebase-aware segments | Adaptation passes tests at a target set in advance |
| 7. Scale | 2028+ | Team, enterprise, marketplace, funding | Repeatable growth |

**Ambitious-but-possible compression (stretch goals):** working MVP with early users by December 2026, caching plus first routing and a benchmark by about April-May 2027. Everything later is the longer-term vision.

**Kill-or-pivot reviews:** end of Phase 1 (did outsiders use it?), end of Phase 3 (are people saving money and trusting quality checks?), end of Phase 5 (will anyone pay?).

### Phase 1 task breakdown (start here)
1. Repo, tooling, CI, Docker Compose with Postgres + Redis.
2. Project + API key model, auth middleware.
3. `/v1/chat/completions` non-streaming for one provider; then streaming.
4. Provider adapter interface; add a second provider.
5. Price table + cost calculator + tests against sample invoices.
6. Async request logging into Postgres.
7. Admin API endpoints for usage/requests.
8. Dashboard: login, spend charts, expensive requests table.
9. Load test (basic) and error-handling pass; docs and quickstart.
10. Dogfood on our own test app for 2 weeks; fix; invite first outside users.

---

## 12. Editor and adaptive segments (Phase 6 design sketch)

This is the research-heavy part. Plan it, but do not build it before Phase 6.

**Goal:** drag a segment into a user's real project and have it fit.

**Adaptation pipeline**
1. **Project scanner:** detect language, framework, folder layout, naming style, existing middleware/routes/config, dependencies (using tree-sitter and manifest files).
2. **Deterministic slot filling:** segment templates have typed slots (auth type, DB, rate limit...). Fill from scanner results and user choices.
3. **Structural edits:** apply code transforms (LibCST for Python, ts-morph/jscodeshift for TypeScript) to insert/modify code in the right files.
4. **LLM-assisted gaps:** use an LLM only where deterministic steps cannot decide; constrain output to the slot schema and validate it.
5. **Verification:** run the segment's bundled tests, type checks and linters on the result.
6. **Diff preview:** show a diff; the user approves. Output is **plain code the user owns** (generate-then-own, no black-box runtime).
7. **Two-way sync:** edits in the code view reflect in the visual view and vice versa, where the segment's structure allows.

**Scoping rules**
- Start with **one stack** (e.g. FastAPI, or Express) and LLM-related segments first.
- Add non-LLM segments (auth middleware, routes, rate limiting) only after LLM segments work well.
- Build our own benchmark suite of sample projects and track "adaptation success rate" (tests pass after insertion). Set the target before building, not after.

---

## 13. Local development setup (target experience)

```bash
git clone <repo-url> morphkit && cd morphkit
cp .env.example .env            # add provider API keys + DB creds
docker compose up -d            # postgres, redis, gateway, dashboard
# gateway:   http://localhost:8080
# dashboard: http://localhost:3000

# point any OpenAI-compatible client at the gateway:
curl http://localhost:8080/v1/chat/completions \
  -H "Authorization: Bearer $MORPHKIT_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"<model-name>","messages":[{"role":"user","content":"hello"}]}'
```

Environment variables (initial): `DATABASE_URL`, `REDIS_URL`, `ENCRYPTION_KEY`, `ADMIN_PASSWORD`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `LOG_PAYLOADS=false`.

Local testing without spending money: use a **mock provider** (returns canned responses with fake token counts) and small open-weight models; keep a cached fixtures set for evaluation development.

## 14. Testing and quality

- Unit tests for every segment, cost calculation and provider adapter (pytest).
- Contract tests: our `/v1/chat/completions` against the official OpenAI client libraries, including streaming.
- Integration tests with Docker Compose (Postgres + Redis + mock provider).
- Cost accuracy test against real invoices (see 9.5).
- Load test for latency overhead: the gateway should add minimal latency; measure and publish p50/p95.
- CI on every PR: ruff, mypy, pytest, dashboard lint + tests. No merge on red.
- Benchmarks reproducible and versioned (`benchmarks/`).

## 15. Security and privacy (design in from day one)

- Store only hashed Morphkit API keys; encrypt provider keys at rest; never log secrets.
- **Do not store prompts/responses by default.** If a project opts in, encrypt them, set retention limits, and allow deletion.
- Sanitize logs; strict input validation; per-key rate limits.
- Dependency hygiene: pin versions, review new releases before upgrading (supply-chain risk is real for gateway software), enable automated dependency alerts.
- Multi-tenant isolation, audit logs, and role-based access are required before hosting other people's data (Phase 5).
- Write a short, honest privacy statement before the first outside user.

## 16. Working agreement (two people)

- **Suggested split (adjust to strengths):** main builder - gateway, routing, evaluation, architecture. Co-builder - dashboard UI, documentation, user outreach and demos.
- Weekly 1-hour sync; monthly 1-hour review (plan vs reality); decisions recorded as short ADRs in `docs/`.
- Decide in Phase 0: who has final say on what, how disagreements are settled, how to add or part with a member, and how ownership/equity is split. Write it down.
- Work rule: **one phase at a time.** No later-phase work until the current exit gate is met. The editor stays parked until Phase 6.
- Protect the pace: sustainable hours, lighter exam weeks.

## 17. Validation plan (Phase 0)

- 10-15 conversations with people running LLM features in production.
- Ask: monthly LLM spend, how they track it, what they have tried to reduce it, what stops them from using caching/routing, what they would pay for.
- Record answers in a shared sheet; summarize the top three pains in the one-page problem statement.
- Ship early and get a handful of real users; their feedback beats guessing.

## 18. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Crowded market of gateways/routers | Compete on quality-proven savings, agent cost-per-task, and the visual/testable segment system, not on "a gateway" |
| Provider prices keep falling | Sell visibility and control, not savings alone; track prices automatically |
| Serving a wrong cached/routed answer | Conservative defaults, shadow mode, opt-in per route, quality floor, easy fallback to the strong model |
| Wrong cost numbers destroy trust | Versioned prices; reconcile against invoices; flag estimated tokens |
| Scope creep from the editor idea | Phase gates; editor only in Phase 6 |
| Two-person team strain | Written agreement, regular syncs |
| Burnout alongside college | Part-time pace, planned slow weeks, monthly review |
| Building without customers | Interviews in Phase 0; user checkpoint at the end of every phase |

## 19. Naming and legal checklist (do before any public launch)

- [ ] Search domains (.com, .dev, .io) for "morphkit"
- [ ] Check the GitHub organization/user name
- [ ] Check package names on npm and PyPI
- [ ] Search the Indian trademark database and general web for conflicts in software/IT classes
- [ ] Decide on company registration timing and structure (consult a qualified professional)
- [ ] Choose an open-source license for the core (decide deliberately; it affects the business model)

## 20. Glossary

- **LLM gateway / proxy:** a service between an app and LLM providers that can log, cache, route and control requests.
- **Segment:** a reusable, typed, tested building block (cache, budget cap, router...) with a manifest.
- **Pipeline:** an ordered list of segments applied to every request.
- **Semantic cache:** returns a stored answer for a *similar* (not identical) prompt, using embeddings.
- **Routing:** choosing which model handles each request; **strong-vs-weak routing** sends easy requests to a cheaper model.
- **Shadow mode:** measuring what an optimization *would* do without applying it.
- **Quality floor:** the minimum quality the user will accept from any cost-saving route.
- **Cost per task:** total cost of all model calls needed to finish one agent task.
- **ADR:** architecture decision record, a short note explaining a decision and why.

## 21. Open decisions (resolve in Phase 0-1)

1. Build the provider layer ourselves or use an existing open-source library under a thin adapter?
2. Open-source license and what stays proprietary (for example hosted features).
3. First two providers to support.
4. Whether the semantic cache starts in Phase 2 with pgvector only, or needs a dedicated vector store.
5. First target user group (indie devs vs. small startups vs. student teams) based on interview results.
6. Final name confirmation after the conflict checks in section 19.
