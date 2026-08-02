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

        # Take initial screenshot
        screenshot_path = SCREENSHOTS_DIR / f"{name.replace(' ', '_').lower()}_initial.png"
        try:
            await page.screenshot(path=str(screenshot_path), full_page=False)
        except Exception:
            pass

        # Look for a "Get Free Listing" / "Add" / "Submit a Tool" button that reveals the form
        reveal_buttons = ["Get Free Listing", "Add Your Tool", "Submit a Tool", "Suggest", "Get Started"]
        for btn_text in reveal_buttons:
            try:
                btn = page.get_by_role("button", name=btn_text, exact=False).first
                if await btn.count() > 0:
                    await btn.click()
                    await page.wait_for_timeout(2000)
                    print(f"  → Clicked '{btn_text}' to reveal form")
                    break
            except Exception:
                pass

        # Scroll to bottom to ensure lazy-loaded forms are rendered
        try:
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(1500)
        except Exception:
            pass

        # Find and fill the form
        filled = 0

        # Try to find ALL input/textarea fields (broader approach)
        all_inputs = await page.locator('input[type="text"], input[type="email"], input[type="url"], textarea').all()
        print(f"  Found {len(all_inputs)} input fields on page")

        # Map inputs to values based on label association
        for inp in all_inputs:
            try:
                inp_type = await inp.get_attribute("type") or "text"
                inp_name = await inp.get_attribute("name") or ""
                inp_placeholder = await inp.get_attribute("placeholder") or ""

                # Try to find associated label
                inp_id = await inp.get_attribute("id")
                label_text = ""
                if inp_id:
                    try:
                        label = page.locator(f'label[for="{inp_id}"]')
                        if await label.count() > 0:
                            label_text = await label.first.inner_text()
                    except Exception:
                        pass

                combined = f"{inp_name} {inp_placeholder} {label_text}".lower()

                # URL field
                if (inp_type == "url" or
                    "url" in combined or "website" in combined or "link" in combined or
                    "site" in combined):
                    await inp.fill(SITE_INFO["url"])
                    filled += 1
                    print(f"    ✓ URL → {SITE_INFO['url'][:40]}")
                # Name field
                elif "name" in combined and "tool" not in combined.replace("tool_name", ""):
                    if "tool" in combined or inp_name:
                        await inp.fill(SITE_INFO["name"])
                        filled += 1
                        print(f"    ✓ Name → {SITE_INFO['name']}")
                # Description field
                elif "desc" in combined or "summary" in combined or "about" in combined:
                    await inp.fill(SITE_INFO["description"][:500])
                    filled += 1
                    print(f"    ✓ Description (truncated)")
                # Email field
                elif inp_type == "email" or "email" in combined or "contact" in combined:
                    await inp.fill(SITE_INFO["email"])
                    filled += 1
                    print(f"    ✓ Email")
            except Exception as e:
                pass

        # Also try the original label-based approach (more reliable)
        if filled < 3:
            for kw, value in [
                ("url", SITE_INFO["url"]),
                ("name", SITE_INFO["name"]),
                ("title", SITE_INFO["name"]),
                ("description", SITE_INFO["description"][:500]),
                ("email", SITE_INFO["email"]),
            ]:
                try:
                    field = page.get_by_label(kw, exact=False).first
                    if await field.count() > 0:
                        await field.fill(value)
                        filled += 1
                except Exception:
                    pass

        print(f"  Fields filled: {filled}")
        print(f"  Screenshot: {screenshot_path.name}")

        if filled == 0:
            print(f"  ⚠ No fields detected — likely needs manual submission")
            return "manual", "no_fields_found"

        # Find and click submit button
        submit_button = None
        for button_text in ["submit", "add", "send", "save", "🚀"]:
            try:
                btn = page.get_by_role("button", name=button_text, exact=False)
                if await btn.count() > 0:
                    submit_button = btn.first
                    break
            except Exception:
                pass

        if not submit_button:
            submit_button = page.locator('button[type="submit"], input[type="submit"]').first

        if submit_button:
            try:
                await submit_button.click()
                await page.wait_for_timeout(8000)  # Wait for form submission

                # Take after-submit screenshot
                after_path = SCREENSHOTS_DIR / f"{name.replace(' ', '_').lower()}_after.png"
                try:
                    await page.screenshot(path=str(after_path), full_page=False)
                except Exception:
                    pass

                content = await page.content()
                success_indicators = ["thank you", "success", "submitted", "received", "we'll review", "we will review"]
                if any(ind in content.lower() for ind in success_indicators):
                    print(f"  ✓ Submission appears successful!")
                    return True, "submitted"
                else:
                    current_url = page.url
                    if any(ind in current_url.lower() for ind in ["thank", "success", "submitted"]):
                        print(f"  ✓ Redirected to success page!")
                        return True, "submitted"
                    print(f"  ? Submission attempted, result unclear. Check screenshots.")
                    return "uncertain", "ambiguous_response"
            except Exception as e:
                print(f"  ✗ Submit click failed: {e}")
                return False, str(e)[:100]
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
    # Smaller directories without bot protection (verified 2026-08-02)
    DIRECTORIES = [
        {"name": "TheNextAI", "url": "https://www.thenextai.com/submit-ai-tool/", "da": 35,
         "fields": ["Tool Name", "Website URL", "Category", "Pricing Model", "Short Description", "Full Description", "Logo URL", "Your Email", "Tags"]},
        {"name": "ToolsLand", "url": "https://www.toolsland.ai/submit-ai-tool-free", "da": 25,
         "fields": ["name", "url", "description", "email", "category"]},
        {"name": "Stork", "url": "https://www.stork.ai/submit-ai-tool-free", "da": 25,
         "fields": ["name", "url", "description", "email"]},
        {"name": "AIToolsSync", "url": "https://aitoolsync.com/submit-a-tool", "da": 25,
         "fields": ["name", "url", "description", "email", "category"]},
        {"name": "AIToolsDirectory", "url": "https://www.aitools-directory.com/submit-your-ai-tool-get-listed-on-ai-tools-directory/", "da": 25,
         "fields": ["name", "url", "description", "email"]},
        {"name": "PromptFrenzy", "url": "https://www.promptfrenzy.com/directory/submit", "da": 20,
         "fields": ["name", "url", "description", "email"]},
        {"name": "AIBazaar", "url": "https://ai-bazaar-eight.vercel.app/submit", "da": 20,
         "fields": ["name", "url", "description", "email"]},
        # Larger directories (likely bot-protected, but worth trying)
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
