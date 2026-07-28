# Lens: Config / CI / infra

Fires on `.github/`, CI yaml, Dockerfiles, env/secrets, build config, `*.toml`/`*.yaml`
infra. These PRs look trivial and ship rarely-tested paths — a broken workflow or a
leaked secret isn't caught by app tests. The blast radius is **the pipeline and the
runtime environment**, not the app code.

## Read for these

- **Secrets & exposure.** Any secret/token/key moved into a place it can leak: echoed
  in a step, written to logs, passed as a build-arg (baked into image layers),
  interpolated into a `run:` block where it prints, or committed as a literal instead
  of a `secrets.*` reference? **A newly logged secret is the #1 finding here.**
- **`pull_request_target` / permissions.** In GitHub Actions, `pull_request_target`
  runs with repo secrets against **untrusted PR code** — a classic exfiltration hole.
  Check `permissions:` is least-privilege (not blanket `write-all`).
- **Env var changes.** New required env var — is it documented, defaulted, and set in
  every environment (local `.env.example`, CI, prod)? A new required var missing in one
  env breaks that env silently. Renamed var — all readers updated?
- **Trigger / matrix changes.** Did the workflow trigger change (e.g. now runs on every
  push vs PR)? Matrix change drop a platform/version that was providing coverage?
- **Pinning / supply chain.** Actions pinned to a SHA or a floating `@v3`/`@main`
  (mutable — supply-chain risk)? Base image pinned to a digest or a floating tag?
- **Caching & concurrency.** Cache key correctness (stale cache poisoning), and
  `concurrency:` to cancel superseded runs.
- **Cost / time.** Did a change make CI run much more (matrix blow-up, lost cache,
  removed path filter)?

## Blast radius

- Which env consumes the changed var/secret (grep app code + other workflows)?
- Does another workflow depend on this one (reusable workflow, artifact handoff)?
- Does a Dockerfile change alter the runtime the app assumes (base image, installed
  libs, user, workdir)?

## Diagram

Usually none. For a multi-job pipeline change, a small **flowchart of the job graph**
(triggers → jobs → dependencies) before/after can be worth it. Otherwise skip.

## Standing checks (config)

- No secret echoed, logged, or baked into an image layer / build-arg?
- Actions & base images pinned (SHA/digest), not floating tags?
- `pull_request_target` (if any) not running untrusted code with secrets;
  `permissions:` least-privilege?
- New/renamed env var set + documented across ALL environments?
- No accidental trigger widening or lost coverage in a matrix change?

## Verify these (config)

- "Step at `file:line` — verify the secret isn't printed to logs or passed where it's
  echoed."
- "New env var `X` at `file:line` — verify it's set in prod + CI + `.env.example`, not
  just locally."
- "Action `@v3` at `file:line` — verify it's pinned to a SHA; a floating tag is a
  supply-chain risk."
