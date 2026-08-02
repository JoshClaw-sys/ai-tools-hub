#!/usr/bin/env python3
"""
Reddit engagement automation for AI Tools Hub.

Uses Agent Reach (Exa search) to find high-intent Reddit questions matching
our content categories. Outputs a daily report of questions to answer.

For each question, write a thoughtful, value-first reply with one link
to the relevant AI Tools Hub article at the end.

Usage:
  source ~/.agent-reach-venv/bin/activate
  python3 reddit_engagement.py --days 1
"""
import os
import sys
import json
import argparse
import subprocess
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path("/home/beryl-server/projects/ai-for-india")
LOG_FILE = ROOT / "reddit_engagement.json"

# High-value Reddit communities for AI tools content
SUBREDDITS = {
    "ChatGPT": {
        "members": "3.4M",
        "topics": ["ChatGPT", "GPT-5", "Claude", "Gemini", "free AI", "AI comparison"],
        "best_for": "Chatbot comparisons, free tier questions"
    },
    "LocalLLaMA": {
        "members": "650K",
        "topics": ["open source AI", "Llama", "Mistral", "self-hosted", "Ollama"],
        "best_for": "Open-source AI alternatives"
    },
    "singularity": {
        "members": "1.5M",
        "topics": ["AI news", "AI tools", "AGI", "AI impact"],
        "best_for": "Broad AI discussion"
    },
    "artificial": {
        "members": "380K",
        "topics": ["AI news", "machine learning", "AI applications"],
        "best_for": "ML research and news"
    },
    "AI_Agents": {
        "members": "200K+",
        "topics": ["AI agents", "AutoGPT", "agent frameworks", "workflow automation"],
        "best_for": "Agent tools and frameworks"
    },
    "cursor": {
        "members": "10K+",
        "topics": ["Cursor", "AI IDE", "code editors", "Claude Code"],
        "best_for": "AI coding tool discussions"
    },
    "ClaudeAI": {
        "members": "15K+",
        "topics": ["Claude", "Anthropic", "Sonnet", "Opus"],
        "best_for": "Claude-specific questions"
    },
    "ChatGPTCoding": {
        "members": "50K+",
        "topics": ["AI coding", "Cursor", "Copilot", "code generation"],
        "best_for": "Developer-focused coding AI questions"
    },
    "StableDiffusion": {
        "members": "1M+",
        "topics": ["image generation", "Midjourney", "Stable Diffusion", "ComfyUI"],
        "best_for": "AI image generation"
    },
    "MidJourney": {
        "members": "200K+",
        "topics": ["Midjourney", "image prompts", "AI art"],
        "best_for": "Midjourney-specific discussions"
    },
}


def search_reddit_questions(topic, limit=5):
    """Use Exa to find recent Reddit questions matching a topic."""
    query = f"site:reddit.com {topic}"
    try:
        result = subprocess.run(
            ["mcporter", "call", f'exa.web_search_exa(query: "{query}", numResults: {limit})'],
            capture_output=True, text=True, timeout=30,
            env={**os.environ},
        )
        if result.returncode == 0:
            return result.stdout
        return f"Error: {result.stderr}"
    except Exception as e:
        return f"Error: {e}"


def parse_reddit_urls(text):
    """Extract Reddit URLs from Exa search output."""
    import re
    urls = re.findall(r'https?://(?:www\.)?reddit\.com/r/\w+/comments/[\w]+/?[^\s"]*', text)
    return list(set(urls))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=1, help="How many days back to look")
    parser.add_argument("--per-subreddit", type=int, default=3, help="Questions per subreddit")
    parser.add_argument("--output", default=str(ROOT / "reddit_leads.md"))
    args = parser.parse_args()

    print("=" * 60)
    print(f"Reddit Engagement — Finding questions to answer")
    print(f"Site: https://joshclaw-sys.github.io/ai-tools-hub/")
    print("=" * 60)

    # Load existing log
    log = {"answered": [], "skipped": []}
    if LOG_FILE.exists():
        log = json.loads(LOG_FILE.read_text())

    all_leads = []
    report_lines = [
        "# Reddit Engagement — Today's Leads",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        f"Site: https://joshclaw-sys.github.io/ai-tools-hub/",
        "",
        "## How to use this report",
        "",
        "For each subreddit below, find 1-2 questions that match a content piece on",
        "AI Tools Hub. Write a thoughtful, value-first reply (150+ words) that includes",
        "ONE link to the most relevant article at the end.",
        "",
        "**Rules:**",
        "- 90% value, 10% self-promotion",
        "- No bare link drops — answer the question first",
        "- Mention the AI Tools Hub article only when it directly answers what was asked",
        "- Don't link to multiple articles — one contextual link per comment",
        "",
        "---",
        "",
    ]

    for sub, info in SUBREDDITS.items():
        print(f"\n→ r/{sub} ({info['members']})")
        for topic in info["topics"][:2]:  # Top 2 topics per sub
            print(f"  Searching: {topic}")
            text = search_reddit_questions(f"r/{sub} {topic}", limit=args.per_subreddit)
            urls = parse_reddit_urls(text)
            print(f"  Found {len(urls)} potential questions")

            for url in urls[:args.per_subreddit]:
                if url in log["answered"] or url in log["skipped"]:
                    continue
                all_leads.append({"subreddit": sub, "topic": topic, "url": url})

    # Group by subreddit
    by_sub = {}
    for lead in all_leads:
        by_sub.setdefault(lead["subreddit"], []).append(lead)

    for sub, leads in by_sub.items():
        report_lines.append(f"## r/{sub} ({SUBREDDITS[sub]['members']})")
        report_lines.append(f"*{SUBREDDITS[sub]['best_for']}*")
        report_lines.append("")
        for lead in leads:
            report_lines.append(f"- [{lead['topic']}] {lead['url']}")
        report_lines.append("")

    # Save report
    Path(args.output).write_text("\n".join(report_lines))
    print(f"\n✅ Saved {len(all_leads)} leads to {args.output}")
    print(f"   (Cross-check against /articles/ and /comparisons/ to find matches)")
    print(f"   Then open Reddit, write thoughtful reply, include ONE link to AI Tools Hub")


if __name__ == "__main__":
    main()
