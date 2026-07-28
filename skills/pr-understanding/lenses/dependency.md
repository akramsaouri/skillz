# Lens: Dependency bump

Fires when only manifests + lockfiles change (`package.json`, `Podfile`, `go.mod`,
`Cargo.toml`, `*.gradle`, `Package.swift`) — version numbers, no app logic. The diff
is boring and **that is the trap**: the risk is entirely in code you did NOT write and
is NOT in the diff. The blast radius is the **changelog**, not the repo.

## Do NOT read the lockfile

A lockfile diff is hundreds of lines of transitive churn — pure noise. List it under
"Ignore". Read the **manifest** for what actually changed: which package, from → to,
and is it a **major / minor / patch** bump (semver tells you the risk tier).

## The real work: fetch the changelog / release notes

For each bumped package (focus on non-patch bumps and anything in the hot path):
- `gh release view` / the repo's `CHANGELOG.md` / `npm view <pkg> versions`, or fetch
  the releases page. Read the entries **between** old and new version.
- Extract **BREAKING CHANGES**, removed/renamed APIs, changed defaults, min-runtime
  bumps (Node/Xcode/JDK/Swift), and new peer-dependency requirements.
- For a range bump (0.83.2 → 0.83.10) read **every** intermediate release, not just the
  endpoints — a breaking change can land in a middle patch.

## Match breaking changes → our call sites (blast radius)

For each breaking change found, grep the repo for our usage of the affected API and
report `file:line` hits. "The changelog says `X` was removed in v5 — we call `X` at
`a.ts:12`, `b.ts:88`" is the single most valuable output of this lens.

## Native / build implications

- RN/iOS/Android: does the bump need a **native rebuild** (`pod install`,
  `./gradlew clean`, new Xcode)? Is the lockfile (`Podfile.lock`) updated to match, or
  will CI drift?
- New **min OS / runtime** version? Transitive **native** dep added?
- Any **postinstall script** newly introduced (supply-chain surface)?

## Diagram

**Usually none.** A dependency bump has no changed flow. Skip it unless the new version
changes an API contract we consume, in which case a tiny before/after of that one call.

## Standing checks (dependency)

- Manifest and lockfile both updated and consistent (no drift)?
- Any listed breaking change hits a repo call site? (list them)
- Native rebuild required and reflected (Podfile.lock / Gradle)?
- Min runtime / peer-dep requirement still satisfied by our toolchain/CI?
- Is this a security patch (then prioritize) or a feature bump (then justify)?

## Verify these (dependency)

- "The v0.83.x notes list `<breaking change>` — verify our usage at `file:line` is
  compatible or updated."
- "Bump requires a native rebuild — verify `Podfile.lock` reflects it (`file:line`)
  so CI and local don't drift."
- "Range bump 0.83.2→0.83.10 — did you read the intermediate releases, or only the
  endpoints? A break can hide in 0.83.6."
