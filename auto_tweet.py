"""Auto-post new articles to Twitter/X.

Uses twitter-cli (installed via Agent Reach). Requires TWITTER_AUTH_TOKEN + TWITTER_CT0
in environment. Get them from your browser via Cookie-Editor extension:
https://chromewebstore.google.com/detail/cookie-editor/hlkenndednhfkekhgcdicdfddnkalmdm
"""
import os
import sys
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).parent

def check_twitter_env():
    """Verify Twitter credentials are set."""
    token = os.environ.get("TWITTER_AUTH_TOKEN")
    ct0 = os.environ.get("TWITTER_CT0")
    if not token or not ct0:
        print("⚠️  TWITTER_AUTH_TOKEN and TWITTER_CT0 not set.")
        print("   To enable auto-tweeting:")
        print("   1. Install Cookie-Editor Chrome extension")
        print("   2. Go to x.com (logged in)")
        print("   3. Cookie-Editor → Export → Header String")
        print("   4. Set the env vars:")
        print("      export TWITTER_AUTH_TOKEN='...'")
        print("      export TWITTER_CT0='...'")
        print("   Then re-run this script.")
        return False
    return True

def tweet_article(meta, twitter_cli="twitter"):
    """Tweet about a new article using twitter-cli."""
    # Build tweet text (280 char max)
    title = meta["title"]
    short_title = meta.get("short_title", title)
    url = f"https://joshclaw-sys.github.io/ai-tools-hub/articles/{meta['slug']}.html"

    # Hashtags
    cat = meta.get("category", "ai")
    cat_label = cat.replace("-", " ").title().replace(" ", "")
    tags = f"#AI #{cat_label}"

    # Build tweet
    tweet = f"{short_title}\n\n{url}\n\n{tags}"

    if len(tweet) > 280:
        # Truncate title
        max_title = 280 - len(url) - len(tags) - 4
        tweet = f"{short_title[:max_title]}...\n\n{url}\n\n{tags}"

    print(f"  → Tweeting: {tweet[:80]}...")

    if not check_twitter_env():
        return False

    # Run twitter-cli
    try:
        result = subprocess.run(
            [twitter_cli, "tweet", tweet],
            capture_output=True, text=True, timeout=30,
            env={**os.environ, "TWITTER_AUTH_TOKEN": os.environ["TWITTER_AUTH_TOKEN"], "TWITTER_CT0": os.environ["TWITTER_CT0"]},
        )
        if result.returncode == 0:
            print(f"  ✓ Tweet posted: {result.stdout[:80]}")
            return True
        else:
            print(f"  ✗ Tweet failed: {result.stderr[:200]}")
            return False
    except FileNotFoundError:
        print(f"  ✗ twitter-cli not found. Activate Agent Reach venv:")
        print(f"     source ~/.agent-reach-venv/bin/activate")
        return False
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def main():
    """Tweet about all published articles that haven't been tweeted yet."""
    # Load tweet log
    log_file = ROOT / "tweet_log.json"
    if log_file.exists():
        tweeted = set(json.loads(log_file.read_text()))
    else:
        tweeted = set()

    # Find articles that haven't been tweeted
    articles_dir = ROOT / "articles"
    new_tweets = []
    for art_dir in sorted(articles_dir.iterdir()):
        if not art_dir.is_dir():
            continue
        meta_file = art_dir / "meta.json"
        if not meta_file.exists():
            continue
        slug = art_dir.name
        if slug in tweeted:
            continue
        meta = json.loads(meta_file.read_text())
        if tweet_article(meta):
            new_tweets.append(slug)

    # Also tweet comparison + long-tail pages
    for kind in ["comparisons", "long-tail"]:
        kind_dir = ROOT / kind
        if not kind_dir.exists():
            continue
        for p_dir in sorted(kind_dir.iterdir()):
            if not p_dir.is_dir():
                continue
            meta_file = p_dir / "meta.json"
            if not meta_file.exists():
                continue
            slug = f"{kind}/{p_dir.name}"
            if slug in tweeted:
                continue
            meta = json.loads(meta_file.read_text())
            if tweet_article(meta):
                new_tweets.append(slug)

    # Update log
    tweeted.update(new_tweets)
    log_file.write_text(json.dumps(sorted(tweeted), indent=2))

    print(f"\n✅ Posted {len(new_tweets)} new tweets")


if __name__ == "__main__":
    main()
