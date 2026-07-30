# Lens: Dependency bump

Fires when only manifests + lockfiles change — version numbers, no app logic:
`package.json`, `Podfile`, `go.mod`, `Cargo.toml`, `*.gradle`, `Package.swift`,
`pyproject.toml`/`requirements.txt`, `Gemfile`, `composer.json`, `pubspec.yaml`,
`mix.exs`, `*.csproj`. The diff is boring and **that is the trap**: the risk is entirely
in code you did NOT write and is NOT in the diff. The blast radius is the **changelog**,
not the repo.

## Do NOT read the lockfile

A lockfile diff is hundreds of lines of transitive churn — pure noise. List it under
"Ignore" (`package-lock.json`, `pnpm-lock.yaml`, `yarn.lock`, `Podfile.lock`, `go.sum`,
`Cargo.lock`, `Package.resolved`, `poetry.lock`, `uv.lock`, `Gemfile.lock`,
`composer.lock`, `pubspec.lock`, `mix.lock`). Read the **manifest** for what actually
changed: which package, from → to, and is it a **major / minor / patch** bump.

**Two caveats on semver.** Pre-1.0 (`0.x`), a *minor* bump is the breaking one — 0.x
gives no stability promise. And Go, Python, and Ruby libraries frequently break in
patch releases regardless of what semver says. Read the notes even for a patch in the
hot path.

**Do scan the lockfile for one thing:** transitive packages that appeared or jumped a
major, especially anything you don't recognize. That's where a supply-chain surprise
enters, and the manifest won't show it.

## The real work: fetch the changelog / release notes

For each bumped package (focus on non-patch bumps and anything in the hot path):
- `gh release view` / the repo's `CHANGELOG.md`, or fetch the releases page. Read the
  entries **between** old and new version. Registry metadata by ecosystem:
  `npm view <pkg> versions`, `pip index versions <pkg>`, `gem list -ra <pkg>`,
  `go list -m -versions <mod>`, `cargo search`/docs.rs, `composer show -a <pkg>`.
- Extract **BREAKING CHANGES**, removed/renamed APIs, changed defaults, min-runtime
  bumps (Node/Python/Ruby/Go/Xcode/JDK/Swift/.NET), and new peer-dependency
  requirements.
- For a range bump (0.83.2 → 0.83.10) read **every** intermediate release, not just the
  endpoints — a breaking change can land in a middle patch.

## Match breaking changes → our call sites (blast radius)

For each breaking change found, grep the repo for our usage of the affected API and
report `file:line` hits. "The changelog says `X` was removed in v5 — we call `X` at
`a.ts:12`, `b.ts:88`" is the single most valuable output of this lens.

## Toolchain / build implications

- **Does the bump need a rebuild or regeneration step the PR didn't run?** RN/iOS/
  Android: `pod install`, `./gradlew clean`, a new Xcode. Python: a wheel that now
  compiles from source. Go: `go mod tidy` (is `go.sum` complete?). Rust: an MSRV bump.
  Java/Kotlin: a Gradle plugin or JDK target bump. If the manifest moved but the
  lockfile didn't (or vice versa), CI and local will drift — flag it.
- **New min runtime / language version?** Check it against what CI, Docker base images,
  and the deploy target actually run — a bump that needs Node 22 or Python 3.12 fails
  at deploy, not in review.
- **New install-time script** (`postinstall`, `setup.py`, `build.rs`, Gradle plugin)?
  That's arbitrary code on every developer machine and CI runner — supply-chain surface.
- **Package identity**: did the package get renamed, change owner/namespace, or is this
  a fork swapped in at the same import path? Rare, but the highest-severity finding here.

## Diagram

**Usually none.** A dependency bump has no changed flow. Skip it unless the new version
changes an API contract we consume, in which case a tiny before/after of that one call.

## Standing checks (dependency)

- Manifest and lockfile both updated and consistent (no drift)?
- Any listed breaking change hits a repo call site? (list them)
- Rebuild/regeneration step required and reflected in the lockfile?
- Min runtime / peer-dep requirement still satisfied by CI, Docker base, and deploy target?
- New install-time script or changed package ownership?
- Is this a security patch (then prioritize) or a feature bump (then justify)?

## Verify these (dependency)

- "The v0.83.x notes list `<breaking change>` — verify our usage at `file:line` is
  compatible or updated."
- "Bump requires a rebuild/regen step — verify the lockfile at `file:line` reflects it
  (`Podfile.lock`, `go.sum`, `poetry.lock`…) so CI and local don't drift."
- "Bump raises the min runtime to `X` — verify CI matrix, Dockerfile, and the deploy
  target all run at least `X`."
- "Range bump 0.83.2→0.83.10 — did you read the intermediate releases, or only the
  endpoints? A break can hide in 0.83.6."
