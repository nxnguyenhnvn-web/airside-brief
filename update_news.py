#!/usr/bin/env python3
"""Collect aviation news from RSS/Atom feeds into data/news.json.

Uses only the Python standard library, so it runs anywhere Python 3.9+ is installed:
    python scripts/update_news.py

It merges new stories with the ones already saved, removes duplicates,
drops stories older than MAX_AGE_DAYS and keeps at most MAX_ITEMS.
"""
import html
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FEEDS_FILE = ROOT / "scripts" / "feeds.json"
NEWS_FILE = ROOT / "data" / "news.json"

MAX_AGE_DAYS = 30
MAX_ITEMS = 150
PER_FEED = 25
SUMMARY_CHARS = 220
UA = "Mozilla/5.0 (compatible; AirsideBrief/1.0; +https://github.com)"

# Keyword rules, checked in order; the first match sets the category.
RULES = [
    ("Safety & regulation", r"\b(crash|crashes|crashed|accident|incident|emergency landing|ntsb|faa|easa|caa|investigat\w*|grounded|grounding|turbulence|near.miss|safety|tai nạn|sự cố|cục hàng không)\b"),
    ("Manufacturers", r"\b(airbus|boeing|embraer|comac|bombardier|atr|deliveries|delivery|orders?|backlog|certification|certified|engine|pratt|rolls.royce|ge aerospace|cfm|evtol|737|787|a320|a321|a350|a220|777x)\b"),
    ("Airports", r"\b(airport|airports|runway|terminal|apron|sân bay|cảng hàng không|nhà ga|đường băng)\b"),
    ("Market", r"\b(iata|icao|demand|traffic|load factor|jet fuel|fuel price|profit|earnings|revenue|fares?|cargo|freight|outlook|forecast|rpk)\b"),
]
VN = re.compile(r"(vietnam|viet nam|việt nam|vietjet|vietravel|bamboo airways|pacific airlines|sun phuquoc|long th[aà]nh|t[aâ]n s[ơo]n nh[aấ]t|n[ộo]i b[àa]i|gia b[ìi]nh|đà nẵng|da nang|ph[úu] qu[ốo]c|hanoi|hà nội|ho chi minh|hồ chí minh|acv\b|hàng không)", re.I)

ATOM = "{http://www.w3.org/2005/Atom}"


def clean(text):
    text = html.unescape(re.sub(r"<[^>]+>", " ", text or ""))
    return re.sub(r"\s+", " ", text).strip()


def to_date(value):
    if not value:
        return None
    value = value.strip()
    try:
        dt = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def parse_feed(xml_bytes):
    """Return a list of dicts with title, link, published, summary, source from RSS 2.0 or Atom."""
    root = ET.fromstring(xml_bytes)
    out = []
    if root.tag == ATOM + "feed":
        for e in root.findall(ATOM + "entry"):
            link = ""
            for l in e.findall(ATOM + "link"):
                if l.get("rel", "alternate") == "alternate":
                    link = l.get("href", "")
                    break
            out.append({
                "title": clean(e.findtext(ATOM + "title")),
                "link": link,
                "published": to_date(e.findtext(ATOM + "published") or e.findtext(ATOM + "updated")),
                "summary": clean(e.findtext(ATOM + "summary") or e.findtext(ATOM + "content")),
                "source": "",
            })
    else:
        for i in root.iter("item"):
            out.append({
                "title": clean(i.findtext("title")),
                "link": (i.findtext("link") or "").strip(),
                "published": to_date(i.findtext("pubDate") or i.findtext("{http://purl.org/dc/elements/1.1/}date")),
                "summary": clean(i.findtext("description")),
                "source": clean(i.findtext("source")),
            })
    return out


def categorize(text, fallback):
    low = text.lower()
    for cat, pattern in RULES:
        if re.search(pattern, low, re.I):
            return cat
    return fallback


def norm_title(t):
    return re.sub(r"[^a-z0-9à-ỹ]+", "", t.lower())[:90]


def to_item(raw, feed):
    title, source = raw["title"], raw["source"]
    google = "news.google.com" in feed["url"]
    # Google News titles end in " - Publisher"
    if google and " - " in title:
        title, pub = title.rsplit(" - ", 1)
        source = source or pub
    summary = raw["summary"]
    if google or summary.lower().startswith(title.lower()[:40]):
        summary = ""  # Google News descriptions only repeat the headline
    if len(summary) > SUMMARY_CHARS:
        summary = summary[:SUMMARY_CHARS].rsplit(" ", 1)[0] + "…"
    text = f"{title} {summary}"
    return {
        "date": raw["published"].strftime("%Y-%m-%d"),
        "ts": raw["published"].isoformat(),
        "cat": categorize(text, feed.get("cat", "Airlines")),
        "vn": bool(feed.get("vn")) or bool(VN.search(text)),
        "title": title.strip(),
        "sum": summary,
        "src": source or feed["name"],
        "url": raw["link"],
    }


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read()


def main():
    feeds = json.loads(FEEDS_FILE.read_text(encoding="utf-8"))["feeds"]
    try:
        existing = json.loads(NEWS_FILE.read_text(encoding="utf-8")).get("items", [])
    except FileNotFoundError:
        existing = []

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=MAX_AGE_DAYS)
    fresh, ok = [], 0
    for feed in feeds:
        try:
            raws = parse_feed(fetch(feed["url"]))
        except Exception as exc:  # one bad feed must not stop the update
            print(f"  ! {feed['name']}: {exc}", file=sys.stderr)
            continue
        ok += 1
        raws = [r for r in raws if r["title"] and r["link"] and r["published"] and cutoff <= r["published"] <= now + timedelta(hours=6)]
        raws.sort(key=lambda r: r["published"], reverse=True)
        items = [to_item(r, feed) for r in raws[:PER_FEED]]
        print(f"  {feed['name']}: {len(items)} items")
        fresh.extend(items)

    if ok == 0:
        print("No feed could be read; leaving news.json unchanged.", file=sys.stderr)
        return 1

    merged, seen = [], set()
    # newest first, fresh items win over saved ones with the same headline
    for it in sorted(fresh, key=lambda x: x.get("ts", x["date"]), reverse=True) + existing:
        key = norm_title(it["title"])
        if not key or key in seen or it.get("url") in seen:
            continue
        if it["date"] < cutoff.strftime("%Y-%m-%d"):
            continue
        seen.add(key)
        seen.add(it.get("url"))
        merged.append(it)
    merged.sort(key=lambda x: x.get("ts", x["date"] + "T00:00:00+00:00"), reverse=True)
    merged = merged[:MAX_ITEMS]

    NEWS_FILE.parent.mkdir(parents=True, exist_ok=True)
    NEWS_FILE.write_text(json.dumps({"updated": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "items": merged}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Saved {len(merged)} stories from {ok}/{len(feeds)} feeds.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
