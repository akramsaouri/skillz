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

- All states handled (loading/empty/error/success/offline)? Which are missing?
- Every new external call has a timeout + error path?
- New screen/endpoint behind correct auth (incl. deep-link reachability)?
- New logic reuses existing utils rather than duplicating?
- Behind a feature flag, or justified to ship hot?
- (repo convention) Analytics events instrumented?

## Verify these (feature)

- "The new flow handles success at `file:line` — verify the **error** path exists;
  which state renders when the call at `file:line` throws?"
- "New endpoint `file:line` — verify auth gating; can a deep link reach it unauthed?"
- "Claims this is net-new — verify `X` at `file:line` isn't duplicating the existing
  `Y` at `file:line`."
