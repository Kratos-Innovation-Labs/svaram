#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Kratos Innovation Labs Limited
"""Build the public web folder from the language packs and web/site.yaml.

    python3 tools/build_site.py --out /tmp/site          # write the site
    python3 tools/build_site.py --out /tmp/site --check  # also check every pack is complete

Writes: index.html (type in English), one page per language (/<code>/), /about/, app.js,
app.css, fonts and brand files, and robots.txt and sitemap.xml when search is allowed.
The phrase audio (/phrases/<code>/<id>.mp3) is made separately by tools/make_phrases.py.
Standard library plus PyYAML.
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "core"))
import yaml  # noqa: E402
from packs import load_all  # noqa: E402

WEB = os.path.join(ROOT, "web")
NUM_WORDS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
             "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen",
             "nineteen", "twenty"]
TOKEN = re.compile(r"\{\{([a-zA-Z0-9_.]+)\}\}")


def fill(template: str, values: dict) -> str:
    def lookup(m: re.Match) -> str:
        cur = values
        for part in m.group(1).split("."):
            if not isinstance(cur, dict) or part not in cur:
                raise KeyError(f"template value missing: {m.group(1)}")
            cur = cur[part]
        return str(cur)
    return TOKEN.sub(lookup, template)


def esc(s: str) -> str:
    return html.escape(s, quote=True)


def and_list(names: list[str]) -> str:
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


def phrase_buttons(packs: dict, order: list[str], shown: str, home: bool) -> str:
    """The quick-phrase buttons. Every button carries the phrase in every language, so the
    page can switch language without asking the server."""
    base = packs[order[0]].phrases
    ids = [p["id"] for p in base]
    by_lang = {c: {p["id"]: p for p in packs[c].phrases} for c in order}
    lines = []
    for p in base:
        attrs = " ".join(f'data-{c}="{esc(by_lang[c][p["id"]]["text"])}"' for c in order)
        extra = ' data-extra="1" hidden' if p.get("extra") else ""
        text = esc(by_lang[shown][p["id"]]["text"])
        if home:
            inner = f'<span class="qp-en">{esc(p["english"])}</span><span class="qp-te" lang="{shown}">{text}</span>'
        else:
            inner = f'<span class="qp-en" lang="{shown}">{text}</span>'
        lines.append(f'        <button type="button" class="qp" data-id="{p["id"]}" {attrs} '
                     f'aria-label="Speak: {esc(p["english"])}"{extra}>{inner}</button>\n')
    for c in order:
        missing = set(ids) - set(by_lang[c])
        if missing:
            raise SystemExit(f"lang/{c}/phrases.yaml is missing: {', '.join(sorted(missing))}")
    return "".join(lines)


def languages_js(packs: dict, order: list[str]) -> str:
    rows = []
    for c in order:
        m = packs[c].meta
        entry = {"name": m["name"], "native": m["native"], **m["ui"], "page": f"/{c}/"}
        rows.append(f"    {c}: " + json.dumps(entry, ensure_ascii=False))
    return "{\n" + ",\n".join(rows) + "\n  }"


def build(out: str, check: bool = False) -> list[str]:
    with open(os.path.join(WEB, "site.yaml"), encoding="utf-8") as f:
        site = yaml.safe_load(f)
    packs = load_all(with_prepare=check)
    order = site["languages"]
    for c in order:
        if c not in packs:
            raise SystemExit(f"site.yaml lists {c!r} but lang/{c}/ is missing or not live")
    default = site["default_language"]
    robots = "" if site.get("allow_search") else '<meta name="robots" content="noindex">\n'
    common = {"asset_version": site["asset_version"], "phrase_version": site["phrase_version"],
              "robots_meta": robots, "footer_extra": site["footer_extra"]}
    credits = site["credits"]

    def tpl(name: str) -> str:
        with open(os.path.join(WEB, "templates", name), encoding="utf-8") as f:
            return f.read()

    def write(rel: str, text: str) -> None:
        path = os.path.join(out, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        written.append(rel)

    written: list[str] = []
    if os.path.isdir(out):
        shutil.rmtree(out)
    shutil.copytree(os.path.join(WEB, "static"), out)

    # one page per language
    lang_tpl = tpl("lang.html")
    for c in order:
        m = packs[c].meta
        svc = m["voice"]["service"]
        others = " · ".join(f'<a href="/{o}/" lang="{o}">{packs[o].meta["native"]}</a>' for o in order if o != c)
        values = {**common, **m, "page": m["page"], "ui": m["ui"],
                  "phrase_buttons": phrase_buttons(packs, order, c, home=False),
                  "other_langs": others,
                  "voice_credit": f'{credits[svc]["page_prefix"]}: {credits[svc]["page"]}'}
        write(f"{c}/index.html", fill(lang_tpl, values))

    # home page: type in English, spoken in the chosen language
    parts = []
    for key in site["home_credit_order"]:
        if key == "translate":
            parts.append(credits["translate"]["home"])
            continue
        names = [packs[c].meta["name"] for c in order if packs[c].meta["voice"]["service"] == key]
        if names:
            parts.append(f'{and_list(names)} voice: {credits[key]["home"]}')
    d = packs[default].meta
    n = len(order)
    write("index.html", fill(tpl("home.html"), {
        **common, "default": {**d, "ui": d["ui"]},
        "phrase_buttons": phrase_buttons(packs, order, default, home=True),
        "voice_credits": " · ".join(parts),
        "language_count_words": NUM_WORDS[n] if n < len(NUM_WORDS) else str(n)}))
    write("about/index.html", fill(tpl("about.html"), common))
    write("app.js", fill(tpl("app.js"), {**common, "languages_js": languages_js(packs, order)}))

    if site.get("allow_search"):
        dom = site["domain"]
        write("robots.txt", f"User-agent: *\nDisallow: /api/\nSitemap: https://{dom}/sitemap.xml\n")
        urls = ["/", "/about/"] + [f"/{c}/" for c in order]
        body = "".join(f"  <url><loc>https://{dom}{u}</loc></url>\n" for u in urls)
        write("sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n'
              '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + body + "</urlset>\n")

    if check:                                     # every live pack must prepare its own phrases
        for c in order:
            prep = packs[c].prepare
            for p in packs[c].phrases:
                r = prep(p["text"])
                if not r.ok:
                    raise SystemExit(f"lang/{c}: phrase {p['id']!r} has words the voice cannot say")
    return written


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", required=True, help="folder to write the site into (replaced)")
    ap.add_argument("--check", action="store_true", help="also load every pack and check its phrases")
    a = ap.parse_args()
    files = build(a.out, a.check)
    print(f"wrote {len(files)} pages and files into {a.out}")


if __name__ == "__main__":
    main()
