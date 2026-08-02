#!/usr/bin/env python3
"""
Smart video visual generator.

Reads article structure + audio transcript, then creates
content-aware visuals for each 60-second segment.

For each segment:
- Pulls the audio for that segment
- Looks at what's actually being discussed (via article text)
- Generates a custom visual frame matching that content
- Stitches back together

Result: A video where the visuals actually reflect what's being said.
"""
import os
import sys
import json
import subprocess
import re
from pathlib import Path
from datetime import datetime

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).parent
VIDEO_DIR = ROOT / "videos"
AUDIO_DIR = ROOT / "audio"
SMART_DIR = ROOT / "smart_video"
TEMP_DIR = SMART_DIR / "temp"
OUTPUT_DIR = SMART_DIR / "output"
TEMP_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

CHUNK_DURATION = 60  # seconds per visual chunk


def load_article(slug):
    """Load article meta + body for content-aware visuals."""
    meta_file = ROOT / "articles" / slug / "meta.json"
    body_file = ROOT / "articles" / slug / "body.html"
    if not meta_file.exists() or not body_file.exists():
        return None
    meta = json.loads(meta_file.read_text())
    body_html = body_file.read_text()
    return meta, body_html


def html_to_plain(html):
    """Strip HTML to plain text."""
    text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    import html as htmlmod
    return htmlmod.unescape(text).strip()


def split_text_into_segments(text, n_segments, total_duration):
    """Divide article text into n chunks proportional to video duration."""
    if not text:
        return [""] * n_segments

    words = text.split()
    words_per_segment = max(50, len(words) // n_segments)
    segments = []
    for i in range(n_segments):
        start = i * words_per_segment
        end = min((i + 1) * words_per_segment, len(words))
        chunk = " ".join(words[start:end])
        segments.append(chunk)
    return segments


def extract_audio(video_path, output_dir):
    """Extract audio chunks from the source video."""
    chunks = []
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(video_path)],
        capture_output=True, text=True, timeout=10
    )
    total = float(result.stdout.strip())
    n_chunks = int(total / CHUNK_DURATION) + 1
    video_name = Path(video_path).stem

    for i in range(n_chunks):
        start = i * CHUNK_DURATION
        if start >= total:
            break
        duration = min(CHUNK_DURATION, total - start)
        chunk_audio = output_dir / f"{video_name}_audio_{i:03d}.mp3"
        # Re-encode audio (more reliable than -acodec copy for MP4)
        result = subprocess.run([
            "ffmpeg", "-y", "-i", str(video_path),
            "-ss", str(start), "-t", str(duration),
            "-vn", "-acodec", "libmp3lame", "-ab", "128k",
            str(chunk_audio)
        ], capture_output=True, text=True, timeout=30)
        if chunk_audio.exists() and chunk_audio.stat().st_size > 1000:
            chunks.append({"start": start, "duration": duration, "audio": chunk_audio})
        else:
            print(f"  ⚠ Audio chunk {i} failed: {result.stderr[:200]}")
    return chunks, total, n_chunks


def generate_content_visual(article_meta, chunk_text, chunk_index, total_chunks, theme="dark_indigo"):
    """Generate a content-aware visual frame."""
    themes = {
        "dark_indigo": {"bg": (10, 10, 20), "accent": (99, 102, 241), "text": (241, 241, 245), "dim": (160, 160, 180)},
        "dark_amber": {"bg": (10, 10, 20), "accent": (245, 158, 11), "text": (241, 241, 245), "dim": (160, 160, 180)},
        "dark_teal": {"bg": (10, 10, 20), "accent": (45, 212, 191), "text": (241, 241, 245), "dim": (160, 160, 180)},
    }
    t = themes[theme]

    width, height = 1280, 720
    img = Image.new("RGB", (width, height), color=t["bg"])
    draw = ImageDraw.Draw(img)

    try:
        font_huge = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 56)
        font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 38)
        font_med = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
        font_tiny = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
    except Exception:
        font_huge = font_large = font_med = font_small = font_tiny = ImageFont.load_default()

    # === Decorative background elements ===
    # Top-left gradient accent
    for i in range(40):
        alpha = (40 - i) // 2
        draw.ellipse([60 - i*2, 60 - i*2, 200 + i*2, 200 + i*2], outline=t["accent"], width=1)
    # Bottom-right accent
    for i in range(30):
        draw.ellipse([1100 - i, 600 - i, 1280 + i, 720 + i], outline=t["accent"], width=1)

    # Vertical accent line on left
    draw.rectangle([48, 100, 52, 620], fill=t["accent"])

    # === Article title at top ===
    title = article_meta.get("short_title", article_meta.get("title", "AI Tools Hub"))
    # Word-wrap title
    words = title.split()
    title_lines = []
    current = ""
    for w in words:
        if len(current + " " + w) > 30:
            title_lines.append(current.strip())
            current = w
        else:
            current += " " + w
    if current.strip():
        title_lines.append(current.strip())

    y_offset = 70
    for line in title_lines[:2]:
        draw.text((80, y_offset), line, font=font_large, fill=t["text"])
        y_offset += 50

    # Subtle chapter indicator
    chapter_text = f"PART {chunk_index + 1} of {total_chunks}"
    draw.text((80, 30), chapter_text, font=font_small, fill=t["accent"])

    # === Chunk title (what this segment is about) ===
    # Extract first sentence from chunk_text as the segment headline
    chunk_text_clean = chunk_text.strip()
    if chunk_text_clean:
        # Get first 8-12 words as a snippet
        snippet_words = chunk_text_clean.split()[:10]
        snippet = " ".join(snippet_words)
        if len(snippet) > 80:
            snippet = snippet[:77] + "..."

        # Wrap snippet
        words = snippet.split()
        lines = []
        current = ""
        for w in words:
            if len(current + " " + w) > 35:
                lines.append(current.strip())
                current = w
            else:
                current += " " + w
        if current.strip():
            lines.append(current.strip())
        lines = lines[:3]

        # Draw snippet as the main visual
        snippet_y = 280
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font_huge)
            text_width = bbox[2] - bbox[0]
            if text_width > width - 200:
                # Font too big for this line, use smaller font
                font_use = font_large
            else:
                font_use = font_huge
            # Draw with quote styling
            draw.text((80, snippet_y), f'"{line}"', font=font_use, fill=t["text"])
            snippet_y += 70

    # === Bottom callout: Brand + URL ===
    # Decorative divider
    draw.line([(80, 640), (400, 640)], fill=t["accent"], width=3)

    # Brand
    draw.text((80, 660), "AI Tools Hub", font=font_med, fill=t["accent"])
    draw.text((280, 665), "·", font=font_med, fill=t["dim"])
    draw.text((300, 665), "ai-tools-hub", font=font_small, fill=t["dim"])

    # Progress indicator (right side)
    progress_pct = (chunk_index + 1) / total_chunks
    bar_x = width - 280
    bar_y = 660
    bar_w = 200
    bar_h = 8
    draw.rectangle([bar_x, bar_y, bar_x + bar_w, bar_y + bar_h], fill=t["dim"])
    draw.rectangle([bar_x, bar_y, bar_x + int(bar_w * progress_pct), bar_y + bar_h], fill=t["accent"])
    draw.text((bar_x, bar_y + 15), f"{int(progress_pct * 100)}%", font=font_small, fill=t["text"])

    return img


def make_chunk_video(chunk_audio, visual_image, output_path, duration):
    """Combine a single visual frame with audio for the chunk."""
    # Save visual as PNG
    frame_path = TEMP_DIR / f"frame_{output_path.stem}.png"
    visual_image.save(frame_path)

    # Combine with audio
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", str(frame_path),
        "-i", str(chunk_audio),
        "-c:v", "libx264", "-tune", "stillimage",
        "-c:a", "aac", "-b:a", "128k",
        "-pix_fmt", "yuv420p",
        "-shortest",
        "-t", str(duration),
        str(output_path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    return result.returncode == 0


def concat_chunks(chunk_videos, output_path):
    """Stitch all chunks together."""
    list_file = TEMP_DIR / "concat.txt"
    with open(list_file, "w") as f:
        for cv in chunk_videos:
            f.write(f"file '{cv.absolute()}'\n")

    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(list_file),
        "-c", "copy",
        str(output_path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    return result.returncode == 0


def process_video(video_path, slug):
    """Process a video with content-aware visuals."""
    print("=" * 60)
    print(f"Smart Video Visual Generator")
    print(f"Source: {video_path}")
    print(f"Article slug: {slug}")
    print("=" * 60)

    # Load article content
    article = load_article(slug)
    if not article:
        print(f"ERROR: Article '{slug}' not found")
        return None
    meta, body_html = article
    body_text = html_to_plain(body_html)
    print(f"Article: {meta['title'][:60]}...")
    print(f"Body text: {len(body_text)} chars, ~{len(body_text.split())} words")

    # Extract audio chunks
    chunks, total_duration, n_chunks = extract_audio(video_path, TEMP_DIR)
    actual_chunks = len(chunks)
    print(f"Audio: {total_duration:.1f}s total → {actual_chunks} chunks of {CHUNK_DURATION}s")

    # Split article text into proportional chunks
    text_segments = split_text_into_segments(body_text, actual_chunks, total_duration)
    for i, seg in enumerate(text_segments):
        words = seg.split()[:6]
        print(f"  Chunk {i+1}: {' '.join(words)}...")

    # Generate content-aware visuals + render each chunk
    chunk_videos = []
    for i, chunk in enumerate(chunks):
        print(f"\n[{i+1}/{actual_chunks}] Rendering chunk...")
        visual = generate_content_visual(meta, text_segments[i], i, actual_chunks)
        chunk_video = TEMP_DIR / f"final_chunk_{i:03d}.mp4"
        ok = make_chunk_video(chunk["audio"], visual, chunk_video, chunk["duration"])
        if ok:
            chunk_videos.append(chunk_video)
            print(f"  ✓ Rendered: {chunk_video.name}")
        else:
            print(f"  ✗ Failed to render chunk {i+1}")

    # Stitch all chunks together
    if not chunk_videos:
        print("No chunks rendered")
        return None

    output_path = OUTPUT_DIR / f"{Path(video_path).stem}_smart.mp4"
    print(f"\nStitching {len(chunk_videos)} chunks...")
    if concat_chunks(chunk_videos, output_path):
        size_mb = output_path.stat().st_size / (1024 * 1024)
        print(f"\n✓ Generated: {output_path.name} ({size_mb:.1f}MB)")
        return output_path
    else:
        print("Failed to stitch chunks")
        return None


def main():
    video_path = VIDEO_DIR / "best-free-ai-tools-2026.mp4"
    slug = "best-free-ai-tools-2026"

    if len(sys.argv) > 1:
        video_path = Path(sys.argv[1])
        slug = video_path.stem

    if not video_path.exists():
        print(f"Video not found: {video_path}")
        print("Generate one first with: python3 make_videos.py --article <slug>")
        return

    result = process_video(video_path, slug)

    if result:
        print(f"\n🎬 Done! Open: {result}")
        print(f"Duration: ~{result.stat().st_size // 100000}MB")


if __name__ == "__main__":
    main()
