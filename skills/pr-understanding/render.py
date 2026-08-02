#!/usr/bin/env python3
"""Render a Markdown report (with ```mermaid blocks) to a readable, OS-theme-aware
HTML page and open it in the browser. Zero dependencies (Python stdlib only).

Usage:
    python3 render.py [--title TITLE] [--meta JSON|PATH] [--triage STR] [--out PATH]
                      [--no-open] [INPUT.md]
    cat report.md | python3 render.py --title "PR #123"

--meta takes `gh pr view --json …` output verbatim (as a string or a file path) and
renders an identity bar under the title: author + avatar, state, link, dates, churn,
branches. Unknown keys are ignored and missing ones are simply not shown.

--triage takes the skill's routing line ("Deep lane · Feature lens · 14 meaningful
files") and renders each `·`-separated part as a chip in the same header. It belongs
in the chrome, not the body: it describes how the report was produced, not the PR.

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
import html
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
    --ok: #1a7f37;
    --danger: #cf222e;
    --merge: #8250df;
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
      --ok: #3fb950;
      --danger: #f85149;
      --merge: #a371f7;
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
    -webkit-text-size-adjust: 100%;
    overflow-wrap: break-word;
  }
  main { max-width: var(--maxw); margin: 0 auto; width: 100%; }

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

  /* ---- PR identity bar ---- */
  .prmeta {
    display: flex; flex-wrap: wrap; align-items: center; gap: .35rem .6rem;
    margin: .7rem 0 .65rem; font-size: .87rem; color: var(--muted);
  }
  .prmeta .sep { color: var(--border); }
  .prmeta .who {
    display: inline-flex; align-items: center; gap: .45rem;
    text-decoration: none; color: var(--text); font-weight: 620;
  }
  .prmeta .who:hover { color: var(--accent); }
  .avatar {
    position: relative; width: 22px; height: 22px; border-radius: 50%;
    overflow: hidden; flex: none; background: var(--accent-weak);
    border: 1px solid var(--border-soft);
  }
  .avatar img { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }
  .avatar .ini {
    display: flex; align-items: center; justify-content: center;
    width: 100%; height: 100%; font-size: .62rem; font-weight: 700; color: var(--accent);
  }
  .pill {
    font-size: .7rem; font-weight: 700; letter-spacing: .05em; text-transform: uppercase;
    padding: .1rem .5rem; border-radius: 999px;
    border: 1px solid currentColor; color: var(--muted);
  }
  .pill-open { color: var(--ok); }
  .pill-merged { color: var(--merge); }
  .pill-closed { color: var(--danger); }
  .prmeta .chip {
    font-family: var(--mono); font-size: .81rem; text-decoration: none;
    color: var(--accent); background: var(--accent-weak);
    padding: .1rem .45rem; border-radius: 6px;
  }
  .prmeta .add { color: var(--ok); font-weight: 650; }
  .prmeta .del { color: var(--danger); font-weight: 650; }
  .prmeta .branch { font-family: var(--mono); font-size: .8rem; }

  /* ---- triage chips (how the report was made, not what the PR does) ---- */
  .triage { display: flex; flex-wrap: wrap; gap: .35rem; margin: .55rem 0 .2rem; }
  .triage span {
    font-size: .72rem; font-weight: 640; letter-spacing: .02em;
    color: var(--muted); background: var(--code-bg);
    border: 1px solid var(--border-soft); border-radius: 999px;
    padding: .12rem .55rem;
  }

  /* ---- table of contents ---- */
  nav.toc {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: var(--radius); padding: 1.1rem 1.35rem 1.2rem;
    margin: 1.75rem 0 2.5rem; box-shadow: var(--shadow);
  }
  nav.toc .toc-label {
    font-size: .72rem; font-weight: 700; letter-spacing: .07em;
    text-transform: uppercase; color: var(--muted);
    padding-bottom: .55rem; border-bottom: 1px solid var(--border-soft);
  }
  nav.toc ol {
    list-style: none; margin: .35rem 0 0; padding: 0; counter-reset: toc;
  }
  nav.toc li { counter-increment: toc; margin: 0; }
  nav.toc a {
    text-decoration: none; color: var(--text); font-size: .95rem;
    display: flex; align-items: baseline; gap: .6rem;
    padding: .34rem .4rem; border-radius: 6px;
  }
  nav.toc a::before {
    content: counter(toc) "."; color: var(--muted);
    font-variant-numeric: tabular-nums; font-size: .85rem;
    min-width: 1.3rem; text-align: right; flex: none;
  }
  nav.toc a::after {
    content: ""; flex: 1 1 auto; min-width: 1.25rem;
    border-bottom: 1px dotted var(--border);
  }
  nav.toc a:hover { background: var(--accent-weak); color: var(--accent); }
  nav.toc a:hover::before { color: var(--accent); }

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
  /* `file:line` refs are long unbreakable tokens — let them break anywhere
     rather than push the whole page sideways on a narrow screen. */
  code { font-family: var(--mono); font-size: .86em; overflow-wrap: anywhere; }
  a { overflow-wrap: anywhere; }
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
  /* Wide comparison tables can't compress on a phone — the JS wraps each one in
     .table-scroll so it scrolls sideways on its own instead of crushing columns. */
  .table-scroll {
    overflow-x: auto; -webkit-overflow-scrolling: touch;
    margin: 1.2rem 0; border: 1px solid var(--border); border-radius: 10px;
  }
  .table-scroll > table { margin: 0; border: none; border-radius: 0; }
  table {
    border-collapse: collapse; width: 100%; margin: 1.2rem 0;
    font-size: .93rem; overflow: hidden; border-radius: 10px;
    border: 1px solid var(--border);
  }
  th, td { border-bottom: 1px solid var(--border-soft); padding: .55rem .8rem; text-align: left; }
  th { background: var(--figure-bg); font-weight: 640; }
  tr:last-child td { border-bottom: none; }

  hr { border: none; border-top: 1px solid var(--border-soft); margin: 2.5rem 0; }

  /* ---- screenshots (visual lens embeds these as plain markdown images) ---- */
  #content img {
    max-width: 100%; height: auto; display: block;
    border: 1px solid var(--border); border-radius: 10px; background: var(--figure-bg);
  }
  td img { margin: 0 auto; }

  /* ---- UI mocks: before | after panels the visual lens rebuilds from the diff ---- */
  .pv {
    display: grid; gap: 1rem; margin: 1.5rem 0;
    grid-template-columns: repeat(auto-fit, minmax(16rem, 1fr));
  }
  .pv figure { margin: 0; }
  .pv figcaption {
    font-size: .72rem; font-weight: 700; letter-spacing: .07em;
    text-transform: uppercase; color: var(--muted); margin-bottom: .45rem;
  }
  .mock {
    display: flex; flex-direction: column; gap: .55rem;
    background: var(--surface); border: 1px solid var(--border);
    border-radius: var(--radius); padding: .9rem; box-shadow: var(--shadow);
    font-size: .82rem; line-height: 1.4;
  }
  .mock .row { display: flex; align-items: center; gap: .5rem; }
  .mock .btn {
    flex: 1; text-align: center; padding: .45rem .6rem; font-size: .78rem;
    border: 1px solid var(--border); border-radius: 8px; background: var(--code-bg);
  }
  .mock .ph { height: .55rem; border-radius: 999px; background: var(--border-soft); }
  .mock .is-new { outline: 2px solid var(--ok); outline-offset: 3px; }
  .mock .is-gone { outline: 2px dashed var(--danger); outline-offset: 3px; opacity: .55; }

  /* ---- mermaid figures ---- */
  .mermaid-graph {
    margin: 1.6rem 0; padding: 1.25rem; text-align: center;
    background: var(--figure-bg); border: 1px solid var(--border);
    border-radius: var(--radius); overflow-x: auto;
    -webkit-overflow-scrolling: touch; box-shadow: var(--shadow);
  }
  /* Mermaid writes an inline max-width on the <svg> sized to the diagram's
     natural width. On a phone that cap shrinks the diagram to an illegible
     smudge, so below the breakpoint we drop the cap and scroll the figure
     instead — paint() pins an explicit pixel width so this is deterministic. */
  .mermaid-graph svg { max-width: 100%; height: auto; }
  @media (max-width: 44rem) {
    .mermaid-graph { padding: .9rem; text-align: left; }
    .mermaid-graph svg { max-width: none; }
    .mermaid-graph::-webkit-scrollbar { height: 4px; }
    .mermaid-graph::-webkit-scrollbar-thumb {
      background: var(--border); border-radius: 4px;
    }
  }
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

  /* ---- narrow screens (phones) ---- */
  @media (max-width: 44rem) {
    body { padding: 1.5rem 1rem 5rem; font-size: 16px; line-height: 1.65; }
    header.doc h1 { font-size: 1.5rem; }
    .prmeta { font-size: .8rem; gap: .3rem .45rem; }
    /* The " · " separators only make sense on one line; wrapped, they float
       to the start of a row and read as noise. */
    .prmeta .sep { display: none; }
    .prmeta .branch { overflow-wrap: anywhere; }
    nav.toc { padding: .9rem 1rem 1rem; margin: 1.25rem 0 1.75rem; }
    nav.toc a { font-size: .9rem; padding: .42rem .3rem; }
    /* The dotted leader needs a full line to itself once labels wrap. */
    nav.toc a::after { display: none; }
    h2 { font-size: 1.22rem; margin: 2.2rem 0 .8rem; padding-top: 1.2rem; }
    h3 { font-size: 1.05rem; }
    ul, ol { padding-left: 1.15rem; }
    pre { padding: .8rem .85rem; font-size: .8rem; }
    blockquote { padding: .6rem .85rem; }
    .table-scroll { margin: 1rem -1rem; border-radius: 0; border-left: none; border-right: none; }
    .table-scroll > table { font-size: .84rem; }
    /* Let the widest column keep its shape; the wrapper scrolls. */
    .table-scroll th, .table-scroll td { padding: .5rem .6rem; }
    .table-scroll th:first-child, .table-scroll td:first-child { min-width: 9rem; }
    details { padding: .3rem .85rem; }
  }
  @media (max-width: 26rem) {
    body { padding: 1.25rem .8rem 4.5rem; }
    header.doc h1 { font-size: 1.32rem; }
    .table-scroll { margin: 1rem -.8rem; }
  }
</style>
</head>
<body>
<main>
  <header class="doc">
    <div class="eyebrow">PR Understanding</div>
    <h1>__TITLE__</h1>
__METABAR__
__TRIAGE__
    <p class="meta">Map — falsify at a glance · generated __GENERATED__</p>
  </header>
  <nav class="toc" id="toc" hidden><div class="toc-label">Contents</div><ol></ol></nav>
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

// A heading may be a full narrative sentence — great in the body, unreadable as a nav
// label. Prefer the part before an em-dash/colon, but only when that prefix is
// substantial enough to name the section on its own.
const TOC_MAX = 48;
function tocLabel(s) {
  const t = s.trim();
  if (t.length <= TOC_MAX) return t;
  const cut = t.search(/\s+[—–:]\s+/);
  if (cut >= 12 && cut <= TOC_MAX) return t.slice(0, cut);
  return t.slice(0, TOC_MAX - 1).trimEnd() + '…';
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
      a.href = '#' + id; a.textContent = tocLabel(h.textContent);
      if (a.textContent !== h.textContent.trim()) a.title = h.textContent.trim();
      li.appendChild(a); ol.appendChild(li);
    }
    document.getElementById('toc').hidden = false;
  }

  // Wrap every table so a wide one scrolls sideways on its own instead of
  // squeezing 4 columns of file:line refs into a phone's width.
  el.querySelectorAll('table').forEach(t => {
    if (t.parentElement?.classList.contains('table-scroll')) return;
    const wrap = document.createElement('div');
    wrap.className = 'table-scroll';
    t.replaceWith(wrap);
    wrap.appendChild(t);
  });

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

  // Rotating the phone changes which diagrams fit — re-evaluate, debounced.
  let rt;
  addEventListener('resize', () => {
    clearTimeout(rt);
    rt = setTimeout(() => document.querySelectorAll('.mermaid-graph').forEach(sizeDiagram), 150);
  });
}

// Mermaid emits `style="max-width: NNNpx"` plus a viewBox. Wide-on-desktop is
// fine, but on a phone that lets the SVG scale down to ~350px and the node text
// becomes unreadable. Pin an explicit width: its natural size when the figure is
// too narrow to hold it (the figure then scrolls), otherwise Mermaid's own cap,
// which leaves a diagram that already fits at exactly the size it has today.
const MIN_LEGIBLE_SCALE = 0.92;
function sizeDiagram(holder) {
  const svg = holder.querySelector('svg');
  if (!svg) return;
  const vb = svg.viewBox?.baseVal;
  const natural = vb && vb.width ? vb.width : parseFloat(svg.style.maxWidth) || 0;
  if (!natural) return;
  svg.dataset.natural = String(natural);
  const avail = holder.clientWidth
    - parseFloat(getComputedStyle(holder).paddingLeft || 0)
    - parseFloat(getComputedStyle(holder).paddingRight || 0);
  if (avail > 0 && avail < natural * MIN_LEGIBLE_SCALE) {
    // Too tight to render legibly — keep full size and scroll the figure.
    svg.style.maxWidth = 'none';
    svg.style.width = natural + 'px';
  } else {
    svg.style.maxWidth = natural + 'px';
    svg.style.width = '';
  }
  svg.style.height = 'auto';
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
      sizeDiagram(g);
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


def load_meta(raw):
    """`--meta` is either inline JSON or a path to a JSON file."""
    if not raw:
        return {}
    text = raw if raw.lstrip().startswith('{') else open(raw, encoding='utf-8').read()
    try:
        meta = json.loads(text)
    except (ValueError, OSError) as e:
        print('pr-understanding: --meta ignored, could not parse -> %s' % e, file=sys.stderr)
        return {}
    return meta if isinstance(meta, dict) else {}


def _url(u):
    """Only http(s) survives — a meta blob must not be able to inject javascript:."""
    return u.strip() if isinstance(u, str) and re.match(r'https?://', u.strip(), re.I) else ''


def _date(v):
    if not isinstance(v, str) or not v:
        return ''
    try:
        d = datetime.datetime.fromisoformat(v.replace('Z', '+00:00'))
    except ValueError:
        return v
    return '%s %d, %d' % (d.strftime('%b'), d.day, d.year)


def build_metabar(meta):
    """Author + avatar, state, link, dates, churn, branches — from `gh pr view --json`
    output verbatim. Every part is optional; whatever is missing is left out."""
    if not meta:
        return ''
    e = lambda v: html.escape(str(v), quote=True)
    bits = []

    author = meta.get('author')
    author = {'login': author} if isinstance(author, str) else (author or {})
    login = author.get('login') or ''
    who = author.get('name') or login
    if who:
        # gh's author object has no avatar URL, but github.com/<login>.png is stable.
        plain = re.match(r'^[A-Za-z0-9][A-Za-z0-9-]{0,38}$', login)
        avatar = _url(meta.get('avatarUrl') or author.get('avatarUrl') or
                      ('https://github.com/%s.png?size=64' % login if plain else ''))
        profile = _url(author.get('url') or
                       ('https://github.com/%s' % login if plain else ''))
        initials = ''.join(w[0] for w in who.split()[:2]).upper() or '?'
        # The <img> sits on top of the initials, so a failed load reveals them.
        face = '<span class="avatar">%s<span class="ini">%s</span></span>' % (
            '<img src="%s" alt="" onerror="this.remove()">' % e(avatar) if avatar else '',
            e(initials))
        tag = 'a href="%s"' % e(profile) if profile else 'span'
        bits.append('<%s class="who">%s%s</%s>' % (tag, face, e(who), tag.split()[0]))

    state = str(meta.get('state') or '').lower()
    if meta.get('isDraft'):
        state = 'draft'
    if state:
        bits.append('<span class="pill pill-%s">%s</span>' % (e(state), e(state)))

    url = _url(meta.get('url'))
    owner_repo, number = meta.get('repo') or '', meta.get('number') or ''
    at = re.search(r'github\.com/([^/]+/[^/]+)/pull/(\d+)', url)
    if at:
        owner_repo, number = owner_repo or at.group(1), number or at.group(2)
    label = ('%s#%s' % (owner_repo, number)).strip('#') or url
    if url and label:
        bits.append('<a class="chip" href="%s">%s</a>' % (e(url), e(label)))
    elif label:
        bits.append('<span class="chip">%s</span>' % e(label))

    for key, verb in (('createdAt', 'opened'), ('mergedAt', 'merged'),
                      ('closedAt', 'closed'), ('date', '')):
        if key == 'closedAt' and meta.get('mergedAt'):
            continue
        when = _date(meta.get(key))
        if when:
            bits.append('<span>%s</span>' % e(('%s %s' % (verb, when)).strip()))

    adds, dels = meta.get('additions'), meta.get('deletions')
    files = meta.get('changedFiles')
    if files is None and isinstance(meta.get('files'), list):
        files = len(meta['files'])
    churn = []
    if isinstance(adds, int):
        churn.append('<span class="add">+%d</span>' % adds)
    if isinstance(dels, int):
        churn.append('<span class="del">−%d</span>' % dels)
    if isinstance(files, int):
        churn.append('across %d file%s' % (files, '' if files == 1 else 's'))
    if churn:
        bits.append('<span>%s</span>' % ' '.join(churn))

    head = meta.get('headRefName') or meta.get('branch')
    base = meta.get('baseRefName') or meta.get('base')
    if head and base:
        bits.append('<span class="branch">%s → %s</span>' % (e(head), e(base)))

    if not bits:
        return ''
    return '    <div class="prmeta">%s</div>' % '<span class="sep">·</span>'.join(bits)


def build_triage(raw):
    """"Deep lane · Feature lens · 14 meaningful files" -> one chip per `·` part."""
    trim = lambda s: s.strip(' \t*_>')
    parts = [trim(p) for p in re.split(r'[·|]', raw or '')]
    # The skill may still prefix the line with its own label; the chips are the label.
    parts[0] = trim(re.sub(r'^triage\s*:', '', parts[0], flags=re.I))
    chips = ''.join('<span>%s</span>' % html.escape(p, quote=True) for p in parts if p)
    return '    <div class="triage">%s</div>' % chips if chips else ''


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
    ap.add_argument('--meta', help='PR metadata: `gh pr view --json …` output, inline or a file path')
    ap.add_argument('--triage', help='routing line, e.g. "Deep lane · Feature lens · 14 meaningful files"')
    ap.add_argument('--out', help='output HTML path (default: stable temp path from title)')
    ap.add_argument('--no-open', action='store_true', help='do not launch a browser')
    a = ap.parse_args()

    md = open(a.input, encoding='utf-8').read() if a.input else sys.stdin.read()
    subs = {
        '__TITLE__': re.sub(r'[<>]', '', a.title),
        '__GENERATED__': datetime.datetime.now().strftime('%Y-%m-%d %H:%M'),
        '__METABAR__': build_metabar(load_meta(a.meta)),
        '__TRIAGE__': build_triage(a.triage),
        '__PAYLOAD__': embed(md),
    }
    # One pass, so a substituted value can never be re-scanned as a placeholder.
    page = re.sub(r'__(?:TITLE|GENERATED|METABAR|TRIAGE|PAYLOAD)__',
                  lambda m: subs[m.group(0)], TEMPLATE)

    # Stable path by default so re-running UPDATES the same artifact in place
    # (constant URL — just refresh the tab) instead of leaving random temp files.
    path = a.out or os.path.join(tempfile.gettempdir(),
                                 'pr-understanding-%s.html' % slug(a.title))
    with open(path, 'w', encoding='utf-8') as f:
        f.write(page)

    if not a.no_open:
        open_in_browser(path)
    print(path)


if __name__ == '__main__':
    main()
