#!/usr/bin/env python3
"""Render a Markdown report (with ```mermaid blocks) to a readable, OS-theme-aware
HTML page and open it in the browser. Zero dependencies (Python stdlib only).

Usage:
    python3 render.py [--title TITLE] [--out PATH] [--no-open] [INPUT.md]
    cat report.md | python3 render.py --title "PR #123"

By default the page is written to a STABLE path derived from the title
(<tmpdir>/pr-understanding-<slug>.html), so re-running the skill on the same PR
UPDATES the same artifact in place instead of littering new random temp files —
the URL stays constant and the open tab just needs a refresh. Pass --out to pin
a location. Prints the path. Nothing is committed.

The page follows the OS light/dark setting LIVE: page chrome via a CSS
prefers-color-scheme media query, and Mermaid diagrams re-render when the OS
theme flips. Markdown + Mermaid load from pinned CDN ESM builds; if the network
is unavailable the page falls back to showing the raw markdown. A diagram that
fails to parse degrades to a small labelled source block — never Mermaid's
"Syntax error" bomb graphic.
"""
import argparse
import datetime
import tempfile
import json
import os
import platform
import re
import subprocess
import sys
import webbrowser

TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
  :root {
    color-scheme: light dark;
    --maxw: 58rem;
    --bg: #fbfbfa;
    --surface: #ffffff;
    --text: #1f2328;
    --muted: #6a737d;
    --border: #d8dee4;
    --border-soft: #ebeef1;
    --accent: #0969da;
    --accent-weak: #ddf4ff;
    --code-bg: #f2f4f6;
    --code-text: #24292f;
    --warn-border: #d4a72c;
    --warn-bg: #fff8e6;
    --figure-bg: #f8fafc;
    --shadow: 0 1px 2px rgba(27,31,36,.06), 0 8px 24px rgba(27,31,36,.05);
    --radius: 12px;
    --mono: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, "Liberation Mono", monospace;
    --sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --bg: #0d1117;
      --surface: #161b22;
      --text: #e6edf3;
      --muted: #9aa5b1;
      --border: #30363d;
      --border-soft: #21262d;
      --accent: #58a6ff;
      --accent-weak: #123055;
      --code-bg: #1b222c;
      --code-text: #d1d9e0;
      --warn-border: #bb9020;
      --warn-bg: #1c1a10;
      --figure-bg: #11161d;
      --shadow: 0 1px 2px rgba(0,0,0,.4), 0 8px 28px rgba(0,0,0,.35);
    }
  }
  * { box-sizing: border-box; }
  html { scroll-behavior: smooth; }
  body {
    margin: 0; padding: 2.5rem 1.25rem 7rem;
    font-family: var(--sans);
    font-size: 16px; line-height: 1.7;
    background: var(--bg); color: var(--text);
    -webkit-font-smoothing: antialiased;
  }
  main { max-width: var(--maxw); margin: 0 auto; }

  /* ---- header ---- */
  header.doc { margin-bottom: 2rem; }
  .eyebrow {
    font-size: .72rem; font-weight: 700; letter-spacing: .09em;
    text-transform: uppercase; color: var(--accent);
    display: inline-flex; align-items: center; gap: .5rem;
  }
  .eyebrow::before {
    content: ""; width: 1.4rem; height: 2px; border-radius: 2px;
    background: var(--accent); display: inline-block;
  }
  header.doc h1 {
    font-size: 2rem; font-weight: 680; line-height: 1.2;
    margin: .55rem 0 .5rem;
  }
  .meta { color: var(--muted); font-size: .85rem; margin: 0; }

  /* ---- table of contents ---- */
  nav.toc {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: var(--radius); padding: 1rem 1.25rem;
    margin: 1.75rem 0 2.5rem; box-shadow: var(--shadow);
  }
  nav.toc .toc-label {
    font-size: .72rem; font-weight: 700; letter-spacing: .07em;
    text-transform: uppercase; color: var(--muted); margin-bottom: .6rem;
  }
  nav.toc ol {
    list-style: none; margin: 0; padding: 0;
    display: grid; grid-template-columns: repeat(auto-fit, minmax(13rem, 1fr));
    gap: .3rem 1.5rem; counter-reset: toc;
  }
  nav.toc li { counter-increment: toc; margin: 0; }
  nav.toc a {
    text-decoration: none; color: var(--text); font-size: .92rem;
    display: flex; gap: .55rem; padding: .28rem .35rem; border-radius: 6px;
    align-items: baseline;
  }
  nav.toc a::before {
    content: counter(toc); color: var(--accent); font-variant-numeric: tabular-nums;
    font-weight: 600; font-size: .8rem; min-width: 1.1rem;
  }
  nav.toc a:hover { background: var(--accent-weak); }

  /* ---- headings ---- */
  h1, h2, h3 { line-height: 1.3; }
  h2 {
    font-size: 1.4rem; font-weight: 660; margin: 3rem 0 1rem;
    padding-top: 1.6rem; border-top: 1px solid var(--border-soft);
    scroll-margin-top: 1.5rem;
  }
  main > section:first-of-type h2:first-child,
  h2:first-child { border-top: none; padding-top: 0; margin-top: .5rem; }
  h3 { font-size: 1.12rem; font-weight: 640; margin: 1.8rem 0 .6rem; }

  p { margin: .8rem 0; }
  ul, ol { padding-left: 1.4rem; }
  li { margin: .35rem 0; }
  li::marker { color: var(--muted); }
  strong { font-weight: 650; }
  a { color: var(--accent); text-underline-offset: 2px; }

  /* ---- code ---- */
  code { font-family: var(--mono); font-size: .86em; }
  :not(pre) > code {
    background: var(--code-bg); color: var(--code-text);
    padding: .12em .4em; border-radius: 5px;
    border: 1px solid var(--border-soft);
  }
  pre {
    background: var(--code-bg); color: var(--code-text);
    padding: 1rem 1.1rem; border-radius: 10px; overflow: auto;
    border: 1px solid var(--border-soft); font-size: .88rem; line-height: 1.55;
  }
  pre code { border: none; background: none; padding: 0; }

  /* ---- blockquote (verify / callouts) ---- */
  blockquote {
    margin: 1.1rem 0; padding: .7rem 1.1rem;
    border-left: 4px solid var(--warn-border); border-radius: 0 8px 8px 0;
    background: var(--warn-bg); color: var(--text);
  }
  blockquote p { margin: .3rem 0; }

  /* ---- tables ---- */
  table {
    border-collapse: collapse; width: 100%; margin: 1.2rem 0;
    font-size: .93rem; overflow: hidden; border-radius: 10px;
    border: 1px solid var(--border);
  }
  th, td { border-bottom: 1px solid var(--border-soft); padding: .55rem .8rem; text-align: left; }
  th { background: var(--figure-bg); font-weight: 640; }
  tr:last-child td { border-bottom: none; }

  hr { border: none; border-top: 1px solid var(--border-soft); margin: 2.5rem 0; }

  /* ---- mermaid figures ---- */
  .mermaid-graph {
    margin: 1.6rem 0; padding: 1.25rem; text-align: center;
    background: var(--figure-bg); border: 1px solid var(--border);
    border-radius: var(--radius); overflow-x: auto; box-shadow: var(--shadow);
  }
  .mermaid-graph svg { max-width: 100%; height: auto; }
  .diagram-error {
    margin: 1.6rem 0; border: 1px solid var(--warn-border);
    border-radius: var(--radius); overflow: hidden; background: var(--warn-bg);
  }
  .diagram-error .label {
    font-size: .78rem; font-weight: 650; color: var(--muted);
    padding: .5rem .9rem; border-bottom: 1px solid var(--warn-border);
    display: flex; align-items: center; gap: .5rem;
  }
  .diagram-error pre { margin: 0; border: none; border-radius: 0; background: transparent; text-align: left; }

  /* ---- collapsible detail sections ---- */
  details {
    border: 1px solid var(--border); border-radius: 10px;
    padding: .3rem 1rem; margin: 1rem 0; background: var(--surface);
  }
  details[open] { padding-bottom: .9rem; }
  summary {
    cursor: pointer; font-weight: 620; padding: .55rem 0;
    list-style: none; color: var(--text);
  }
  summary::-webkit-details-marker { display: none; }
  summary::before { content: "▸ "; color: var(--muted); }
  details[open] summary::before { content: "▾ "; }
</style>
</head>
<body>
<main>
  <header class="doc">
    <div class="eyebrow">PR Understanding</div>
    <h1>__TITLE__</h1>
    <p class="meta">Map — falsify at a glance · generated __GENERATED__</p>
  </header>
  <nav class="toc" id="toc" hidden><div class="toc-label">On this page</div><ol></ol></nav>
  <div id="content"></div>
</main>
<script type="module">
const MD = __PAYLOAD__;
const el = document.getElementById('content');
const mq = matchMedia('(prefers-color-scheme: dark)');
let mermaid, seq = 0;
const sources = [];

function slugify(s) {
  return s.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '') || 'section';
}

async function boot() {
  const { marked } = await import('https://cdn.jsdelivr.net/npm/marked@12/lib/marked.esm.js');
  mermaid = (await import('https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs')).default;
  el.innerHTML = marked.parse(MD, { gfm: true });

  // Build a table of contents from the H2 sections.
  const heads = [...el.querySelectorAll('h2')];
  if (heads.length > 1) {
    const ol = document.querySelector('#toc ol');
    const seen = {};
    for (const h of heads) {
      let id = slugify(h.textContent);
      if (seen[id]) id += '-' + (++seen[id]); else seen[id] = 1;
      h.id = id;
      const li = document.createElement('li');
      const a = document.createElement('a');
      a.href = '#' + id; a.textContent = h.textContent;
      li.appendChild(a); ol.appendChild(li);
    }
    document.getElementById('toc').hidden = false;
  }

  // Swap each ```mermaid code block for a placeholder that remembers its source,
  // so we can RE-render it whenever the OS theme flips.
  el.querySelectorAll('pre > code.language-mermaid').forEach((code, i) => {
    sources[i] = code.textContent;
    const holder = document.createElement('div');
    holder.className = 'mermaid-graph';
    holder.dataset.idx = String(i);
    code.parentElement.replaceWith(holder);
  });
  await paint();
  mq.addEventListener('change', paint);
}

async function paint() {
  if (!mermaid) return;
  // suppressErrorRendering keeps Mermaid from injecting its "Syntax error" bomb
  // SVG into the page; we catch the throw and show a clean source block instead.
  mermaid.initialize({
    startOnLoad: false,
    theme: mq.matches ? 'dark' : 'default',
    securityLevel: 'loose',
    suppressErrorRendering: true,
  });
  for (const holder of document.querySelectorAll('.mermaid-graph, .diagram-error')) {
    const idx = Number(holder.dataset.idx);
    const src = sources[idx];
    try {
      const { svg } = await mermaid.render('mmd-' + (seq++), src);
      const g = document.createElement('div');
      g.className = 'mermaid-graph'; g.dataset.idx = String(idx); g.innerHTML = svg;
      holder.replaceWith(g);
    } catch (e) {
      const box = document.createElement('div');
      box.className = 'diagram-error'; box.dataset.idx = String(idx);
      const label = document.createElement('div');
      label.className = 'label';
      label.textContent = '\u26A0 Diagram could not be rendered — showing source';
      const pre = document.createElement('pre');
      pre.textContent = src;
      box.append(label, pre);
      holder.replaceWith(box);
      console.error('pr-understanding: mermaid render failed ->', e);
    }
  }
}

boot().catch(e => {
  const pre = document.createElement('pre');
  pre.textContent = MD;
  el.replaceChildren(pre);
  console.error('pr-understanding: rendering fell back to raw markdown ->', e);
});
</script>
</body>
</html>
"""


def embed(md):
    """JSON string literal that is also safe inside a <script> element."""
    s = json.dumps(md)
    return s.replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')


def slug(t):
    return re.sub(r'[^a-z0-9]+', '-', t.lower()).strip('-') or 'pr'


def open_in_browser(path):
    """Open `path` in the user's default browser as reliably as possible.

    webbrowser.open() alone is unreliable from subprocess / non-interactive
    contexts (a Claude Code or coding-agent session, cron, no controlling
    terminal): on macOS it can return False and launch nothing. So try the
    platform-native opener first (`open` on macOS, `os.startfile` on Windows,
    `xdg-open` on Linux) and fall back to webbrowser only if that fails.
    Diagnostics go to stderr so stdout stays just the path. Returns True if a
    launch plausibly succeeded.
    """
    abspath = os.path.abspath(path)
    url = "file://" + abspath
    system = platform.system()
    try:
        if system == "Darwin":
            subprocess.run(["open", abspath], check=True)
            return True
        if system == "Windows":
            os.startfile(abspath)  # type: ignore[attr-defined]
            return True
        if system == "Linux":
            subprocess.run(["xdg-open", abspath], check=True)
            return True
    except Exception as e:
        print("pr-understanding: native open failed (%s); trying webbrowser" % e,
              file=sys.stderr)
    try:
        if webbrowser.open(url):
            return True
    except Exception as e:
        print("pr-understanding: webbrowser.open failed -> %s" % e, file=sys.stderr)
    print("pr-understanding: could not auto-open a browser. Open it manually:\n  %s"
          % url, file=sys.stderr)
    return False


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('input', nargs='?', help='Markdown file (default: stdin)')
    ap.add_argument('--title', default='PR Understanding')
    ap.add_argument('--out', help='output HTML path (default: stable temp path from title)')
    ap.add_argument('--no-open', action='store_true', help='do not launch a browser')
    a = ap.parse_args()

    md = open(a.input, encoding='utf-8').read() if a.input else sys.stdin.read()
    generated = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
    safe_title = re.sub(r'[<>]', '', a.title)
    html = (TEMPLATE
            .replace('__TITLE__', safe_title)
            .replace('__GENERATED__', generated)
            .replace('__PAYLOAD__', embed(md)))

    # Stable path by default so re-running UPDATES the same artifact in place
    # (constant URL — just refresh the tab) instead of leaving random temp files.
    path = a.out or os.path.join(tempfile.gettempdir(),
                                 'pr-understanding-%s.html' % slug(a.title))
    with open(path, 'w', encoding='utf-8') as f:
        f.write(html)

    if not a.no_open:
        open_in_browser(path)
    print(path)


if __name__ == '__main__':
    main()
