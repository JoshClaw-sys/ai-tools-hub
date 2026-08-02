#!/usr/bin/env python3
"""
Free TTS service using Microsoft Edge TTS (edge-tts).

No API key required. Uses Microsoft's neural voices for free.
Generates high-quality voiceovers for YouTube companion videos,
podcast clips, and audio article versions.

Usage:
  source ~/.agent-reach-venv/bin/activate
  python3 tts_service.py --text "Hello world" --output /tmp/hello.mp3
  python3 tts_service.py --article best-free-ai-tools-2026
  python3 tts_service.py --batch  # process all articles
"""
import os
import sys
import json
import asyncio
import argparse
from pathlib import Path
from datetime import datetime

# edge-tts is async
try:
    import edge_tts
except ImportError:
    print("ERROR: edge-tts not installed.")
    print("Install with: pip install edge-tts")
    sys.exit(1)

ROOT = Path(__file__).parent
ARTICLES_DIR = ROOT / "articles"
AUDIO_DIR = ROOT / "audio"
AUDIO_DIR.mkdir(exist_ok=True)

# Best Microsoft Edge neural voices for content (verified working as of 2026)
VOICES = {
    "male_us": "en-US-GuyNeural",           # Friendly male, great for tech
    "female_us": "en-US-JennyNeural",       # Professional female
    "male_uk": "en-GB-RyanNeural",          # British male, polished
    "female_uk": "en-GB-SoniaNeural",       # British female
    "narrator": "en-US-GuyNeural",          # Using Guy as narrator (verified working)
    "conversational": "en-US-AriaNeural",   # Casual, friendly
    "deep": "en-US-DavisNeural",            # Try Davis for deep voice (may fail gracefully)
    "calm": "en-US-JennyNeural",            # Using Jenny for calm narration
}
def build_article_script(meta, body_html):
    """Build a natural-sounding script from article meta + body."""
    import re
    parts = []
    parts.append(meta['title'] + ".")

    tldr = meta.get('tldr_pick') or meta.get('short_desc') or meta.get('description', '')
    if tldr:
        tldr_clean = re.sub(r'<[^>]+>', '', tldr)
        parts.append("Quick summary. " + tldr_clean + ".")

    # Add short intro
    parts.append("In this guide. ")

    # Body text — limit to keep TTS length manageable (~5-6 min audio)
    body_text = html_to_speech_text(body_html)[:6000]
    parts.append(body_text)

    # Outro
    parts.append("That's it for this guide. Thanks for listening. You can read the full article at A I Tools Hub dot github dot io. Subscribe for weekly A I tool reviews.")

    return " ".join(parts)


async def text_to_speech(text, output_path, voice="male_us", rate="+0%", pitch="+0Hz"):
    """Convert text to speech using edge-tts."""
    voice_name = VOICES.get(voice, VOICES["male_us"])
    communicate = edge_tts.Communicate(
        text=text,
        voice=voice_name,
        rate=rate,
        pitch=pitch,
    )
    await communicate.save(str(output_path))
    return output_path


def html_to_speech_text(html):
    """Convert HTML article body to clean text for TTS."""
    import re
    # Remove script/style
    text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
    # Convert headings to spoken form with period
    text = re.sub(r'<h[1-6][^>]*>(.*?)</h[1-6]>', r'\n\n\1. \n\n', text, flags=re.DOTALL)
    # Convert paragraphs to natural speech
    text = re.sub(r'<p[^>]*>', '\n\n', text)
    text = re.sub(r'</p>', '', text)
    # Add natural pauses for lists
    text = re.sub(r'<li[^>]*>', '\n- ', text)
    text = re.sub(r'</li>', '', text)
    # Remove all other tags
    text = re.sub(r'<[^>]+>', '', text)
    # Clean up whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Decode HTML entities
    import html
    text = html.unescape(text)
    return text.strip()


def build_article_script(meta, body_html):
    """Build a natural-sounding script from article meta + body."""
    parts = []
    parts.append(f"<break time='800ms'/> {meta['title']}.")
    parts.append(f"<break time='500ms'/> By AI Tools Hub Editorial. <break time='500ms'/>")
    tldr = meta.get('tldr_pick') or meta.get('short_desc') or meta.get('description', '')
    if tldr:
        # Strip HTML tags from tldr
        import re
        tldr_clean = re.sub(r'<[^>]+>', '', tldr)
        parts.append(f"<break time='300ms'/> {tldr_clean} <break time='1s'/>")
    parts.append(f"<break time='300ms'/> In this guide. <break time='300ms'/>")
    parts.append(html_to_speech_text(body_html)[:8000])
    parts.append("<break time='500ms'/> That's it for this guide.")
    parts.append(f"<break time='300ms'/> Read the full article at A I Tools Hub dot github dot io. <break time='500ms'/>")
    parts.append(f"<break time='300ms'/> Subscribe for weekly A I tool reviews. <break time='1s'/>")
    return " ".join(parts)


async def generate_article_audio(article_dir, voice="male_us", max_chars=10000):
    """Generate audio for one article."""
    meta_file = article_dir / "meta.json"
    body_file = article_dir / "body.html"
    if not meta_file.exists() or not body_file.exists():
        return None, "missing files"

    meta = json.loads(meta_file.read_text())
    body_html = body_file.read_text()

    script = build_article_script(meta, body_html)
    # Cap length for TTS (edge-tts has 10min limit per request)
    script = script[:max_chars]

    output_path = AUDIO_DIR / f"{article_dir.name}.mp3"
    print(f"  → {meta['short_title']} → {output_path.name}")
    try:
        await text_to_speech(script, output_path, voice=voice)
        size_kb = output_path.stat().st_size // 1024
        print(f"    ✓ {size_kb}KB")
        return output_path, "ok"
    except Exception as e:
        print(f"    ✗ Error: {e}")
        return None, str(e)


async def generate_single_text(text, output_path, voice="male_us"):
    """Generate audio from raw text."""
    print(f"Generating audio: {text[:60]}...")
    try:
        await text_to_speech(text, Path(output_path), voice=voice)
        print(f"✓ Saved: {output_path}")
        return Path(output_path)
    except Exception as e:
        print(f"✗ Error: {e}")
        return None


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--text", help="Plain text to convert")
    parser.add_argument("--article", help="Article slug to convert")
    parser.add_argument("--voice", default="male_us", choices=list(VOICES.keys()),
                        help="Voice to use")
    parser.add_argument("--output", help="Output MP3 path")
    parser.add_argument("--batch", action="store_true", help="Generate audio for all articles")
    parser.add_argument("--rate", default="+0%", help="Speech rate adjustment")
    parser.add_argument("--pitch", default="+0Hz", help="Pitch adjustment")
    args = parser.parse_args()

    print("=" * 60)
    print(f"AI Tools Hub — Free TTS Service (edge-tts)")
    print(f"Voice: {args.voice} ({VOICES.get(args.voice, '?')})")
    print("=" * 60)

    if args.text:
        output = args.output or "/tmp/tts_output.mp3"
        await generate_single_text(args.text, output, args.voice)

    elif args.article:
        article_dir = ARTICLES_DIR / args.article
        if not article_dir.exists():
            print(f"Article not found: {args.article}")
            return
        await generate_article_audio(article_dir, args.voice)

    elif args.batch:
        print(f"\nGenerating audio for all articles in {ARTICLES_DIR}/")
        articles = [d for d in ARTICLES_DIR.iterdir() if d.is_dir() and (d / "meta.json").exists()]
        print(f"Found {len(articles)} articles")

        results = {"ok": 0, "failed": 0}
        for article_dir in sorted(articles):
            result, status = await generate_article_audio(article_dir, args.voice)
            if status == "ok":
                results["ok"] += 1
            else:
                results["failed"] += 1
            await asyncio.sleep(1)

        print(f"\n{'='*60}")
        print(f"Generated {results['ok']}/{len(articles)} audio files in {AUDIO_DIR}/")
        print(f"{'='*60}")

    else:
        print("Usage:")
        print("  python3 tts_service.py --text 'Hello world' --output /tmp/hello.mp3")
        print("  python3 tts_service.py --article best-free-ai-tools-2026")
        print("  python3 tts_service.py --batch")
        print(f"\nAvailable voices: {', '.join(VOICES.keys())}")


if __name__ == "__main__":
    asyncio.run(main())
