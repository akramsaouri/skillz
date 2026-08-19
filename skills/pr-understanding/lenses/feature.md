# Lens: Feature / new flow

Fires on new screens/routes/endpoints/files that introduce behavior. This is the
**heavyweight** treatment — usually Deep lane. The full blast-radius fan-out, old-vs-new
architecture diagram, and the widest verify list all apply. The lens adds the questions
specific to *new* code paths.

## What new code needs mapping that changed code doesn't

New code has no "before" to diff against, so the map is an **inventory of the new
surface**. Enumerate it; the enumeration itself shows the reader what is and isn't there.

- **Every state of the new flow.** Loading, empty, error, success, offline, permission-
  denied — list the ones it renders and cite each (`file:line`). A list of three where
  the reader expected six tells them more than any adjective would.
- **Entry & exit.** How the new flow is reached (route, button, deep link) and how it is
  left (back, cancel, completion). Name every door in and every door out.
- **New external calls.** Every new network/DB/RPC call, and what the code does around
  it: timeout, retry, loading indicator, and what the user sees on failure — silent,
  toast, blocking.
- **New state / data ownership.** Where the new state lives (local, store, server), and
  what invalidates it.
- **Auth / gating.** What gates the new screen/endpoint, cited — and which of the entry
  points above that gate actually sits behind.
- **Analytics / feature flag.** Is the feature behind a flag or shipped hot? Which events
  it instruments (if the repo has that convention).

**If the new surface is a UI flow**, the states above are the whole game. **If it's an
API, endpoint, job, or consumer**, swap in these:
- **Boundary handling** — is the request body/params parsed by a schema (zod, pydantic,
  serializer, struct tags) or read straight off the request? Where authorization is
  checked, is it per *resource* or per session? Say which; both are real designs.
- **Call-twice semantics** — what happens on a client retry or an at-least-once
  redelivery: is there an idempotency key or unique constraint, or does it write again?
- **Bounds** — pagination or a cap on the new list endpoint, a `LIMIT` on the new query,
  the number of round-trips across the new relation, the fan-out to downstream services.
- **Failure semantics** — is the write transactional across the rows it touches, what is
  left behind if the process dies halfway, and where a background job's failure surfaces
  (dead-letter, alert, nowhere).
- **Rate limiting & cost** — what the new endpoint calls per request (paid or slow third
  parties), and whether it is rate-limited.

## Blast radius (full fan-out)

All four Deep-lane subagents. Plus feature-specific:
- Does the new flow **reuse** existing components/hooks/utils, or **reimplement** logic
  that already exists somewhere? Point to both, with `file:line` — two implementations
  of the same thing is a fact about the codebase the reader should know it now has.
- Does it register routes/deep links/notification handlers that reach into shared
  registries elsewhere (a central navigator, an intent filter)?

## Diagram

**Lead with architecture** — a **`.layers`** stack of the new flow: one `.layer` per
boundary (entry → screen → state → data source), the components as `.node` chips with
`is-new` on the ones this PR introduces, and what crosses between bands — the prop, the
payload, the row shape — on the `.cross` row. The `is-new` chips are the point: they show
how much of the flow is genuinely new versus wired out of parts that already existed.

Then, if a request/RPC path carries the weight, a **`.ladder`** of the new call, with the
response hop marked `is-return`. When the feature **modifies an existing flow** rather
than adding one, a **`.rail`** of old against new says it faster than either. Markup
contract in Step 6.

## Verify these (feature)

- "The new flow handles success at `file:line` — verify the **error** path exists;
  which state renders when the call at `file:line` throws?"
- "New endpoint `file:line` — verify auth gating; can a deep link reach it unauthed?"
- "`file:line` looks up the record by an id from the request — verify it also checks the
  caller *owns* it, or any authenticated user can pass someone else's id."
- "The write at `file:line` has no idempotency key or unique constraint behind it —
  verify a client retry or queue redelivery writing twice is acceptable here."
- "Claims this is net-new — verify `X` at `file:line` isn't duplicating the existing
  `Y` at `file:line`."
