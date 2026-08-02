#!/usr/bin/env python3
"""
Real browser-based directory submission.

Uses Playwright (headless Chromium) to:
1. Open each directory's submit page in a real browser
2. Detect and fill the form fields (URL, name, description)
3. Submit the form
4. Capture screenshot for verification

This handles JavaScript-rendered forms that urllib can't.
"""
import os
import sys
import json
import asyncio
import argparse
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright

ROOT = Path(__file__).parent
LOG_FILE = ROOT / "submit_log.json"
SCREENSHOTS_DIR = ROOT / "submission_screenshots"
SCREENSHOTS_DIR.mkdir(exist_ok=True)

SITE_INFO = {
    "name": "AI Tools Hub",
    "tagline": "Honest, no-fluff AI tool reviews for 2026.",
    "url": "https://joshclaw-sys.github.io/ai-tools-hub/",
    "description": (
        "AI Tools Hub is the no-nonsense guide to AI tools that matter in 2026. "
        "We test every tool with real workflows — writing, coding, research, "
        "image generation, voice — and rank them honestly. No sponsored fluff, "
        "no affiliate bias. Every article includes a clear top pick, best for "
        "recommendations, a side-by-side comparison table, specific test "
        "methodology, and an honest skip-this section when a popular tool "
        "doesn't deliver. Updated monthly as the AI landscape shifts."
    ),
    "category": "AI Tools",
    "email": "hello@ai-tools-hub.example",
}

# Form field patterns we know how to fill
FIELD_PATTERNS = {
    "url": ["url", "site_url", "website", "link", "tool_url", "project_url", "site"],
    "name": ["name", "tool_name", "title", "site_name", "project_name"],
    "description": ["description", "desc", "summary", "details", "about", "content"],
    "email": ["email", "contact", "your_email", "contact_email"],
    "category": ["category", "categories", "type", "tag"],
}


def find_field_by_label(page, keywords):
    """Find form field by label text or placeholder matching keywords."""
    for kw in keywords:
        # Try by label
        try:
            label = page.get_by_label(kw, exact=False)
            if label.count() > 0:
                return label.first
        except Exception:
            pass
        # Try by placeholder
        try:
            field = page.get_by_placeholder(kw, exact=False)
            if field.count() > 0:
                return field.first
        except Exception:
            pass
        # Try by name attribute
        try:
            field = page.locator(f'input[name*="{kw}" i], textarea[name*="{kw}" i]').first
            if field.count() > 0:
                return field
        except Exception:
            pass
    return None


async def submit_one(browser, directory):
    """Try to submit one directory using a real browser."""
    name = directory["name"]
    url = directory["url"]
    print(f"\n→ {name} ({url})")

    context = await browser.new_context(
        user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        viewport={"width": 1280, "height": 800},
    )
    page = await context.new_page()

    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(3000)  # Let JS render

        # Take a screenshot for debugging
        screenshot_path = SCREENSHOTS_DIR / f"{name.replace(' ', '_').lower()}.png"
        try:
            await page.screenshot(path=str(screenshot_path), full_page=False)
        except Exception:
            pass

        # Find and fill the form
        filled = 0

        url_field = find_field_by_label(page, FIELD_PATTERNS["url"])
        if url_field:
            await url_field.fill(SITE_INFO["url"])
            filled += 1

        name_field = find_field_by_label(page, FIELD_PATTERNS["name"])
        if name_field:
            await name_field.fill(SITE_INFO["name"])
            filled += 1

        desc_field = find_field_by_label(page, FIELD_PATTERNS["description"])
        if desc_field:
            await desc_field.fill(SITE_INFO["description"][:500])  # Most have char limits
            filled += 1

        email_field = find_field_by_label(page, FIELD_PATTERNS["email"])
        if email_field:
            await email_field.fill(SITE_INFO["email"])
            filled += 1

        cat_field = find_field_by_label(page, FIELD_PATTERNS["category"])
        if cat_field:
            try:
                await cat_field.select_option(label=SITE_INFO["category"])
            except Exception:
                try:
                    await cat_field.fill(SITE_INFO["category"])
                except Exception:
                    pass

        print(f"  Fields filled: {filled}/5")
        print(f"  Screenshot: {screenshot_path.name}")

        if filled == 0:
            print(f"  ⚠ No fields detected — likely needs manual submission")
            return "manual", "no_fields_found"

        # Find and click submit button
        submit_button = None
        for button_text in ["submit", "add", "suggest", "send", "save", "continue"]:
            try:
                btn = page.get_by_role("button", name=button_text, exact=False)
                if await btn.count() > 0:
                    submit_button = btn.first
                    break
            except Exception:
                pass
            try:
                btn = page.locator(f'input[type="submit"][value*="{button_text}" i], button[type="submit"]').first
                if await btn.count() > 0:
                    submit_button = btn
                    break
            except Exception:
                pass

        if not submit_button:
            # Try any button with type=submit
            submit_button = page.locator('button[type="submit"], input[type="submit"]').first

        if submit_button:
            await submit_button.click()
            await page.wait_for_timeout(5000)  # Wait for form submission

            # Take after-submit screenshot
            after_path = SCREENSHOTS_DIR / f"{name.replace(' ', '_').lower()}_after.png"
            try:
                await page.screenshot(path=str(after_path), full_page=False)
            except Exception:
                pass

            # Check for success indicators
            content = await page.content()
            success_indicators = ["thank you", "success", "submitted", "received", "we'll review"]
            if any(ind in content.lower() for ind in success_indicators):
                print(f"  ✓ Submission appears successful!")
                return True, "submitted"
            else:
                # Check current URL — many sites redirect to a thank-you page
                current_url = page.url
                if any(ind in current_url.lower() for ind in ["thank", "success", "submitted"]):
                    print(f"  ✓ Redirected to success page!")
                    return True, "submitted"
                print(f"  ? Submission attempted, result unclear. Check screenshots.")
                return "uncertain", "ambiguous_response"
        else:
            print(f"  ⚠ No submit button found — needs manual submission")
            return "manual", "no_submit_button"

    except Exception as e:
        print(f"  ✗ Error: {str(e)[:150]}")
        return False, str(e)[:100]
    finally:
        await context.close()


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", help="Submit to a specific directory name")
    parser.add_argument("--limit", type=int, default=10, help="Max directories to process")
    parser.add_argument("--headless", action="store_true", default=True)
    args = parser.parse_args()

    # Load existing log
    log = {"submitted": {}, "pending": [], "rejected": [], "manual_needed": []}
    if LOG_FILE.exists():
        log = json.loads(LOG_FILE.read_text())
        # Normalize old key
        if "pending" not in log:
            log["pending"] = []
        if "manual_needed" not in log:
            log["manual_needed"] = log.pop("pending", [])

    # Directory list — same as before, but now using real browser
    DIRECTORIES = [
        {"name": "Futurepedia", "url": "https://www.futurepedia.io/submit-tool", "da": 55},
        {"name": "AI Top Tools", "url": "https://www.aitoptools.com/submit", "da": 40},
        {"name": "AllAboutAI", "url": "https://www.allaboutai.com/submit-tool/", "da": 70},
        {"name": "TopAI.tools", "url": "https://topai.tools/submit", "da": 35},
        {"name": "AIChief", "url": "https://aichief.com/submit", "da": 35},
        {"name": "AI Tool Flow", "url": "https://ai-toolflow.com/submit", "da": 35},
        {"name": "Appscribed", "url": "https://appscribed.com/submit-tool/", "da": 60},
        {"name": "AI Tool Hunt", "url": "https://aitoolhunt.com/submit", "da": 35},
        {"name": "FutureTools", "url": "https://futuretools.io/submit", "da": 35},
        {"name": "Best AI Tools", "url": "https://bestai.tools/submit", "da": 30},
        {"name": "Toolify", "url": "https://www.toolify.ai/submit", "da": 40},
        {"name": "Insidr AI", "url": "https://www.insidr.ai/submit", "da": 25},
        {"name": "AI Nav", "url": "https://ai-nav.net/submit", "da": 25},
        {"name": "AI Hunt List", "url": "https://aihuntlist.com/submit", "da": 30},
        {"name": "AI Tools Directory", "url": "https://aitoolsdirectory.com/submit", "da": 30},
        {"name": "AI Tool List", "url": "https://ai-tool-list.com/submit", "da": 30},
        {"name": "AI Sites", "url": "https://ai-sites.net/submit", "da": 25},
        {"name": "AI Hub", "url": "https://aihubs.ai/submit", "da": 30},
        {"name": "AI Directory Wiki", "url": "https://aidirectory.wiki/submit", "da": 30},
        {"name": "AI Dir", "url": "https://aidir.wiki/submit", "da": 25},
        {"name": "AI Kaptan", "url": "https://aikaptan.com/submit", "da": 30},
    ]

    if args.target:
        DIRECTORIES = [d for d in DIRECTORIES if d["name"] == args.target]
        if not DIRECTORIES:
            print(f"Directory '{args.target}' not found")
            return

    DIRECTORIES = DIRECTORIES[:args.limit]

    print("=" * 60)
    print(f"AI Tools Hub — Browser-Based Directory Submission")
    print(f"Using Playwright (real Chromium browser)")
    print(f"Site: {SITE_INFO['url']}")
    print(f"Directories to process: {len(DIRECTORIES)}")
    print(f"Screenshots saved to: {SCREENSHOTS_DIR}/")
    print("=" * 60)

    results = {"submitted": 0, "manual_needed": 0, "failed": 0, "uncertain": 0}

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=args.headless)

        for i, directory in enumerate(DIRECTORIES, 1):
            print(f"\n[{i}/{len(DIRECTORIES)}] ", end="")

            if directory["name"] in log["submitted"]:
                status = log["submitted"][directory["name"]].get("status", "ok")
                if status == "ok":
                    print(f"⏭ {directory['name']}: already submitted")
                    continue

            result, reason = await submit_one(browser, directory)

            if result is True:
                log["submitted"][directory["name"]] = {
                    "url": directory["url"],
                    "da": directory["da"],
                    "submitted_at": datetime.utcnow().isoformat() + "Z",
                    "status": "ok",
                    "method": "playwright_browser",
                }
                results["submitted"] += 1
            elif result == "manual":
                log["manual_needed"].append({
                    "name": directory["name"],
                    "url": directory["url"],
                    "reason": reason,
                    "da": directory["da"],
                })
                results["manual_needed"] += 1
            elif result == "uncertain":
                log["submitted"][directory["name"]] = {
                    "url": directory["url"],
                    "da": directory["da"],
                    "submitted_at": datetime.utcnow().isoformat() + "Z",
                    "status": "uncertain",
                }
                results["uncertain"] += 1
            else:
                log["rejected"].append({
                    "name": directory["name"],
                    "url": directory["url"],
                    "reason": reason,
                })
                results["failed"] += 1

            LOG_FILE.write_text(json.dumps(log, indent=2))
            await asyncio.sleep(5)  # Rate limit

        await browser.close()

    print("\n" + "=" * 60)
    print(f"RESULTS:")
    print(f"  ✓ Submitted: {results['submitted']}")
    print(f"  ⚠ Manual needed: {results['manual_needed']}")
    print(f"  ? Uncertain: {results['uncertain']}")
    print(f"  ✗ Failed: {results['failed']}")
    print(f"\nScreenshots in: {SCREENSHOTS_DIR}/")
    print(f"Log: {LOG_FILE}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
