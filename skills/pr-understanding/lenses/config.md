# Lens: Config / CI / infra

Fires on CI/CD config (`.github/workflows`, `.gitlab-ci.yml`, `.circleci`,
`.buildkite`, `Jenkinsfile`), Dockerfiles and Compose files, infra-as-code (Terraform,
Pulumi, CloudFormation, Helm charts, k8s manifests), env/secrets, and build config
(`*.toml`/`*.yaml`, `vite.config`, `webpack`, `tsconfig`, Gradle, `Makefile`). These PRs
look trivial and ship rarely-tested paths — a broken workflow or a leaked secret isn't
caught by app tests. The blast radius is **the pipeline and the runtime environment**,
not the app code.

## Read for these

- **Secrets & exposure.** Any secret/token/key moved into a place it can leak: echoed
  in a step, written to logs, passed as a build-arg (baked into image layers),
  interpolated into a `run:` block where it prints, or committed as a literal instead
  of a `secrets.*` reference? **A newly logged secret is the #1 finding here.**
- **Untrusted code running with secrets.** The classic exfiltration hole, by provider:
  GitHub Actions `pull_request_target` (runs with repo secrets against **fork PR code**)
  and `permissions:` set to blanket `write-all`; GitLab CI secrets not marked
  *Protected* so they reach fork/branch pipelines; CircleCI "pass secrets to forked
  PRs". Also: does any step interpolate an attacker-controlled value —
  `${{ github.event.pull_request.title }}`, a branch name — straight into a `run:`
  block? That's shell injection into a privileged runner.
- **Infra-as-code blast radius.** For Terraform/Helm/k8s: does the change
  **replace** rather than update a resource (a rename usually means destroy+create),
  widen a security group / IAM policy / bucket ACL, or drop a `prevent_destroy`?
  Is there a plan output in the PR to read, or are you guessing?
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
- Third-party actions & base images pinned (SHA/digest), not floating tags?
- No untrusted code (fork PR) running with secrets; job permissions least-privilege?
- No attacker-controlled value interpolated into a shell step?
- New/renamed env var set + documented across ALL environments?
- No accidental trigger widening or lost coverage in a matrix change?
- (IaC) No resource replacement or widened IAM/network rule hiding in the plan?

## Verify these (config)

- "Step at `file:line` — verify the secret isn't printed to logs or passed where it's
  echoed."
- "New env var `X` at `file:line` — verify it's set in prod + CI + `.env.example`, not
  just locally."
- "Action `@v3` at `file:line` — verify it's pinned to a SHA; a floating tag is a
  supply-chain risk."
