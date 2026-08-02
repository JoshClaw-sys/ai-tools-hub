#!/usr/bin/env python3
"""
Generate LinkedIn article drafts from each AI Tools Hub guide.

LinkedIn articles get ranked in Google search and reach professional AI users
(high-value audience for affiliate revenue). This script extracts the content
from each article and reformats it as a LinkedIn-friendly post.

Workflow:
1. Run this script → generates linkedin_articles/ folder with .md drafts
2. Open LinkedIn → click "Write article" → paste each draft
3. Publish → LinkedIn notifies your network + ranks in Google
"""
import os
import sys
import json
import re
import subprocess
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path("/home/beryl-server/projects/ai-for-india")
OUTPUT_DIR = ROOT / "linkedin_articles"
OUTPUT_DIR.mkdir(exist_ok=True)


def html_to_text(html):
    """Strip HTML tags to plain text for LinkedIn drafts."""
    text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
    text = re.sub(r'<h[1-6][^>]*>(.*?)</h[1-6]>', r'\n\n## \1\n\n', text, flags=re.DOTALL)
    text = re.sub(r'<p[^>]*>', '\n\n', text)
    text = re.sub(r'</p>', '', text)
    text = re.sub(r'<strong[^>]*>(.*?)</strong>', r'**\1**', text, flags=re.DOTALL)
    text = re.sub(r'<em[^>]*>(.*?)</em>', r'*\1*', text, flags=re.DOTALL)
    text = re.sub(r'<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', r'[\2](\1)', text, flags=re.DOTALL)
    text = re.sub(r'<li[^>]*>', '\n- ', text)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def linkedin_format(meta, body_html):
    """Reformat as LinkedIn article."""
    text = html_to_text(body_html)
    word_count = len(text.split())

    # LinkedIn articles: hook + 3-5 sections + CTA
    # First 150 chars are critical (preview in feed)
    hook = text[:150].replace("\n", " ").strip()
    if not hook.endswith((".", "?", "!")):
        hook += "..."

    linkedin_post = f"""# {meta['title']}

*{meta['short_title']} — Published {meta['date_display']} on AI Tools Hub*

---

## The Quick Take

{meta.get('tldr_pick', meta.get('description', ''))}

I tested the top {meta['category'].replace('-', ' ')} tools so you don't have to.

Here's what actually won — and what to skip.

---

{text[:3000]}

---

## Why I Wrote This

I run AI Tools Hub (https://joshclaw-sys.github.io/ai-tools-hub/), where we test AI tools with real workflows and publish honest buying guides.

Most AI reviews are affiliate-driven noise. We're not. We test, rank, and tell you what to skip.

## What's Next

If you want more guides like this — new tools, monthly updates, no sponsored rankings — follow AI Tools Hub on LinkedIn.

👉 Full guide with all picks, comparison table, and methodology:
**https://joshclaw-sys.github.io/ai-tools-hub/articles/{meta['slug']}.html**

---

*What's your experience with {meta['short_title']}? Drop a comment — I read every one.*

#AI #MachineLearning #{meta['category'].replace('-', '').title()} #Productivity
"""
    return linkedin_post


def main():
    articles_dir = ROOT / "articles"
    count = 0

    for article_dir in sorted(articles_dir.iterdir()):
        if not article_dir.is_dir():
            continue
        meta_file = article_dir / "meta.json"
        body_file = article_dir / "body.html"
        if not meta_file.exists() or not body_file.exists():
            continue

        meta = json.loads(meta_file.read_text())
        body_html = body_file.read_text()
        linkedin_post = linkedin_format(meta, body_html)

        out_file = OUTPUT_DIR / f"{article_dir.name}.md"
        out_file.write_text(linkedin_post)
        count += 1
        print(f"  ✓ {meta['title'][:60]}")

    print(f"\n✅ Generated {count} LinkedIn article drafts in {OUTPUT_DIR}/")
    print(f"\nNext: Open LinkedIn → Write article → paste each draft → publish")
    print(f"Recommended cadence: 1 article/week on LinkedIn")


if __name__ == "__main__":
    main()
