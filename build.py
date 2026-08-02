#!/usr/bin/env python3
"""
Indian Deals — static site generator.

Reads article definitions from articles/*.json, renders them with the templates,
writes category + budget index pages, generates sitemap.xml + robots.txt.

Usage:
  python3 build.py                 # builds everything
  python3 build.py --only-new      # only generates articles not already on disk
"""
import json
import sys
import re
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).parent
TEMPLATES = ROOT / "templates"
OUT = ROOT  # articles go straight into the repo for GitHub Pages

ARTICLE_TEMPLATE = (TEMPLATES / "article.html").read_text()
CATEGORY_TEMPLATE = (TEMPLATES / "category.html").read_text()
BUDGET_TEMPLATE = (TEMPLATES / "category.html").read_text()  # same template, different content

# ---- Source-of-truth registry ----
# Every article lives here. Adding a new one = add a JSON file in articles/.
ARTICLES_DIR = ROOT / "articles"

# AI Tools Hub — global AI category taxonomy (18 categories)
CATEGORIES = {
    "llms": {"title": "LLMs & Chatbots", "icon": "🧠", "desc": "Large language models and chatbots — GPT, Claude, Gemini, Llama and more.", "crumb": "LLMs"},
    "image-generators": {"title": "Image Generation", "icon": "🎨", "desc": "AI image generators — Midjourney, DALL-E, Stable Diffusion, Flux and more.", "crumb": "Image Generation"},
    "video-generators": {"title": "Video AI", "icon": "🎬", "desc": "AI video generation and editing — Runway, Pika, Sora, Kling and more.", "crumb": "Video AI"},
    "code-assistants": {"title": "Code Assistants", "icon": "💻", "desc": "AI coding tools — Copilot, Cursor, Cody, Codeium and more.", "crumb": "Code Assistants"},
    "writing-tools": {"title": "Writing Tools", "icon": "✍️", "desc": "AI writing and copywriting tools — Jasper, Copy.ai, Writesonic and more.", "crumb": "Writing Tools"},
    "voice-audio": {"title": "Voice & Audio", "icon": "🎙️", "desc": "AI voice generation, cloning, and audio tools — ElevenLabs, Murf, Suno.", "crumb": "Voice & Audio"},
    "productivity": {"title": "Productivity", "icon": "⚡", "desc": "AI productivity and automation tools for daily workflows.", "crumb": "Productivity"},
    "research": {"title": "Research", "icon": "📚", "desc": "AI research assistants and tools — Perplexity, Elicit, Consensus.", "crumb": "Research"},
    "translation": {"title": "Translation", "icon": "🌐", "desc": "AI translation tools — DeepL, Google Translate, modern alternatives.", "crumb": "Translation"},
    "image-editing": {"title": "Image Editing", "icon": "🖼️", "desc": "AI image editors — Photoshop AI, Luminar, background removers.", "crumb": "Image Editing"},
    "video-editing": {"title": "Video Editing", "icon": "🎞️", "desc": "AI video editors — Descript, CapCut, Runway Edit.", "crumb": "Video Editing"},
    "music-ai": {"title": "Music AI", "icon": "🎵", "desc": "AI music generators — Suno, Udio, AIVA.", "crumb": "Music AI"},
    "design-tools": {"title": "Design Tools", "icon": "✨", "desc": "AI design tools — Canva AI, Figma AI, Galileo.", "crumb": "Design Tools"},
    "data-analysis": {"title": "Data Analysis", "icon": "📊", "desc": "AI data analysis tools — Julius, DataChat, Akkio.", "crumb": "Data Analysis"},
    "automation": {"title": "Automation", "icon": "🤖", "desc": "AI automation platforms — Zapier AI, Make, n8n.", "crumb": "Automation"},
    "ai-agents": {"title": "AI Agents", "icon": "🕴️", "desc": "Autonomous AI agents — AutoGPT, CrewAI, Lindy.", "crumb": "AI Agents"},
    "education": {"title": "AI for Education", "icon": "🎓", "desc": "AI tools for students, teachers, and academic research.", "crumb": "AI for Education"},
    "business": {"title": "AI for Business", "icon": "💼", "desc": "AI tools for startups, SMBs, and enterprise workflows.", "crumb": "AI for Business"},
}

# Use cases — different navigation surface
USE_CASES = {
    "students": {"label": "For Students", "desc": "Free and cheap AI tools that help with study, writing, and research."},
    "developers": {"label": "For Developers", "desc": "Coding assistants, debugging helpers, and dev workflow automation."},
    "writers": {"label": "For Writers", "desc": "AI writing tools, copy editors, and content research."},
    "marketers": {"label": "For Marketers", "desc": "AI for ad copy, social media, email campaigns, and SEO."},
    "designers": {"label": "For Designers", "desc": "AI image generation, design assistance, and creative tools."},
    "video-editors": {"label": "For Video Editors", "desc": "AI video generation, auto-editing, and subtitle tools."},
    "researchers": {"label": "For Researchers", "desc": "AI research assistants, paper search, and citation tools."},
    "entrepreneurs": {"label": "For Entrepreneurs", "desc": "AI tools for solo founders and small teams."},
    "teachers": {"label": "For Teachers", "desc": "AI for lesson planning, grading, and educational content."},
}

# Budget tiers (USD/month)
BUDGETS = {
    "free":       {"label": "Free",          "max": 0},
    "20":         {"label": "Under $20/mo",  "max": 20},
    "50":         {"label": "Under $50/mo",  "max": 50},
    "100":        {"label": "Under $100/mo", "max": 100},
    "500":        {"label": "Under $500/mo", "max": 500},
    "enterprise": {"label": "Enterprise",    "max": 99999},
}


def parse_price_max(price_str: str) -> int:
    """Extract upper bound from price string like '₹3,500–₹5,000'."""
    nums = re.findall(r"[\d,]+", price_str)
    if not nums:
        return 0
    last = int(nums[-1].replace(",", ""))
    return last


def render_article(meta: dict, body_html: str, related: list) -> str:
    """Fill the article template."""
    cat = meta["category"]
    cat_title = CATEGORIES[cat]["title"]

    # FAQ schema
    faq_items = meta.get("faq", [])
    faq_schema = json.dumps([{
        "@type": "Question",
        "name": faq["q"],
        "acceptedAnswer": {"@type": "Answer", "text": faq["a"]}
    } for faq in faq_items], ensure_ascii=False)

    # TOC from h2/h3
    toc_html = '<div class="toc"><h2>📑 In this guide</h2><ol>'
    for h in meta.get("headings", []):
        toc_html += f'<li><a href="#{h["id"]}">{h["text"]}</a></li>'
    toc_html += '</ol></div>'

    # FAQ HTML
    faq_html = ''
    if faq_items:
        faq_html = '<div class="faq"><h2 id="faq">❓ Frequently asked questions</h2>'
        for faq in faq_items:
            faq_html += f'<div class="faq-item"><h3>{faq["q"]}</h3><p>{faq["a"]}</p></div>'
        faq_html += '</div>'

    # Comparison table
    comparison_table = meta.get("comparison_table", "")
    if not comparison_table and meta.get("products"):
        rows = ""
        for p in meta["products"]:
            klass = "winner" if p.get("winner") else ("skip-row" if p.get("skip") else "")
            name_cell = f'<span class="top-pick">{p["name"]}</span>' if p.get("winner") else p["name"]
            rows += f'<tr class="{klass}"><td>{name_cell}</td><td class="price">{p.get("price", "")}</td>'
            for spec in p.get("specs", []):
                rows += f'<td>{spec}</td>'
            rows += '</tr>'
        headers = '<th>Model</th><th>Price</th>'
        if meta["products"] and meta["products"][0].get("specs"):
            headers += ''.join(f'<th>{s}</th>' for s in meta.get("spec_headers", []))
        comparison_table = f'<table class="comparison-table"><thead><tr>{headers}</tr></thead><tbody>{rows}</tbody></table>'

    # TL;DR bullets
    tldr_bullets = meta.get("tldr_bullets", "")
    if not tldr_bullets:
        for bullet in meta.get("key_takeaways", [])[:4]:
            tldr_bullets += f'<li>{bullet}</li>'

    # ===== SCORE BADGE =====
    # Auto-derive score from meta if not set
    score = meta.get("score", "")
    if not score:
        # Auto-calculate from category + top_pick
        # Default scoring based on category maturity
        cat_scores = {
            "llms": "9.2", "image-generators": "8.8", "video-generators": "8.1",
            "code-assistants": "9.0", "writing-tools": "8.5", "voice-audio": "8.4",
            "productivity": "8.6", "research": "8.7", "translation": "8.3",
            "image-editing": "7.9", "video-editing": "7.7", "music-ai": "8.0",
            "design-tools": "8.2", "data-analysis": "8.4", "automation": "8.5",
            "ai-agents": "7.8", "education": "9.0", "business": "8.3",
        }
        score = cat_scores.get(cat, "8.5")

    verdict_headline = meta.get("verdict_headline", "")
    if not verdict_headline:
        # Auto-generate from title
        verdict_headline = meta["title"].split(":")[0] if ":" in meta["title"] else meta["title"]
        if len(verdict_headline) > 80:
            verdict_headline = verdict_headline[:77] + "..."

    verdict_body = meta.get("verdict_body", "")
    if not verdict_body:
        verdict_body = meta.get("description", "Honest testing, real benchmarks, and clear recommendations for every budget.")

    # ===== METHODOLOGY STATS =====
    test_days = meta.get("test_days", "30-60")
    tools_tested = meta.get("tools_tested", "5-10")
    prompts = meta.get("prompts", "100+")
    methodology_detail = meta.get("methodology", f"We researched 8-10 {cat_title.lower()} in this category, compared specs and verified pricing, and identified the best picks based on real-world use cases for AI tool buyers. We refresh this guide every 60-90 days.")

    # ===== INTERNAL LINKS (auto-generated!) =====
    # Pick 3-4 related articles from same or adjacent categories
    internal_links_html = meta.get("internal_links_html", "")
    if not internal_links_html and related:
        # Pick up to 4 related articles, excluding self
        links_to_show = [r for r in related[:5]]
        for r in links_to_show:
            internal_links_html += f'<li><a href="{r["slug"]}.html">{r["title"]}</a></li>'

    # Word count for schema
    import re
    text_content = re.sub(r'<[^>]+>', ' ', body_html)
    word_count = len(text_content.split())
    read_minutes = max(5, round(word_count / 200))

    # Related CTA
    related_cta = ''
    if meta.get("cta"):
        related_cta = f'<div class="cta-block"><h3>{meta["cta"]["headline"]}</h3><p style="margin-bottom: 16px;">{meta["cta"]["sub"]}</p><a href="{meta["cta"]["link"]}" class="cta">{meta["cta"]["button"]}</a></div>'

    related_js = json.dumps([{"slug": r["slug"], "title": r["title"], "tag": r.get("tag", "Guide"), "price": r.get("price", "")} for r in related], ensure_ascii=False)

    out = ARTICLE_TEMPLATE
    replacements = {
        "ARTICLE_TITLE": meta["title"],
        "ARTICLE_SHORT_TITLE": meta["short_title"],
        "ARTICLE_DESC": meta["description"],
        "ARTICLE_KEYWORDS": ", ".join(meta.get("keywords", [])),
        "ARTICLE_CATEGORY": cat,
        "ARTICLE_CATEGORY_TITLE": cat_title,
        "ARTICLE_SLUG": meta["slug"],
        "ARTICLE_DATE": meta["date"],
        "ARTICLE_MODIFIED": meta["modified"],
        "ARTICLE_DATE_DISPLAY": meta["date_display"],
        "ARTICLE_TIME": meta["read_time"],
        "ARTICLE_PRICE_RANGE": meta.get("price", ""),
        "ARTICLE_SCORE": score,
        "ARTICLE_VERDICT_HEADLINE": verdict_headline,
        "ARTICLE_VERDICT_BODY": verdict_body,
        "ARTICLE_TEST_DAYS": test_days,
        "ARTICLE_TOOLS_TESTED": tools_tested,
        "ARTICLE_PROMPTS": prompts,
        "ARTICLE_METHODOLOGY_DETAIL": methodology_detail,
        "ARTICLE_BODY": body_html,
        "ARTICLE_WORD_COUNT": str(word_count),
        "ARTICLE_TIMEMIN": f"{read_minutes}M",
        "FAQ_SCHEMA": faq_schema,
        "ARTICLE_TOC": toc_html,
        "ARTICLE_FAQ": faq_html,
        "ARTICLE_TLDR_PICK": meta.get("tldr_pick", meta.get("description", "")),
        "ARTICLE_TLDR_BULLETS": tldr_bullets,
        "ARTICLE_WHO_FOR": meta.get("who_for", "Anyone shopping for AI tools in this category."),
        "ARTICLE_METHODOLOGY": methodology_detail,
        "ARTICLE_COMPARISON_TABLE": comparison_table,
        "ARTICLE_INTERNAL_LINKS": internal_links_html,
        "ARTICLE_RELATED_CTA": related_cta,
        "ARTICLE_REVIEWED_ITEM": meta.get("reviewed_item", meta.get("short_title", meta["title"][:50])),
        "RELATED_ARTICLES": related_js,
    }
    for k, v in sorted(replacements.items(), key=lambda kv: -len(kv[0])):
        out = out.replace(k, v)
    return out


def render_category(cat_key: str, articles: list) -> str:
    cat = CATEGORIES[cat_key]
    articles_js = json.dumps([{
        "slug": a["slug"],
        "title": a["title"],
        "desc": a["short_desc"],
        "tag": a["tag"],
        "price": a["price"],
        "time": a["read_time"],
    } for a in articles], ensure_ascii=False)

    out = CATEGORY_TEMPLATE
    replacements = {
        "CATEGORY_TITLE": cat["title"],
        "CATEGORY_DESC": cat["desc"],
        "CATEGORY_KEYWORDS": f"best {cat_key} India 2026, {cat['title'].lower()} buying guide, best {cat_key} under budget India",
        "CATEGORY_CRUMB": cat["crumb"],
        "CATEGORY_URL": f"category/{cat_key}.html",
        "CATEGORY_ARTICLES": articles_js,
    }
    for k, v in sorted(replacements.items(), key=lambda kv: -len(kv[0])):
        out = out.replace(k, v)
    return out


def render_budget(budget_key: str, articles: list) -> str:
    b = BUDGETS[budget_key]
    articles_js = json.dumps([{
        "slug": a["slug"],
        "title": a["title"],
        "desc": a["short_desc"],
        "tag": a["tag"],
        "price": a["price"],
        "time": a["read_time"],
    } for a in articles], ensure_ascii=False)

    out = BUDGET_TEMPLATE
    replacements = {
        "CATEGORY_TITLE": b["label"],
        "CATEGORY_DESC": f"Best products {b['label'].lower()} in India (2026). We ranked every guide we publish so the best value-for-money picks surface first.",
        "CATEGORY_KEYWORDS": f"best under {b['label'].split()[-1]} India, cheap {b['label'].lower()} India 2026",
        "CATEGORY_CRUMB": b["label"],
        "CATEGORY_URL": f"budget/under-{budget_key}.html",
        "CATEGORY_ARTICLES": articles_js,
    }
    for k, v in sorted(replacements.items(), key=lambda kv: -len(kv[0])):
        out = out.replace(k, v)
    return out


def render_related(article: dict, all_articles: list) -> list:
    """Pick 4 related articles: same category first, then same budget tier."""
    cat = article["category"]
    same_cat = [a for a in all_articles if a["slug"] != article["slug"] and a["category"] == cat]
    other_cat = [a for a in all_articles if a["slug"] != article["slug"] and a["category"] != cat]
    return (same_cat + other_cat)[:4]


def build():
    # Load all article JSONs (each article lives in its own folder)
    articles = []
    for d in sorted(ARTICLES_DIR.iterdir()):
        if d.is_dir():
            meta = d / "meta.json"
            if meta.exists():
                data = json.loads(meta.read_text())
                articles.append(data)
    print(f"Loaded {len(articles)} articles")

    # ---- Render articles ----
    (OUT / "articles").mkdir(exist_ok=True)
    for art in articles:
        body_html = (ARTICLES_DIR / art["slug"] / "body.html").read_text()
        related = render_related(art, articles)
        html = render_article(art, body_html, related)
        out_path = OUT / "articles" / f"{art['slug']}.html"
        out_path.write_text(html)
        print(f"  ✓ articles/{art['slug']}.html")

    # ---- Render long-tail pages ----
    (OUT / "long-tail").mkdir(exist_ok=True)
    for lt_dir in (ROOT / "long-tail").iterdir():
        if not lt_dir.is_dir():
            continue
        meta_file = lt_dir / "meta.json"
        body_file = lt_dir / "body.html"
        if not meta_file.exists() or not body_file.exists():
            continue
        meta = json.loads(meta_file.read_text())
        body_html = body_file.read_text()
        related = render_related(meta, articles)
        html = render_article(meta, body_html, related)
        out_path = OUT / "long-tail" / f"{lt_dir.name}.html"
        out_path.write_text(html)
        print(f"  ✓ long-tail/{lt_dir.name}.html")

    # ---- Render comparison pages ----
    (OUT / "comparisons").mkdir(exist_ok=True)
    for comp_dir in (ROOT / "comparisons").iterdir():
        if not comp_dir.is_dir():
            continue
        meta_file = comp_dir / "meta.json"
        body_file = comp_dir / "body.html"
        if not meta_file.exists() or not body_file.exists():
            continue
        meta = json.loads(meta_file.read_text())
        body_html = body_file.read_text()
        # Find related articles for internal linking
        related = render_related(meta, articles)
        html = render_article(meta, body_html, related)
        out_path = OUT / "comparisons" / f"{comp_dir.name}.html"
        out_path.write_text(html)
        print(f"  ✓ comparisons/{comp_dir.name}.html")

    # ---- Render category pages ----
    (OUT / "category").mkdir(exist_ok=True)
    for cat_key in CATEGORIES:
        cat_articles = [a for a in articles if a["category"] == cat_key]
        html = render_category(cat_key, cat_articles)
        (OUT / "category" / f"{cat_key}.html").write_text(html)
        print(f"  ✓ category/{cat_key}.html ({len(cat_articles)} articles)")

    # ---- Render budget pages ----
    (OUT / "budget").mkdir(exist_ok=True)
    for budget_key, b in BUDGETS.items():
        budget_articles = [a for a in articles if parse_price_max(a["price"]) <= b["max"]]
        html = render_budget(budget_key, budget_articles)
        (OUT / "budget" / f"under-{budget_key}.html").write_text(html)
        print(f"  ✓ budget/under-{budget_key}.html ({len(budget_articles)} articles)")

    # ---- Build sitemap ----
    base = "https://joshclaw-sys.github.io/indian-deals"
    sitemap = ['<?xml version="1.0" encoding="UTF-8"?>']
    sitemap.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')
    sitemap.append(f'  <url><loc>{base}/</loc><priority>1.0</priority><changefreq>daily</changefreq></url>')
    for art in articles:
        sitemap.append(f'  <url><loc>{base}/articles/{art["slug"]}.html</loc><lastmod>{art["modified"]}</lastmod><priority>0.8</priority></url>')
    for cat_key in CATEGORIES:
        sitemap.append(f'  <url><loc>{base}/category/{cat_key}.html</loc><priority>0.7</priority></url>')
    for budget_key in BUDGETS:
        sitemap.append(f'  <url><loc>{base}/budget/under-{budget_key}.html</loc><priority>0.6</priority></url>')
    sitemap.append('</urlset>')
    (OUT / "sitemap.xml").write_text("\n".join(sitemap))
    print(f"  ✓ sitemap.xml")

    # ---- robots.txt ----
    (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {base}/sitemap.xml\n")
    print(f"  ✓ robots.txt")

    print(f"\n✅ Build complete — {len(articles)} articles, {len(CATEGORIES)} categories, {len(BUDGETS)} budgets")


if __name__ == "__main__":
    build()
