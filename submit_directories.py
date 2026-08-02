#!/usr/bin/env python3
"""
Autonomous directory submission system for AI Tools Hub.

Submits the site to 30+ AI tool directories using a combination of:
- requests for sites with JSON APIs
- urllib for browser-like submission
- Manual checklist for sites requiring human verification

Stores submission log in submit_log.json to avoid duplicates.
"""
import os
import sys
import json
import time
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path

ROOT = Path("/home/beryl-server/projects/ai-for-india")
LOG_FILE = ROOT / "submit_log.json"

SITE_INFO = {
    "name": "AI Tools Hub",
    "tagline": "Honest, no-fluff AI tool reviews for 2026.",
    "url": "https://joshclaw-sys.github.io/ai-tools-hub/",
    "description": (
        "AI Tools Hub is the no-nonsense guide to AI tools that matter in 2026. "
        "We test every tool with real workflows — writing, coding, research, "
        "image generation, voice — and rank them honestly. No sponsored fluff, "
        "no affiliate bias. Every article includes a clear top pick, 'best for' "
        "recommendations, a side-by-side comparison table, specific test "
        "methodology, and an honest 'skip this' section when a popular tool "
        "doesn't deliver. We update monthly as the AI landscape shifts."
    ),
    "categories": [
        "AI Tools",
        "Artificial Intelligence",
        "Machine Learning",
        "Productivity",
        "Software",
        "Technology",
    ],
    "logo": "https://joshclaw-sys.github.io/ai-tools-hub/assets/logo.png",
    "email": "hello@ai-tools-hub.example",
    "twitter": "@AIToolsHub",
}

# Directories that accept submissions via simple form POSTs or API
# Format: (name, url, type, notes)
DIRECTORIES = [
    # Tier 1 — high DA, free, large audience
    {"name": "Product Hunt", "url": "https://www.producthunt.com/posts/new",
     "type": "manual", "da": 90, "notes": "Launch day only, need 50+ articles"},
    {"name": "Futurepedia", "url": "https://www.futurepedia.io/submit",
     "type": "form", "da": 55, "notes": "Free, ~50k monthly visitors"},
    {"name": "AI Top Tools", "url": "https://www.aitoptools.com/submit",
     "type": "form", "da": 40, "notes": "Free submission"},
    {"name": "AllAboutAI", "url": "https://www.allaboutai.com/submit-tool/",
     "type": "form", "da": 70, "notes": "1500+ tools listed, high traffic"},
    {"name": "TopAI.tools", "url": "https://topai.tools/submit",
     "type": "form", "da": 35, "notes": "Free directory"},
    {"name": "AI Tools fyi", "url": "https://aitools.fyi/submit",
     "type": "form", "da": 30, "notes": "Free, simple form"},
    {"name": "AIChief", "url": "https://aichief.com/submit",
     "type": "form", "da": 35, "notes": "AI directory, free"},
    {"name": "AI Tool Flow", "url": "https://ai-toolflow.com/submit",
     "type": "form", "da": 35, "notes": "Free submission"},
    {"name": "Appscribed", "url": "https://appscribed.com/submit-tool/",
     "type": "form", "da": 60, "notes": "3000+ tools listed, requires login"},
    {"name": "AI Tool Hunt", "url": "https://aitoolhunt.com/submit",
     "type": "form", "da": 35, "notes": "Free directory"},

    # Tier 2 — medium DA, free
    {"name": "FutureTools", "url": "https://futuretools.io/submit",
     "type": "form", "da": 35},
    {"name": "Best AI Tools", "url": "https://bestai.tools/submit",
     "type": "form", "da": 30},
    {"name": "Toolify", "url": "https://www.toolify.ai/submit",
     "type": "form", "da": 40},
    {"name": "Insidr AI", "url": "https://www.insidr.ai/submit",
     "type": "form", "da": 25},
    {"name": "AI Nav", "url": "https://ai-nav.net/submit",
     "type": "form", "da": 25},
    {"name": "AI Hunt List", "url": "https://aihuntlist.com/submit",
     "type": "form", "da": 30},
    {"name": "AI Tools Directory", "url": "https://aitoolsdirectory.com/submit",
     "type": "form", "da": 30},
    {"name": "AI Tool List", "url": "https://ai-tool-list.com/submit",
     "type": "form", "da": 30},
    {"name": "Cool AI Tools", "url": "https://cool-ai-tools.com/submit",
     "type": "form", "da": 25},
    {"name": "AI Sites", "url": "https://ai-sites.net/submit",
     "type": "form", "da": 25},
    {"name": "AI Hub", "url": "https://aihubs.ai/submit",
     "type": "form", "da": 30},
    {"name": "AI Hunt", "url": "https://aihunt.io/submit",
     "type": "form", "da": 28},
    {"name": "Top Tools AI", "url": "https://toptools.ai/submit",
     "type": "form", "da": 28},
    {"name": "AI Ex", "url": "https://aiex.me/submit",
     "type": "form", "da": 30},
    {"name": "AI Directory Wiki", "url": "https://aidirectory.wiki/submit",
     "type": "form", "da": 30},
    {"name": "AI Dir", "url": "https://aidir.wiki/submit",
     "type": "form", "da": 25},
    {"name": "AI Kaptan", "url": "https://aikaptan.com/submit",
     "type": "form", "da": 30},
    {"name": "AI Dream Hub", "url": "https://aidreamhub.com/submit",
     "type": "form", "da": 25},
    {"name": "AI Agents Directory", "url": "https://aiagentsdirectory.com/submit",
     "type": "form", "da": 40, "notes": "Agent-focused"},
    {"name": "AIDir", "url": "https://aidirs.best/submit",
     "type": "form", "da": 25},
    {"name": "AI Match Pro", "url": "https://aimatch.pro/submit",
     "type": "form", "da": 25},
    {"name": "AIToolsDirectory.io", "url": "https://aitoolsdirectory.io/submit",
     "type": "form", "da": 30},
    {"name": "ThereIsAnAIForThat", "url": "https://theresanaiforthat.com/submit",
     "type": "form", "da": 45, "notes": "High traffic AI directory"},
    {"name": "OpenTools", "url": "https://opentools.ai/submit",
     "type": "form", "da": 30},
    {"name": "AI Center", "url": "https://aicenter.ai/submit",
     "type": "form", "da": 25},
    {"name": "GPTForge", "url": "https://gptforge.ai/submit",
     "type": "form", "da": 25},
    {"name": "AI Parabellum", "url": "https://aiparabellum.com/submit",
     "type": "form", "da": 25},
]


def load_log():
    if LOG_FILE.exists():
        return json.loads(LOG_FILE.read_text())
    return {"submitted": {}, "pending": [], "rejected": []}


def save_log(log):
    LOG_FILE.write_text(json.dumps(log, indent=2))


def check_submission_endpoint(url):
    """Check if a submission URL is reachable."""
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "AI Tools Hub Submission Bot 1.0 (+hello@ai-tools-hub.example)"
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status, resp.read()[:5000].decode("utf-8", errors="ignore")
    except Exception as e:
        return None, str(e)


def find_submission_form(html, base_url):
    """Find the submission form on a directory page."""
    import re
    # Look for typical form patterns
    forms = re.findall(r'<form[^>]*action="([^"]*)"[^>]*method="([^"]*)"', html)
    inputs = re.findall(r'<input[^>]*name="([^"]*)"[^>]*>', html)

    # Find forms with relevant fields (url, name, email, description)
    relevant_inputs = [i for i in inputs if any(
        kw in i.lower() for kw in ["url", "name", "email", "description", "title", "tool"]
    )]

    if forms and relevant_inputs:
        action = forms[0][0]
        method = forms[0][1]
        if not action.startswith("http"):
            action = urllib.parse.urljoin(base_url, action)
        return {"action": action, "method": method, "fields": relevant_inputs}
    return None


def submit_to_form(directory):
    """Try to submit to a directory's form."""
    print(f"\n→ {directory['name']} ({directory['url']})")

    status, html = check_submission_endpoint(directory["url"])
    if status != 200:
        print(f"  ✗ Could not reach: {status or html[:100]}")
        return False, f"unreachable: {status}"

    form = find_submission_form(html, directory["url"])
    if not form:
        print(f"  ⚠ No obvious form found — needs manual submission")
        return "manual", "no_form_detected"

    print(f"  ✓ Found form: {form['method'].upper()} {form['action']}")
    print(f"    Fields: {', '.join(form['fields'][:5])}")

    # Build form data
    form_data = {
        "url": SITE_INFO["url"],
        "name": SITE_INFO["name"],
        "title": SITE_INFO["name"],
        "tool_name": SITE_INFO["name"],
        "email": SITE_INFO["email"],
        "description": SITE_INFO["description"],
        "tagline": SITE_INFO["tagline"],
        "category": SITE_INFO["categories"][0],
        "logo": SITE_INFO["logo"],
        "twitter": SITE_INFO["twitter"],
        "submit": "Submit",
        "action": "submit",
    }

    # Try POST
    try:
        data = urllib.parse.urlencode(form_data).encode("utf-8")
        req = urllib.request.Request(form["action"], data=data, headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AI-Tools-Hub-Bot/1.0",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "text/html,application/xhtml+xml",
        })
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = resp.read()[:3000].decode("utf-8", errors="ignore")
            if any(kw in result.lower() for kw in ["success", "thank", "submitted", "received"]):
                print(f"  ✓ Submission accepted!")
                return True, "submitted"
            elif any(kw in result.lower() for kw in ["error", "invalid", "required", "missing"]):
                print(f"  ✗ Form rejected: {result[:200]}")
                return False, "form_rejected"
            else:
                print(f"  ? Unclear response: {result[:200]}")
                return "uncertain", "ambiguous_response"
    except urllib.error.HTTPError as e:
        print(f"  ✗ HTTP {e.code}: {e.reason}")
        return False, f"http_{e.code}"
    except Exception as e:
        print(f"  ✗ Error: {str(e)[:200]}")
        return False, str(e)[:100]


def main():
    log = load_log()

    print("=" * 60)
    print(f"AI Tools Hub — Directory Submission System")
    print(f"Site: {SITE_INFO['url']}")
    print(f"Directories to process: {len(DIRECTORIES)}")
    print("=" * 60)

    results = {"submitted": 0, "manual_needed": 0, "failed": 0, "uncertain": 0}

    for i, directory in enumerate(DIRECTORIES, 1):
        print(f"\n[{i}/{len(DIRECTORIES)}] ", end="")

        if directory["name"] in log["submitted"]:
            print(f"⏭ {directory['name']}: already submitted")
            continue

        result, reason = submit_to_form(directory)

        if result is True:
            log["submitted"][directory["name"]] = {
                "url": directory["url"],
                "da": directory["da"],
                "submitted_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
            results["submitted"] += 1
        elif result == "manual":
            log["pending"].append({
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
                "submitted_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
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

        # Save log after each attempt
        save_log(log)

        # Rate limit
        time.sleep(3)

    print("\n" + "=" * 60)
    print(f"RESULTS:")
    print(f"  ✓ Submitted: {results['submitted']}")
    print(f"  ⚠ Manual needed: {results['manual_needed']}")
    print(f"  ? Uncertain: {results['uncertain']}")
    print(f"  ✗ Failed: {results['failed']}")
    print(f"\nLog saved to: {LOG_FILE}")
    print("=" * 60)


if __name__ == "__main__":
    main()
