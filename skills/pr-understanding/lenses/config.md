# Lens: Config / CI / infra

Fires on CI/CD config (`.github/workflows`, `.gitlab-ci.yml`, `.circleci`,
`.buildkite`, `Jenkinsfile`), Dockerfiles and Compose files, infra-as-code (Terraform,
Pulumi, CloudFormation, Helm charts, k8s manifests), env/secrets, and build config
(`*.toml`/`*.yaml`, `vite.config`, `webpack`, `tsconfig`, Gradle, `Makefile`). These PRs
look trivial and ship rarely-tested paths — a broken workflow or a leaked secret isn't
caught by app tests. The blast radius is **the pipeline and the runtime environment**,
not the app code.

## Read for these

The report is a map of the pipeline and the runtime **after** this change — what runs,
where, with what credentials. State each as a fact at a `file:line`.

- **Where secrets now flow.** Every secret/token/key the change touches, and where it
  ends up: a `secrets.*` reference, echoed in a step, written to logs, passed as a
  build-arg (baked into image layers), interpolated into a `run:` block that prints it,
  or committed as a literal. Say which.
- **What the triggers admit, and with what.** `pull_request_target` runs **fork PR
  code** with repo secrets; `permissions: write-all` hands the token everything; GitLab
  CI secrets not marked *Protected* reach fork/branch pipelines; CircleCI has a "pass
  secrets to forked PRs" toggle. Say which combination this config now has. Same for
  interpolation: if a step drops `${{ github.event.pull_request.title }}` or a branch
  name into a `run:` block, that value reaches the runner's shell — say so.
- **Infra-as-code reach.** For Terraform/Helm/k8s: does the change **replace** rather
  than update a resource (a rename usually means destroy+create), change a security
  group / IAM policy / bucket ACL, or remove a `prevent_destroy`? Is there a plan output
  in the PR to read, or are you inferring? Say which you did.
- **Env var changes.** For a new required var, name every place it is set (local
  `.env.example`, CI, prod) *and* every place it isn't — that list is the blast radius.
  For a renamed var, which readers the diff updated.
- **Trigger / matrix changes.** What the workflow now runs on (every push vs PR), and
  what the matrix covers now versus before — name the platforms/versions that entered or
  left the set.
- **Pinning.** Actions and base images pinned to a SHA/digest, or a floating
  `@v3`/`@main`/`:latest` — a floating ref means the code that runs can change without
  a diff. Say which each one is.
- **Caching & concurrency.** What the cache key covers now, and whether `concurrency:`
  cancels superseded runs.
- **Cost / time.** How much more (or less) CI runs after this: matrix size, cache hits,
  path filters.

## Blast radius

- Which env consumes the changed var/secret (grep app code + other workflows)?
- Does another workflow depend on this one (reusable workflow, artifact handoff)?
- Does a Dockerfile change alter the runtime the app assumes (base image, installed
  libs, user, workdir)?

## Diagram

Usually none. For a multi-job pipeline change, a **`.rail`** of the job order before and
after earns its place — one row per job, `is-new` on jobs the change adds, `is-gone` on
ones it drops, and the reader can see at a glance whether the gate they rely on still
runs. If the pipeline is better read as stages, a **`.layers`** works too: one `.layer`
per stage (trigger → build → test → deploy), jobs as `.node` chips, and the artifact or
condition passed downstream as the `.cross` label. Reach for Mermaid only if a job graph
genuinely fans out — one job feeding 3+ others *and* fed by 3+. Otherwise skip. Markup
contract in Step 6.

## Verify these (config)

- "Step at `file:line` — verify the secret isn't printed to logs or passed where it's
  echoed."
- "New env var `X` at `file:line` — verify it's set in prod + CI + `.env.example`, not
  just locally."
- "Action `@v3` at `file:line` is a floating tag, not a SHA — verify you want the code
  it runs to be able to change without a diff here."
