# ruff: noqa: E501
"""Build a self-contained, light-themed HTML report from docs/paper.md, inlining
every SVG figure, and (via a headless Chromium) a print-ready PDF.

Pure standard library for the HTML. Regenerate after editing the paper:

    python docs/build_report.py                     # writes docs/research.html
    python docs/build_report.py --pdf CHROME_PATH   # also writes docs/paper.pdf

The HTML has no external dependencies (fonts are system, figures are inlined),
so it opens anywhere and prints cleanly.
"""

from __future__ import annotations

import html
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "docs" / "paper.md"
OUT = ROOT / "docs" / "research.html"
PDF = ROOT / "docs" / "paper.pdf"


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def inline(text: str) -> str:
    codes: list[str] = []

    def stash(m):
        codes.append(m.group(1))
        return f"\x00{len(codes)-1}\x00"

    text = re.sub(r"`([^`]+)`", stash, text)
    text = html.escape(text, quote=False)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    return re.sub(
        r"\x00(\d+)\x00",
        lambda m: f"<code>{html.escape(codes[int(m.group(1))])}</code>",
        text,
    )


def svg_of(path: str) -> str:
    f = ROOT / path.replace("../", "")
    if not f.exists():
        return f"<em>missing figure: {path}</em>"
    s = f.read_text(encoding="utf-8")
    return s[s.index("<svg"):]


def convert(md: str) -> tuple[str, str, str, list[tuple[int, str, str]]]:
    lines = md.split("\n")
    n = len(lines)
    i = 0
    title = subtitle = ""
    while i < n and not lines[i].startswith("# "):
        i += 1
    if i < n:
        title = lines[i][2:].strip()
        i += 1
    while i < n and lines[i].strip() == "":
        i += 1
    if i < n and not lines[i].startswith("#"):
        subtitle = inline(lines[i].strip())
        i += 1

    body: list[str] = []
    toc: list[tuple[int, str, str]] = []
    while i < n:
        s = lines[i].strip()
        if s == "":
            i += 1
            continue
        m = re.match(r"^(#{2,3})\s+(.*)", lines[i])
        if m:
            level = len(m.group(1))
            text = m.group(2).strip()
            sid = slug(text)
            toc.append((level, sid, text))
            body.append(f'<h{level} id="{sid}">{inline(text)}</h{level}>')
            i += 1
            continue
        if s.startswith("```"):
            i += 1
            buf = []
            while i < n and not lines[i].strip().startswith("```"):
                buf.append(lines[i])
                i += 1
            i += 1
            body.append(f'<pre class="eq">{html.escape(chr(10).join(buf))}</pre>')
            continue
        m = re.match(r"^!\[([^\]]*)\]\(([^)]+)\)", s)
        if m:
            svg = svg_of(m.group(2))
            cap = ""
            j = i + 1
            while j < n and lines[j].strip() == "":
                j += 1
            if j < n and re.match(r"^\*[^*].*\*$", lines[j].strip()):
                cap = inline(lines[j].strip()[1:-1])
                i = j
            body.append(
                f'<figure class="fig"><div class="figbox">{svg}</div>'
                + (f"<figcaption>{cap}</figcaption>" if cap else "")
                + "</figure>"
            )
            i += 1
            continue
        if s.startswith("|") and i + 1 < n and re.match(r"^\|[\s:|-]+\|?$", lines[i + 1].strip()):
            header = [c.strip() for c in s.strip("|").split("|")]
            i += 2
            rows = []
            while i < n and lines[i].strip().startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            th = "".join(f"<th>{inline(c)}</th>" for c in header)
            trs = "".join(
                "<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in rows
            )
            body.append(
                f'<div class="tablewrap"><table><thead><tr>{th}</tr></thead>'
                f"<tbody>{trs}</tbody></table></div>"
            )
            continue
        if re.match(r"^[-*]\s+", s) or re.match(r"^\d+\.\s+", s):
            ordered = bool(re.match(r"^\d+\.\s+", s))
            items = []
            while i < n and (
                re.match(r"^[-*]\s+", lines[i].strip()) or re.match(r"^\d+\.\s+", lines[i].strip())
            ):
                item = re.sub(r"^([-*]|\d+\.)\s+", "", lines[i].strip())
                items.append(f"<li>{inline(item)}</li>")
                i += 1
            tag = "ol" if ordered else "ul"
            body.append(f"<{tag}>{''.join(items)}</{tag}>")
            continue
        if re.match(r"^\*[^*].*\*$", s):
            body.append(f'<p class="caption">{inline(s[1:-1])}</p>')
            i += 1
            continue
        body.append(f"<p>{inline(s)}</p>")
        i += 1
    return title, subtitle, "\n".join(body), toc


TEMPLATE = """<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
:root{--paper:#fcfcfa;--panel:#fff;--panel-2:#f6f7f3;--ink:#1b2027;--body:#2b333c;
--muted:#5c6773;--faint:#93a0ab;--rule:#e7e9e3;--rule-strong:#d4d8cf;--accent:#0f766e;
--accent-ink:#0b5a54;--accent-soft:#0f766e14;--serif:"Iowan Old Style",Georgia,"Times New Roman",serif;
--sans:system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,sans-serif;
--mono:ui-monospace,"SF Mono","Cascadia Code",Menlo,monospace;--maxw:44rem;}
*{box-sizing:border-box}html{scroll-behavior:smooth}
body{margin:0;background:var(--paper);color:var(--body);font-family:var(--serif);
font-size:18px;line-height:1.72;-webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility}
.layout{display:grid;grid-template-columns:17rem minmax(0,1fr);max-width:74rem;margin:0 auto}
aside{position:sticky;top:0;align-self:start;height:100vh;overflow-y:auto;
padding:2.4rem 1.4rem 2rem 1.8rem;border-right:1px solid var(--rule)}
.brandmark{font-family:var(--sans);font-size:.72rem;letter-spacing:.16em;text-transform:uppercase;
color:var(--accent);font-weight:700;margin-bottom:.2rem}
.brandsub{font-family:var(--sans);font-size:.78rem;color:var(--faint);margin-bottom:1.5rem;line-height:1.4}
nav{display:flex;flex-direction:column;gap:.1rem;font-family:var(--sans)}
nav a{color:var(--muted);text-decoration:none;font-size:.82rem;line-height:1.35;
padding:.28rem .5rem;border-left:2px solid transparent;border-radius:0 4px 4px 0}
nav a.toc-h3{padding-left:1.2rem;font-size:.78rem;color:var(--faint)}
nav a:hover{color:var(--accent);background:var(--accent-soft)}
nav a.active{color:var(--accent-ink);border-left-color:var(--accent);background:var(--accent-soft);font-weight:600}
main{padding:3.2rem 3rem 6rem;min-width:0}
.prose,header.hero,.rule{max-width:var(--maxw);margin-left:auto;margin-right:auto}
header.hero{margin-bottom:2.4rem}
.eyebrow{font-family:var(--sans);font-size:.74rem;letter-spacing:.15em;text-transform:uppercase;
color:var(--accent);font-weight:700}
h1.title{font-family:var(--serif);font-weight:600;font-size:clamp(2rem,4.4vw,3.1rem);line-height:1.08;
letter-spacing:-.01em;margin:.5rem 0;color:var(--ink);text-wrap:balance}
.subtitle{font-size:1.16rem;color:var(--muted);line-height:1.55;margin:0;text-wrap:pretty}
.meta{font-family:var(--sans);font-size:.8rem;color:var(--faint);margin-top:1.1rem;
display:flex;gap:.6rem;flex-wrap:wrap;align-items:center}.meta .dot{color:var(--rule-strong)}
.chips{display:flex;flex-wrap:wrap;gap:.7rem;margin-top:1.8rem}
.chip{background:var(--panel);border:1px solid var(--rule);border-radius:12px;padding:.7rem .9rem;
min-width:8.5rem;flex:1 1 8.5rem}
.chip .n{font-family:var(--serif);font-size:1.5rem;font-weight:600;color:var(--ink);line-height:1;
font-variant-numeric:tabular-nums}
.chip.accent{background:var(--accent-soft);border-color:transparent}.chip.accent .n{color:var(--accent-ink)}
.chip .k{font-family:var(--sans);font-size:.72rem;color:var(--muted);margin-top:.4rem;line-height:1.3}
.rule{margin-bottom:2.4rem;border:none;border-top:1px solid var(--rule)}
h2{font-family:var(--serif);font-weight:600;font-size:1.7rem;letter-spacing:-.01em;color:var(--ink);
margin:3.2rem 0 .3rem;padding-top:1.6rem;border-top:1px solid var(--rule);text-wrap:balance}
h3{font-family:var(--serif);font-weight:600;font-size:1.24rem;color:var(--ink);margin:2rem 0 .2rem;text-wrap:balance}
p{margin:.9rem 0}
a{color:var(--accent);text-decoration:none;border-bottom:1px solid var(--accent-soft)}
a:hover{border-bottom-color:var(--accent)}strong{color:var(--ink);font-weight:600}
code{font-family:var(--mono);font-size:.86em;background:var(--panel-2);padding:.08em .38em;
border-radius:5px;color:var(--accent-ink);border:1px solid var(--rule)}
pre.eq{font-family:var(--mono);font-size:.92rem;background:var(--panel-2);border:1px solid var(--rule);
border-left:3px solid var(--accent);border-radius:8px;padding:.9rem 1.1rem;overflow-x:auto;
color:var(--ink);line-height:1.5}
ul,ol{margin:.9rem 0;padding-left:1.3rem}li{margin:.35rem 0}li::marker{color:var(--accent)}
figure.fig{margin:2rem 0;max-width:100%}
.figbox{background:var(--panel);border:1px solid var(--rule);border-radius:12px;padding:1rem;
overflow-x:auto;box-shadow:0 1px 2px rgba(20,30,25,.04)}
.figbox svg{display:block;max-width:100%;height:auto;margin:0 auto}
figcaption{font-family:var(--sans);font-size:.82rem;color:var(--muted);margin-top:.7rem;line-height:1.5}
.caption{font-family:var(--sans);font-size:.82rem;color:var(--muted);margin:.4rem 0 1.4rem}
.tablewrap{overflow-x:auto;margin:1.5rem 0;border:1px solid var(--rule);border-radius:10px}
table{border-collapse:collapse;width:100%;font-size:.9rem;font-family:var(--sans)}
thead th{background:var(--panel-2);text-align:left;font-size:.72rem;letter-spacing:.05em;
text-transform:uppercase;color:var(--muted);font-weight:700;padding:.7rem .85rem;
border-bottom:1px solid var(--rule-strong);white-space:nowrap}
td{padding:.6rem .85rem;border-bottom:1px solid var(--rule);vertical-align:top;color:var(--body)}
tbody tr:last-child td{border-bottom:none}tbody tr:nth-child(even){background:var(--panel-2)}
td code{background:transparent;border:none;padding:0;color:var(--accent-ink)}
@media (max-width:900px){.layout{grid-template-columns:1fr}
aside{position:static;height:auto;border-right:none;border-bottom:1px solid var(--rule);padding:1.4rem}
nav{flex-flow:row wrap;gap:.2rem .4rem}nav a.toc-h3{display:none}main{padding:2rem 1.3rem 4rem}}
@media print{
@page{margin:16mm 15mm}
html{font-size:9.6pt}
body{background:#fff;color:#15181d;line-height:1.42}
.layout{display:block;max-width:none}aside{display:none}main{padding:0}
.prose,header.hero,.rule{max-width:none}
a{color:#15181d;border:none}
p{margin:.42rem 0;orphans:2;widows:2}
h2{page-break-after:avoid;break-after:avoid;margin:1.3rem 0 .2rem;padding-top:.7rem;font-size:1.35rem}
h3{page-break-after:avoid;break-after:avoid;margin:.9rem 0 .1rem;font-size:1.08rem}
figure.fig,.tablewrap,pre.eq{page-break-inside:avoid;break-inside:avoid;margin:.9rem 0}
.figbox{box-shadow:none;padding:.5rem}
li{margin:.15rem 0}
header.hero{margin-bottom:1rem}h1.title{font-size:23pt;margin:.2rem 0}
.chips{gap:.35rem;margin-top:1rem}.chip{padding:.5rem .6rem}
table{font-size:8.4pt}thead th,td{padding:.35rem .5rem}
}
</style></head>
<body><div class="layout">
<aside><div class="brandmark">CTA</div>
<div class="brandsub">Chemotactic Task Allocation<br>Research report</div>
<nav id="toc">
__TOC__
</nav></aside>
<main>
<header class="hero">
<div class="eyebrow">Decentralised multi-agent orchestration</div>
<h1 class="title">__TITLE__</h1>
<p class="subtitle">__SUBTITLE__</p>
<div class="meta"><span>Chemotactic Task Allocation</span><span class="dot">&middot;</span>\
<span>Reproducible from seeds</span><span class="dot">&middot;</span><span>127 tests, ruff clean</span></div>
<div class="chips">
<div class="chip accent"><div class="n">&#8776;40&times;</div><div class="k">cheaper at equal completion (agent wrapper)</div></div>
<div class="chip"><div class="n">0.0 / 2.0</div><div class="k">peak-load growth exponent, decentralised vs central</div></div>
<div class="chip"><div class="n">12</div><div class="k">hypotheses; 10 synthetic, 2 on real agents</div></div>
<div class="chip"><div class="n">114</div><div class="k">real-agent attempts behind the calibration result</div></div>
</div></header>
<hr class="rule">
<article class="prose">
__BODY__
</article></main></div>
<script>
const links=[...document.querySelectorAll('#toc a')];
const map=new Map(links.map(a=>[a.getAttribute('href').slice(1),a]));
const seen=new Set();
const io=new IntersectionObserver((es)=>{es.forEach(e=>{e.isIntersecting?seen.add(e.target.id):seen.delete(e.target.id)});
let active=null;document.querySelectorAll('h2[id],h3[id]').forEach(h=>{if(seen.has(h.id))active=active||h.id});
links.forEach(a=>a.classList.remove('active'));if(active&&map.get(active))map.get(active).classList.add('active');},
{rootMargin:'-10% 0px -80% 0px'});
document.querySelectorAll('h2[id],h3[id]').forEach(h=>io.observe(h));
</script>
</body></html>
"""


def build() -> None:
    title, subtitle, body, toc = convert(SRC.read_text(encoding="utf-8"))
    toc_html = "\n".join(
        f'<a class="toc-h{lvl}" href="#{sid}">{html.escape(t)}</a>' for lvl, sid, t in toc
    )
    out = (
        TEMPLATE.replace("__TITLE__", html.escape(title))
        .replace("__SUBTITLE__", subtitle)
        .replace("__TOC__", toc_html)
        .replace("__BODY__", body)
    )
    OUT.write_text(out, encoding="utf-8")
    print(f"wrote {OUT}  ({len([t for t in toc if t[0]==2])} sections, "
          f"{body.count('<figure')} figures inlined)")


def make_pdf(chrome: str) -> None:
    subprocess.run(
        [chrome, "--headless", "--disable-gpu", "--no-sandbox", "--no-pdf-header-footer",
         "--virtual-time-budget=5000", f"--print-to-pdf={PDF}", OUT.as_uri()],
        check=True, capture_output=True,
    )
    print(f"wrote {PDF}  ({PDF.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    build()
    if len(sys.argv) > 2 and sys.argv[1] == "--pdf":
        make_pdf(sys.argv[2])
