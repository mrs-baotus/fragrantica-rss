#!/usr/bin/env python3
"""Create personal RSS feeds from the public Fragrantica home page.

This project links to Fragrantica and retains only feed metadata (titles,
URLs, categories, publication dates, and short page-provided summaries).
"""
from __future__ import annotations

import html
import json
import re
from datetime import UTC, datetime
from email.utils import format_datetime
from pathlib import Path
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET

SOURCE_URL = "https://www.fragrantica.com/"
SITE_URL = "https://www.fragrantica.com"
ROOT = Path(__file__).resolve().parent
DOCS = ROOT / "docs"
STATE_PATH = ROOT / "data" / "seen.json"
USER_AGENT = "FragranticaRSS/1.0 (personal RSS feed; links back to source)"
MAX_ITEMS = 100


def clean(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value)
    return " ".join(html.unescape(value).split())


def fetch_homepage() -> str:
    request = Request(SOURCE_URL, headers={"User-Agent": USER_AGENT, "Accept": "text/html"})
    with urlopen(request, timeout=30) as response:
        if response.status != 200:
            raise RuntimeError(f"Fragrantica returned HTTP {response.status}")
        return response.read().decode("utf-8", errors="replace")


def parse_news(page: str) -> list[dict]:
    items: dict[str, dict] = {}
    for article in re.findall(r"<article\b.*?</article>", page, flags=re.IGNORECASE | re.DOTALL):
        link = re.search(r'<a\s+href="(?P<href>/news/[^"?#]+\.html)"[^>]*aria-label="(?P<title>[^"]+)"', article, re.I)
        if not link:
            continue
        title = clean(link.group("title"))
        summary_match = re.search(r"<p\b[^>]*>(.*?)</p>", article, re.I | re.S)
        span_values = [clean(v) for v in re.findall(r"<span\b[^>]*>(.*?)</span>", article, re.I | re.S)]
        epoch_match = re.search(r'unixtime="(\d+)"', article)
        epoch = int(epoch_match.group(1)) if epoch_match else None
        url = SITE_URL + link.group("href")
        items[url] = {
            "title": title,
            "link": url,
            "description": clean(summary_match.group(1)) if summary_match else "",
            "category": span_values[0] if span_values else "News",
            "author": span_values[1] if len(span_values) > 1 else "Fragrantica",
            "published": epoch,
        }
    return list(items.values())


def parse_perfumes(page: str) -> list[dict]:
    items: dict[str, dict] = {}
    pattern = re.compile(
        r'<a\s+href="(?P<href>/perfume/[^"?#]+\.html)"\s+class="tw-carousel-perfume-card[^>]*>(?P<body>.*?)</a>',
        re.I | re.S,
    )
    for match in pattern.finditer(page):
        values = [clean(v) for v in re.findall(r"<p\b[^>]*>(.*?)</p>", match.group("body"), re.I | re.S)]
        if len(values) < 2:
            continue
        brand, perfume = values[0], values[1]
        url = SITE_URL + match.group("href")
        items[url] = {
            "title": f"{brand} — {perfume}",
            "link": url,
            "description": f"New perfume listing: {perfume} by {brand}.",
            "category": "New Perfumes",
            "author": brand,
            "published": None,
        }
    return list(items.values())


def load_state() -> dict[str, list[dict]]:
    if not STATE_PATH.exists():
        return {"news": [], "perfumes": []}
    try:
        state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        return {key: state.get(key, []) for key in ("news", "perfumes")}
    except (OSError, json.JSONDecodeError):
        return {"news": [], "perfumes": []}


def merge(current: list[dict], old: list[dict]) -> list[dict]:
    merged: dict[str, dict] = {item["link"]: item for item in old}
    for item in current:
        merged[item["link"]] = item
    now = int(datetime.now(UTC).timestamp())
    return sorted(merged.values(), key=lambda x: x["published"] or now, reverse=True)[:MAX_ITEMS]


def pub_date(item: dict) -> str:
    timestamp = item.get("published") or int(datetime.now(UTC).timestamp())
    return format_datetime(datetime.fromtimestamp(timestamp, UTC), usegmt=True)


def write_rss(filename: str, title: str, description: str, items: list[dict]) -> None:
    rss = ET.Element("rss", version="2.0")
    channel = ET.SubElement(rss, "channel")
    ET.SubElement(channel, "title").text = title
    ET.SubElement(channel, "link").text = SOURCE_URL
    ET.SubElement(channel, "description").text = description
    ET.SubElement(channel, "language").text = "en"
    ET.SubElement(channel, "lastBuildDate").text = format_datetime(datetime.now(UTC), usegmt=True)
    for entry in items:
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = entry["title"]
        ET.SubElement(item, "link").text = entry["link"]
        ET.SubElement(item, "guid", isPermaLink="true").text = entry["link"]
        ET.SubElement(item, "description").text = entry["description"]
        ET.SubElement(item, "category").text = entry["category"]
        ET.SubElement(item, "author").text = entry["author"]
        ET.SubElement(item, "pubDate").text = pub_date(entry)
    ET.indent(rss, space="  ")
    (DOCS / filename).write_bytes(b'<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(rss, encoding="utf-8"))


def main() -> None:
    page = fetch_homepage()
    current = {"news": parse_news(page), "perfumes": parse_perfumes(page)}
    if not current["news"] or not current["perfumes"]:
        raise RuntimeError("Could not find both news and new-perfume cards; page layout may have changed.")
    state = load_state()
    state = {key: merge(current[key], state[key]) for key in state}
    DOCS.mkdir(exist_ok=True)
    STATE_PATH.parent.mkdir(exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_rss("news.xml", "Unofficial Fragrantica News", "Recent Fragrantica news; titles and links point to the original source.", state["news"])
    write_rss("new-perfumes.xml", "Unofficial Fragrantica New Perfumes", "Recently listed perfumes on Fragrantica; titles and links point to the original source.", state["perfumes"])
    print(f"Wrote {len(state['news'])} news items and {len(state['perfumes'])} perfume items.")


if __name__ == "__main__":
    main()
