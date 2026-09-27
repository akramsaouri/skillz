#!/usr/bin/env python3
"""Card store for the pr-recall skill: the one thing any pr-* skill writes.

  store.py path                                        print the store path (exit 3: none set)
  store.py overlap --repo OWNER/REPO < pr.diff         stored cards the diff touches, as JSON
  store.py upsert --repo OWNER/REPO --pr N < cards.json
                                                       replace that PR's cards, write the store

The store is $PR_RECALL_STORE, else $LUCIDOS_WORKSPACE/data/artifacts/pr-recall/cards.json.
Writes go through `lucidos data write` when that CLI is on PATH and the store sits
inside the workspace's data/ directory; otherwise the file is replaced atomically.
A store that does not parse is never overwritten.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

SCHEMA = "pr-recall/cards/v1"
FIELDS = ("id", "repo", "pr", "head_sha", "merged_at", "files", "symbols", "kind", "fact")
KINDS = ("decision", "invariant", "moved", "gotcha")
MAX_CARDS = 3
MAX_FACT = 140


def fail(msg, code=2):
    print(f"store.py: {msg}", file=sys.stderr)
    sys.exit(code)


def store_path():
    explicit = os.environ.get("PR_RECALL_STORE")
    if explicit:
        return Path(explicit).expanduser()
    workspace = os.environ.get("LUCIDOS_WORKSPACE")
    if workspace:
        return Path(workspace) / "data" / "artifacts" / "pr-recall" / "cards.json"
    return None


def load(path):
    if path is None or not path.exists():
        return []
    try:
        data = json.loads(path.read_text() or "[]")
    except json.JSONDecodeError as e:
        fail(f"{path} is not valid JSON ({e}); fix it by hand, it will not be overwritten")
    cards = data.get("cards") if isinstance(data, dict) else data
    if not isinstance(cards, list):
        fail(f"{path} holds no card list; fix it by hand, it will not be overwritten")
    return cards


def same_repo(a, b):
    return str(a).lower() == str(b).lower()


def parse_diff(text):
    """Return (every path the diff names, old or new; the changed lines plus hunk contexts)."""
    files, changed, in_header = set(), [], False
    for line in text.splitlines():
        if line.startswith("diff --git "):
            in_header = True
            m = re.match(r'diff --git "?a/(.+?)"? "?b/(.+?)"?$', line)
            if m:
                files.update(m.groups())
        elif in_header and line.startswith(("--- ", "+++ ")):
            p = line[4:].rstrip().strip('"')
            if p != "/dev/null":
                files.add(re.sub(r"^[ab]/", "", p))
        elif in_header and line.startswith(("rename from ", "rename to ")):
            files.add(line.split(" ", 2)[2])
        elif line.startswith("@@"):
            in_header = False
            changed.append(line.split("@@", 2)[-1])  # the enclosing function, when git names it
        elif not in_header and line.startswith(("+", "-")):
            changed.append(line[1:])
    return files, "\n".join(changed)


def validate(card):
    problems = []
    missing = [k for k in FIELDS if k not in card]
    unknown = sorted(set(card) - set(FIELDS))
    if missing:
        problems.append(f"missing {', '.join(missing)}")
    if unknown:
        problems.append(f"unknown {', '.join(unknown)}")
    if problems:
        return problems
    if not re.fullmatch(r"[0-9a-f]{40}", str(card["head_sha"])):
        problems.append("head_sha must be the full 40-hex SHA")
    try:
        datetime.fromisoformat(str(card["merged_at"]).replace("Z", "+00:00"))
    except ValueError:
        problems.append("merged_at must be an ISO-8601 timestamp")
    if card["kind"] not in KINDS:
        problems.append(f"kind must be one of {'|'.join(KINDS)}")
    for key in ("files", "symbols"):
        if not isinstance(card[key], list) or not all(isinstance(x, str) and x for x in card[key]):
            problems.append(f"{key} must be a list of non-empty strings")
    if isinstance(card["files"], list) and not card["files"]:
        problems.append("files must name at least one path")
    fact = card["fact"]
    if not isinstance(fact, str) or not fact.strip() or "\n" in fact:
        problems.append("fact must be one non-empty line")
    elif len(fact) > MAX_FACT:
        problems.append(f"fact is {len(fact)} characters; the cap is {MAX_FACT}")
    return problems


def write(path, text):
    workspace = os.environ.get("LUCIDOS_WORKSPACE")
    if workspace and shutil.which("lucidos"):
        try:
            rel = path.resolve().relative_to((Path(workspace) / "data").resolve())
        except ValueError:
            rel = None
        if rel is not None:
            done = subprocess.run(
                ["lucidos", "data", "write", rel.as_posix(), "--from", "-"],
                input=text, text=True, capture_output=True,
            )
            if done.returncode != 0:
                fail(f"lucidos data write failed: {done.stderr.strip()}")
            return "lucidos"
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    tmp.write_text(text)
    os.replace(tmp, path)
    return "file"


def cmd_path(_args):
    path = store_path()
    if path is None:
        fail("no store: set PR_RECALL_STORE (or run inside a Lucidos workspace)", 3)
    print(path)


def cmd_overlap(args):
    files, changed = parse_diff(sys.stdin.read())
    matches = []
    for card in load(store_path()):
        if not same_repo(card.get("repo", ""), args.repo):
            continue
        hit_files = sorted(set(card.get("files", [])) & files)
        hit_symbols = [
            s for s in card.get("symbols", [])
            if s and re.search(rf"(?<![\w$]){re.escape(s)}(?![\w$])", changed)
        ]
        if hit_files or hit_symbols:
            matches.append({"card": card, "via": {"files": hit_files, "symbols": hit_symbols}})
    print(json.dumps(matches, indent=2, ensure_ascii=False))


def cmd_upsert(args):
    try:
        new = json.loads(sys.stdin.read())
    except json.JSONDecodeError as e:
        fail(f"cards on stdin are not valid JSON ({e})")
    if not isinstance(new, list) or len(new) > MAX_CARDS:
        fail(f"expected a JSON list of at most {MAX_CARDS} cards on stdin")
    for i, card in enumerate(new, 1):
        if not isinstance(card, dict):
            fail(f"card {i} is not an object")
        card.update(id=f"{args.repo}#{args.pr}-{i}", repo=args.repo, pr=args.pr)
        problems = validate(card)
        if problems:
            fail(f"card {i}: {'; '.join(problems)}")

    path = store_path()
    if path is None:
        fail("no store: set PR_RECALL_STORE (or run inside a Lucidos workspace)", 3)
    cards = load(path)
    kept = [c for c in cards if not (same_repo(c.get("repo", ""), args.repo) and c.get("pr") == args.pr)]
    store = {"schema": SCHEMA, "cards": kept + [{k: c[k] for k in FIELDS} for c in new]}
    via = write(path, json.dumps(store, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({
        "path": str(path), "via": via, "written": len(new),
        "replaced": len(cards) - len(kept), "total": len(store["cards"]),
    }))


def repo_arg(value):
    if not re.fullmatch(r"[\w.-]+/[\w.-]+", value):
        raise argparse.ArgumentTypeError("expected OWNER/REPO")
    return value


def main():
    parser = argparse.ArgumentParser(description="pr-recall card store")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("path").set_defaults(run=cmd_path)
    overlap = sub.add_parser("overlap")
    overlap.add_argument("--repo", required=True, type=repo_arg)
    overlap.set_defaults(run=cmd_overlap)
    upsert = sub.add_parser("upsert")
    upsert.add_argument("--repo", required=True, type=repo_arg)
    upsert.add_argument("--pr", required=True, type=int)
    upsert.set_defaults(run=cmd_upsert)
    args = parser.parse_args()
    args.run(args)


if __name__ == "__main__":
    main()
