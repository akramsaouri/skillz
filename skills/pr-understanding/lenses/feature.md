# Lens: Feature / new flow

Fires on new screens/routes/endpoints/files that introduce behavior. This is the
**heavyweight** treatment — usually Deep lane. The full blast-radius fan-out, old-vs-new
architecture diagram, and the widest verify list all apply. The lens adds the questions
specific to *new* code paths.

## What new code needs that changed code doesn't

- **Every state of the new flow.** Loading, empty, error, success, offline, permission-
  denied. A feature PR that only handles the happy path is the most common gap — list
  which states are handled (`file:line`) and which are **missing**.
- **Entry & exit.** How is the new flow reached (route, button, deep link) and how is
  it left (back, cancel, completion)? Is there a dead end — a screen you can enter but
  not leave, or navigation that doesn't reset?
- **New external calls.** Every new network/DB/RPC call: timeout? error path? retry?
  loading indicator? What happens on failure — silent, toast, blocking?
- **New state / data ownership.** Where does the new state live (local, store, server)?
  Who invalidates it? Any stale-cache risk?
- **Auth / gating.** Is the new screen/endpoint behind the right auth? Can an
  unauthorized user reach it by deep link or direct call?
- **Analytics / feature flag.** Is the feature behind a flag (safe rollout) or shipped
  hot? Are the expected events instrumented (if the repo has that convention)?

**If the new surface is a UI flow**, the states above are the whole game. **If it's an
API, endpoint, job, or consumer**, swap in these:
- **Input validation at the boundary** — is the request body/params parsed by a schema
  (zod, pydantic, serializer, struct tags), or trusted? Is authorization checked per
  *resource*, not just "is logged in"? (IDOR: can I pass someone else's id?)
- **Idempotency & retries** — can this be called twice (client retry, at-least-once
  queue) without double-charging or duplicating a row? Is there an idempotency key or a
  unique constraint backing it?
- **Unbounded work** — a list endpoint without pagination or a cap, a query without a
  `LIMIT`, an N+1 across the new relation, an unbounded fan-out to a downstream service.
- **Failure semantics** — is the write transactional across all the rows it touches?
  What's left behind if the process dies halfway? Is a background job's failure visible
  (dead-letter, alert) or silent?
- **Rate limiting & cost** — is the new endpoint rate-limited, and does it call a paid
  or slow third party per request?

## Blast radius (full fan-out)

All four Deep-lane subagents. Plus feature-specific:
- Does the new flow **reuse** existing components/hooks/utils, or **duplicate** logic
  that already exists? (Point to the existing one — duplication is debt.)
- Does it register routes/deep links/notification handlers that need to be added
  elsewhere (a central navigator, an intent filter)?

## Diagram

**Lead with architecture** — a component/boundary flowchart of the new flow: entry →
screens → data sources → exit, marking which nodes are new vs existing. Then, if a
request/RPC path carries the risk, a **sequenceDiagram** of the new call. When it
modifies an existing flow, show **old vs new**.

## Standing checks (feature)

- (UI) All states handled (loading/empty/error/success/offline)? Which are missing?
- Every new external call has a timeout + error path?
- New screen/endpoint behind correct auth — including deep-link reachability and
  per-resource ownership, not just "authenticated"?
- (API) Input validated at the boundary; the write idempotent under retry?
- (API) Nothing unbounded — pagination, `LIMIT`, no N+1 on the new relation?
- New logic reuses existing utils rather than duplicating?
- Behind a feature flag, or justified to ship hot?
- (repo convention) Analytics events instrumented?

## Verify these (feature)

- "The new flow handles success at `file:line` — verify the **error** path exists;
  which state renders when the call at `file:line` throws?"
- "New endpoint `file:line` — verify auth gating; can a deep link reach it unauthed?"
- "`file:line` looks up the record by an id from the request — verify it also checks the
  caller *owns* it, or any authenticated user can pass someone else's id."
- "The write at `file:line` isn't idempotent — verify a client retry or queue redelivery
  can't create a second row / second charge."
- "Claims this is net-new — verify `X` at `file:line` isn't duplicating the existing
  `Y` at `file:line`."
