# Directory Submission Guide — AI Tools Hub

This guide lists every directory that needs manual submission (the script couldn't auto-submit due to JavaScript rendering or bot protection). Each submission takes 2-5 minutes.

## Submission Kit (copy-paste for all directories)

**Site name:** AI Tools Hub
**Tagline (60 chars):** Honest, no-fluff AI tool reviews for 2026.
**URL:** https://joshclaw-sys.github.io/ai-tools-hub/
**Logo:** https://joshclaw-sys.github.io/ai-tools-hub/assets/logo.png
**Email:** hello@ai-tools-hub.example
**Twitter:** @AIToolsHub

**Description (150 words):**
> AI Tools Hub is the no-nonsense guide to AI tools that matter in 2026. We test every tool with real workflows — writing, coding, research, image generation, voice — and rank them honestly. No sponsored fluff, no affiliate bias. Every article includes a clear top pick, "best for" recommendations, a side-by-side comparison table, specific test methodology, and an honest "skip this" section when a popular tool doesn't deliver. We update monthly as the AI landscape shifts. Currently covering 50+ AI tools across LLMs, image generators, code assistants, voice AI, and productivity tools — with new guides published daily.

**Categories:** AI Tools, Artificial Intelligence, Productivity, Software, Technology

## Priority Submissions (highest DA, do these first)

| # | Directory | URL | DA | Notes |
|---|-----------|-----|----|----|
| 1 | **Futurepedia** | https://www.futurepedia.io/submit-tool | 55 | Free, 50k+ monthly visitors, biggest AI directory |
| 2 | **Product Hunt** | https://www.producthunt.com/posts/new | 90 | Launch day only, build to 30+ articles first |
| 3 | **AllAboutAI** | https://www.allaboutai.com/submit-tool/ | 70 | 1500+ tools, requires login |
| 4 | **ThereIsAnAIForThat** | https://theresanaiforthat.com/submit | 45 | High traffic, well-indexed |
| 5 | **Appscribed** | https://appscribed.com/submit-tool/ | 60 | 3000+ tools listed |
| 6 | **Toolify** | https://www.toolify.ai/submit | 40 | High traffic |
| 7 | **TopAI.tools** | https://topai.tools/submit | 35 | Free directory |
| 8 | **AI Top Tools** | https://www.aitoptools.com/submit | 40 | Free |
| 9 | **AIChief** | https://aichief.com/submit | 35 | Free |
| 10 | **FutureTools** | https://futuretools.io/submit | 35 | Free |
| 11 | **BestAI.tools** | https://bestai.tools/submit | 30 | Free |
| 12 | **AI Tool Flow** | https://ai-toolflow.com/submit | 35 | Free |
| 13 | **AI Tool Hunt** | https://aitoolhunt.com/submit | 35 | Free |
| 14 | **Insidr AI** | https://www.insidr.ai/submit | 25 | Free |
| 15 | **AI Nav** | https://ai-nav.net/submit | 25 | Free |
| 16 | **AI Hunt List** | https://aihuntlist.com/submit | 30 | Free |
| 17 | **AI Tools Directory** | https://aitoolsdirectory.com/submit | 30 | Free |
| 18 | **AI Tool List** | https://ai-tool-list.com/submit | 30 | Free |
| 19 | **AI Sites** | https://ai-sites.net/submit | 25 | Free |
| 20 | **AI Hub** | https://aihubs.ai/submit | 30 | Free |
| 21 | **Cool AI Tools** | https://cool-ai-tools.com/submit | 25 | Free |
| 22 | **AI Agents Directory** | https://aiagentsdirectory.com/submit | 40 | Agent-focused |
| 23 | **AI Directory Wiki** | https://aidirectory.wiki/submit | 30 | Free |
| 24 | **AI Dir** | https://aidir.wiki/submit | 25 | Free |
| 25 | **AI Kaptan** | https://aikaptan.com/submit | 30 | Free |

## How to Submit (5-minute workflow)

1. **Open the submission URL** in a browser
2. **Sign up / log in** if needed (use a Google account or your GitHub-linked email)
3. **Copy-paste from the submission kit above** — most sites have these exact fields:
   - Site/Project name → AI Tools Hub
   - URL → https://joshclaw-sys.github.io/ai-tools-hub/
   - Tagline (60 chars) → Honest, no-fluff AI tool reviews for 2026.
   - Description → paste the full 150-word version
   - Category → AI Tools or similar
   - Logo → upload from the URL above
4. **Submit** — most free directories approve within 24-48 hours

## Time Investment

- **8-10 minutes per directory** (most have 3-4 form fields + email verification)
- **25 directories × 10 min = ~4 hours total**
- Recommended: **Do 5 per day for 5 days** = 30 min/day for a week

## What Happens After Submission

- Most directories list within 24-48 hours
- Each listing gives you a backlink (good for SEO)
- Some directories drive direct traffic (Futurepedia, AllAboutAI get 50k+ monthly visitors)
- Higher DA = more SEO value

## Tracking

The script `submit_directories.py` tracks which directories you've submitted to in `submit_log.json`. After you submit manually, run:

```bash
cd ~/projects/ai-for-india
python3 -c "
import json
from pathlib import Path
log = json.loads(Path('submit_log.json').read_text())
log['submitted']['Futurepedia'] = {
    'url': 'https://www.futurepedia.io/submit',
    'da': 55,
    'submitted_at': '2026-08-02T19:30:00Z',
    'method': 'manual'
}
Path('submit_log.json').write_text(json.dumps(log, indent=2))
"
```

Replace `Futurepedia` and details with whichever directory you just submitted to.

## Submission Tracker

| # | Directory | Submitted | Listed | DA | Notes |
|---|-----------|-----------|--------|----|----|
| 1 | Futurepedia | ⬜ | | 55 | |
| 2 | Product Hunt | ⬜ | | 90 | Wait for 30+ articles |
| 3 | AllAboutAI | ⬜ | | 70 | |
| 4 | ThereIsAnAIForThat | ⬜ | | 45 | |
| 5 | Appscribed | ⬜ | | 60 | |
| 6 | Toolify | ⬜ | | 40 | |
| 7 | TopAI.tools | ⬜ | | 35 | |
| 8 | AI Top Tools | ⬜ | | 40 | |
| 9 | AIChief | ⬜ | | 35 | |
| 10 | FutureTools | ⬜ | | 35 | |
| 11-25 | (remaining directories) | ⬜ | | | |
