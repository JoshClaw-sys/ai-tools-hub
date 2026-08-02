#!/usr/bin/env python3
"""
Substack newsletter auto-import via RSS.

Generates a newsletter-digest.html file from the latest articles on the
AI Tools Hub site. When paired with a Substack RSS import URL, your
newsletter auto-updates as new articles publish.

Setup:
1. Create a Substack publication
2. In Substack dashboard → Settings → Import → paste the RSS URL of
   https://joshclaw-sys.github.io/ai-tools-hub/feed.xml
3. New articles will auto-import as drafts for review before sending
"""
import os
import sys
import json
import urllib.request
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path("/home/beryl-server/projects/ai-for-india")
ARTICLES_DIR = ROOT / "articles"
OUTPUT = ROOT / "feed.xml"

# Substack-style RSS feed
RSS_HEADER = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
<channel>
<title>AI Tools Hub Weekly Digest</title>
<link>https://joshclaw-sys.github.io/ai-tools-hub/</link>
<description>Honest, no-fluff AI tool reviews for 2026. New guides every week.</description>
<language>en-us</language>
<atom:link href="https://joshclaw-sys.github.io/ai-tools-hub/feed.xml" rel="self" type="application/rss+xml" />
"""

RSS_FOOTER = """</channel>
</rss>
"""

ITEM_TEMPLATE = """<item>
<title>{title}</title>
<link>{url}</link>
<description>{description}</description>
<pubDate>{pub_date}</pubDate>
<guid isPermaLink="true">{url}</guid>
<category>{category}</category>
</item>
"""


def main():
    items = []
    for article_dir in sorted(ARTICLES_DIR.iterdir()):
        if not article_dir.is_dir():
            continue
        meta_file = article_dir / "meta.json"
        if not meta_file.exists():
            continue
        meta = json.loads(meta_file.read_text())
        url = f"https://joshclaw-sys.github.io/ai-tools-hub/articles/{article_dir.name}.html"

        # Convert ISO date to RFC 822 for RSS
        try:
            dt = datetime.fromisoformat(meta["date"])
            pub_date = dt.strftime("%a, %d %b %Y 00:00:00 GMT")
        except Exception:
            pub_date = "Mon, 01 Jan 2026 00:00:00 GMT"

        items.append(ITEM_TEMPLATE.format(
            title=meta["title"],
            url=url,
            description=meta["description"],
            pub_date=pub_date,
            category=meta["category"],
        ))

    feed = RSS_HEADER + "\n".join(items) + RSS_FOOTER
    OUTPUT.write_text(feed)
    print(f"✓ Generated RSS feed: {OUTPUT}")
    print(f"  Articles: {len(items)}")
    print(f"  Substack import URL: https://joshclaw-sys.github.io/ai-tools-hub/feed.xml")


if __name__ == "__main__":
    main()
