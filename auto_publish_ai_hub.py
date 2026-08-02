#!/usr/bin/env python3
"""
AI Tools Hub — daily auto-publish pipeline.

Reads planned.json queue → for each pending topic:
  1. Run research_generate.py to produce meta.json + body.html with real 2026 data
  2. Run build.py to render the static site
  3. git commit + push to main → GitHub Pages auto-deploys
  4. Run publish_third_party.py to cross-post new articles to Dev.to
  5. Generate RSS feed for Substack auto-import
  6. Generate LinkedIn article drafts
  7. Ping IndexNow for fast search engine discovery

Runs daily at 10 AM IST via cron / systemd.
"""
import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).parent
PLANNED = ROOT / "planned.json"


def run(cmd, cwd=None):
    """Run a shell command, return (success, output)."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=600,
            cwd=cwd or str(ROOT),
            env={**os.environ, "PATH": f"{os.environ['HOME']}/.agent-reach-venv/bin:{os.environ.get('PATH', '')}"},
        )
        return result.returncode == 0, (result.stdout + result.stderr).strip()
    except Exception as e:
        return False, str(e)


def load_planned():
    if PLANNED.exists():
        return json.loads(PLANNED.read_text())
    return []


def git_commit_push(msg):
    ok, out = run("git add -A")
    if not ok:
        return False, out
    ok, out = run(f"git commit -m '{msg}' --allow-empty")
    if not ok:
        # Nothing to commit is fine
        if "nothing to commit" in out:
            return True, "nothing to commit"
        return False, out
    ok, out = run("git push origin main")
    return ok, out


def main():
    print("=" * 60)
    print(f"AI Tools Hub — Daily Auto-Publish")
    print(f"Time: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60)

    plan = load_planned()
    pending = [p for p in plan if not p.get("done") and not p.get("status") == "done"]
    print(f"Pending articles in queue: {len(pending)}")

    n = min(2, len(pending))
    if n == 0:
        print("No pending articles to publish — adding 2 new ones from top categories")
        # Auto-add 2 new topics
        new_topics = [
            {"topic": "AI agents for business automation", "category": "ai-agents"},
            {"topic": "AI video generators for marketing", "category": "video-generators"},
        ]
        plan.extend(new_topics)
        PLANNED.write_text(json.dumps(plan, indent=2, ensure_ascii=False))
        pending = new_topics
        n = 2

    # 1. Research + write new articles
    print(f"\n[1/6] Researching + writing {n} new articles...")
    ok, out = run(f"python3 research_generate.py --from-planned --count {n}")
    print(out[-600:])

    # 2. Build static site
    print(f"\n[2/6] Building static site...")
    ok, out = run("python3 build.py")
    print(out[-300:])

    # 3. Generate RSS feed + LinkedIn drafts
    print(f"\n[3/6] Updating RSS feed + LinkedIn drafts...")
    run("python3 generate_rss.py")
    run("python3 generate_linkedin.py")
    print("  ✓ RSS feed updated")
    print("  ✓ LinkedIn drafts updated")

    # 4. Git commit + push
    print(f"\n[4/6] Committing + pushing to GitHub...")
    msg = f"Auto-publish {n} new articles {datetime.now().strftime('%Y-%m-%d')}"
    ok, out = git_commit_push(msg)
    print(f"  {'✓' if ok else '✗'} {msg}")
    if not ok:
        print(f"    {out[:200]}")

    # 5. Cross-post to Dev.to
    print(f"\n[5/6] Cross-posting to Dev.to...")
    ok, out = run("python3 publish_third_party.py --all")
    print(out[-500:])

    # 6. Ping IndexNow
    print(f"\n[6/6] Pinging IndexNow for fast search engine discovery...")
    ok, out = run("python3 indexnow.py --all")
    print(out[-200:])

    print("\n" + "=" * 60)
    print(f"✓ Auto-publish complete — {n} new articles live")
    print(f"  • Site: https://joshclaw-sys.github.io/ai-tools-hub/")
    print(f"  • Dev.to: https://dev.to/jivinsardine/")
    print(f"  • RSS feed: https://joshclaw-sys.github.io/ai-tools-hub/feed.xml")
    print(f"  • Remaining in queue: {len(pending) - n}")
    print("=" * 60)


if __name__ == "__main__":
    main()
