#!/usr/bin/env python3
"""
AI-Image Video Generator.

Creates engaging YouTube videos by:
1. Splitting article into 60-second segments
2. Generating a unique AI image for each segment (via Pollinations.ai - free, no key)
3. Combining each image with its audio segment
4. Stitching into a final MP4

Each segment gets a custom scene with PEOPLE, OBJECTS, SETTINGS that match
what's being talked about. No more static text-on-gradient.
"""
import os
import sys
import json
import subprocess
import time
import urllib.parse
import urllib.request
import urllib.error
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).parent
VIDEO_DIR = ROOT / "videos"
AUDIO_DIR = ROOT / "audio"
SMART_DIR = ROOT / "smart_video"
TEMP_DIR = SMART_DIR / "temp"
OUTPUT_DIR = SMART_DIR / "output"
TEMP_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

CHUNK_DURATION = 60

# Theme colors (matching site branding)
THEMES = {
    "dark_indigo": {"bg": (10, 10, 20), "accent": (99, 102, 241), "text": (241, 241, 245)},
    "dark_amber": {"bg": (10, 10, 20), "accent": (245, 158, 11), "text": (241, 241, 245)},
    "dark_teal": {"bg": (10, 10, 20), "accent": (45, 212, 191), "text": (241, 241, 245)},
    "dark_pink": {"bg": (10, 10, 20), "accent": (236, 72, 153), "text": (241, 241, 245)},
}


def extract_keywords_from_chunk(text, max_keywords=8):
    """Extract visual-relevant keywords from chunk text."""
    # Remove common stop words
    stop_words = {"the", "a", "an", "and", "or", "but", "is", "are", "was", "were",
                  "in", "on", "at", "to", "for", "of", "with", "by", "from", "as",
                  "this", "that", "these", "those", "it", "its", "be", "have", "has",
                  "had", "do", "does", "did", "can", "could", "would", "should",
                  "you", "your", "we", "our", "they", "their", "them", "i"}

    words = re.findall(r'\b[a-z]{3,}\b', text.lower())
    keywords = []
    seen = set()
    for w in words:
        if w not in stop_words and w not in seen:
            keywords.append(w)
            seen.add(w)
            if len(keywords) >= max_keywords:
                break
    return keywords


def generate_image_prompt(keywords, chunk_text, article_title):
    """Generate a detailed image prompt based on chunk content."""
    # Pick a scene type based on keywords
    scenes = {
        "default": "modern minimalist workspace with a person using a laptop, dark moody lighting, cinematic",
        "laptop": "person working on a sleek laptop in a modern dark office, focused, soft screen glow",
        "code": "developer writing code on a laptop screen with glowing text, dark theme IDE, cinematic lighting",
        "writing": "writer composing text on laptop in cozy dark study, warm desk lamp light",
        "design": "designer creating visual content on dual monitors, dark creative studio, artistic lighting",
        "research": "researcher analyzing data on screen with papers and notes, dark academic atmosphere",
        "meeting": "professional team meeting around a table with laptops and screens, modern office",
        "image": "photographer viewing AI-generated artwork on large screen, dark gallery setting",
        "video": "video editor working with timeline on screen, dark studio with multiple monitors",
        "music": "music producer at workstation with waveforms and controls, atmospheric dark studio",
        "chat": "person having conversation with AI assistant on screen, friendly modern interface",
        "voice": "person recording voice with microphone and audio waveform visualizer, dark studio",
        "ai": "futuristic AI concept with glowing neural network patterns and data visualizations",
        "free": "person celebrating with hands raised, success concept, dark dramatic lighting",
        "compare": "split composition showing two AI tools side by side, comparison visualization",
        "student": "young student using laptop with notes and books, focused study atmosphere",
        "developer": "software engineer at multi-monitor workstation, dark IDE environment",
        "team": "professional team collaborating around screens, modern office aesthetic",
        "decision": "person at crossroads choosing between options, conceptual decision-making scene",
        "product": "product showcase with sleek modern devices arranged aesthetically, studio lighting",
        "abstract": "abstract digital art with flowing data streams, futuristic minimal aesthetic",
        "business": "business professional analyzing growth charts on large screen, corporate dark office",
    }

    # Match scene to keywords
    matched_scene = scenes["default"]
    for kw in keywords:
        if kw in scenes:
            matched_scene = scenes[kw]
            break

    # Build detailed prompt
    primary_kw = keywords[0] if keywords else "AI tools"
    prompt = f"{matched_scene}, subtle {primary_kw} references in the background, cinematic composition, professional, moody dark blue and indigo tones, soft volumetric lighting, photorealistic, 8k quality"

    return prompt


def fetch_ai_image(prompt, width=1280, height=720, retries=3):
    """Fetch AI-generated image from Pollinations.ai (free, no API key)."""
    encoded = urllib.parse.quote(prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded}?width={width}&height={height}&nologo=true&seed={int(time.time()) % 100000}"

    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
            })
            with urllib.request.urlopen(req, timeout=60) as resp:
                if resp.status == 200:
                    data = resp.read()
                    if len(data) > 5000:
                        return data
            time.sleep(2)
        except Exception as e:
            print(f"    Attempt {attempt+1} failed: {str(e)[:80]}")
            time.sleep(3)
    return None


def create_visual_frame(image_data, chunk_text, chunk_index, total_chunks, theme="dark_indigo"):
    """Create the final visual frame: AI image + text overlay."""
    t = THEMES[theme]
    width, height = 1280, 720

    # Open AI image
    from io import BytesIO
    try:
        img = Image.open(BytesIO(image_data)).convert("RGB")
        # Resize to fit
        img = img.resize((width, height), Image.Resampling.LANCZOS)
        # Slight blur + darken so text is readable
        overlay = Image.new("RGB", (width, height), color=(0, 0, 0))
        img = Image.blend(img, overlay, 0.3)  # 30% darken
    except Exception:
        # Fallback to solid color
        img = Image.new("RGB", (width, height), color=t["bg"])

    draw = ImageDraw.Draw(img)

    try:
        font_huge = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 56)
        font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 40)
        font_med = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 26)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
        font_tiny = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
    except Exception:
        font_huge = font_large = font_med = font_small = font_tiny = ImageFont.load_default()

    # === Top: chunk indicator + brand ===
    # Subtle dark bar at top for readability
    for y in range(80):
        alpha = 1 - (y / 80)
        draw.line([(0, y), (width, y)], fill=(0, 0, 0), width=1)

    chunk_label = f"PART {chunk_index + 1} / {total_chunks}"
    draw.text((40, 25), chunk_label, font=font_med, fill=t["accent"])

    # Brand on top-right
    brand = "AI Tools Hub"
    bbox = draw.textbbox((0, 0), brand, font=font_med)
    text_width = bbox[2] - bbox[0]
    draw.text((width - text_width - 40, 25), brand, font=font_med, fill=t["text"])

    # === Center: chunk snippet as quote ===
    chunk_text_clean = chunk_text.strip()
    if chunk_text_clean:
        # Take first 8-12 words for a punchy quote
        words = chunk_text_clean.split()[:10]
        snippet = " ".join(words)
        if len(snippet) > 70:
            snippet = snippet[:67] + "..."

        # Wrap to fit
        all_words = snippet.split()
        lines = []
        current = ""
        for w in all_words:
            test = (current + " " + w).strip()
            bbox = draw.textbbox((0, 0), test, font=font_huge)
            if bbox[2] - bbox[0] > width - 200 and current:
                lines.append(current)
                current = w
            else:
                current = test
        if current:
            lines.append(current)
        lines = lines[:3]

        # Draw as quote with accent bar
        bar_x = 60
        bar_y = 200
        bar_h = len(lines) * 75 - 15
        draw.rectangle([bar_x, bar_y, bar_x + 5, bar_y + bar_h], fill=t["accent"])

        snippet_y = 200
        for line in lines:
            draw.text((90, snippet_y), f'"{line}"', font=font_huge, fill=t["text"])
            snippet_y += 75

    # === Bottom: progress bar + subtitle ===
    # Bottom gradient strip
    for y in range(80):
        alpha = y / 80
        r = int(t["bg"][0] * (1 - alpha) + 0 * alpha)
        g = int(t["bg"][1] * (1 - alpha) + 0 * alpha)
        b = int(t["bg"][2] * (1 - alpha) + 0 * alpha)
        draw.line([(0, height - 80 + y), (width, height - 80 + y)], fill=(r, g, b), width=1)

    progress_pct = (chunk_index + 1) / total_chunks
    bar_y = height - 35
    bar_w = 600
    bar_x = 40

    draw.text((bar_x, bar_y - 28), "Progress", font=font_tiny, fill=t["accent"])
    draw.rectangle([bar_x, bar_y, bar_x + bar_w, bar_y + 6], fill=(40, 40, 60))
    draw.rectangle([bar_x, bar_y, bar_x + int(bar_w * progress_pct), bar_y + 6], fill=t["accent"])

    # Time elapsed / total on right
    elapsed_s = (chunk_index + 1) * CHUNK_DURATION
    total_s = total_chunks * CHUNK_DURATION
    time_text = f"{elapsed_s // 60}:{(elapsed_s % 60):02d} / {total_s // 60}:00"
    bbox = draw.textbbox((0, 0), time_text, font=font_med)
    text_width = bbox[2] - bbox[0]
    draw.text((width - text_width - 40, height - 50), time_text, font=font_med, fill=t["text"])

    return img


def render_chunk_video(audio_path, visual_img, output_path, duration):
    """Render a single chunk as video (static visual + audio)."""
    frame_path = TEMP_DIR / f"frame_{output_path.stem}.png"
    visual_img.save(frame_path)

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", str(frame_path),
        "-i", str(audio_path),
        "-c:v", "libx264", "-tune", "stillimage",
        "-c:a", "aac", "-b:a", "128k",
        "-pix_fmt", "yuv420p",
        "-shortest",
        "-t", str(duration),
        str(output_path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    frame_path.unlink(missing_ok=True)
    return result.returncode == 0


def extract_audio(video_path, output_dir):
    """Extract audio chunks from video."""
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(video_path)],
        capture_output=True, text=True, timeout=10
    )
    total = float(result.stdout.strip())
    n_chunks = int(total / CHUNK_DURATION) + 1
    video_name = Path(video_path).stem

    chunks = []
    for i in range(n_chunks):
        start = i * CHUNK_DURATION
        if start >= total:
            break
        duration = min(CHUNK_DURATION, total - start)
        chunk_audio = output_dir / f"{video_name}_audio_{i:03d}.mp3"
        result = subprocess.run([
            "ffmpeg", "-y", "-i", str(video_path),
            "-ss", str(start), "-t", str(duration),
            "-vn", "-acodec", "libmp3lame", "-ab", "128k", str(chunk_audio)
        ], capture_output=True, text=True, timeout=30)
        if chunk_audio.exists() and chunk_audio.stat().st_size > 1000:
            chunks.append({"start": start, "duration": duration, "audio": chunk_audio})
    return chunks, total, n_chunks


def split_text_into_segments(text, n_segments):
    """Split article text into proportional chunks."""
    if not text:
        return [""] * n_segments
    words = text.split()
    words_per_segment = max(80, len(words) // n_segments)
    segments = []
    for i in range(n_segments):
        start = i * words_per_segment
        end = min((i + 1) * words_per_segment, len(words))
        segments.append(" ".join(words[start:end]))
    return segments


def load_article(slug):
    """Load article meta + body."""
    meta_file = ROOT / "articles" / slug / "meta.json"
    body_file = ROOT / "articles" / slug / "body.html"
    if not meta_file.exists() or not body_file.exists():
        return None
    meta = json.loads(meta_file.read_text())
    body = body_file.read_text()
    # Strip HTML
    body_text = re.sub(r'<script[^>]*>.*?</script>', '', body, flags=re.DOTALL)
    body_text = re.sub(r'<style[^>]*>.*?</style>', '', body_text, flags=re.DOTALL)
    body_text = re.sub(r'<[^>]+>', ' ', body_text)
    body_text = re.sub(r'\s+', ' ', body_text)
    import html as htmlmod
    body_text = htmlmod.unescape(body_text).strip()
    return meta, body_text


def concat_chunks(chunk_videos, output_path):
    """Stitch all chunks together."""
    list_file = TEMP_DIR / "concat.txt"
    with open(list_file, "w") as f:
        for cv in chunk_videos:
            f.write(f"file '{cv.absolute()}'\n")

    result = subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(list_file),
        "-c", "copy", str(output_path)
    ], capture_output=True, text=True, timeout=120)
    return result.returncode == 0


def process_video(video_path, slug):
    """Main pipeline: extract audio → fetch AI images → render → stitch."""
    print("=" * 60)
    print(f"AI-Image Video Generator")
    print(f"Source: {video_path.name}")
    print(f"Article: {slug}")
    print("=" * 60)

    # Load article
    article = load_article(slug)
    if not article:
        print(f"ERROR: Article '{slug}' not found")
        return None
    meta, body_text = article
    print(f"Article: {meta['title'][:60]}")
    print(f"Body: {len(body_text.split())} words\n")

    # Extract audio chunks
    chunks, total_duration, n_chunks = extract_audio(video_path, TEMP_DIR)
    actual_chunks = len(chunks)
    print(f"Audio: {actual_chunks} chunks of {CHUNK_DURATION}s ({total_duration:.1f}s total)")

    # Split article text into proportional segments
    text_segments = split_text_into_segments(body_text, actual_chunks)

    # Theme rotation based on chunk
    theme_keys = list(THEMES.keys())

    # Process each chunk: fetch AI image + create visual + render
    chunk_videos = []
    for i, chunk in enumerate(chunks):
        print(f"\n[{i+1}/{actual_chunks}] {chunk['start']:.0f}s - {chunk['start']+chunk['duration']:.0f}s")

        # Extract keywords + build prompt
        keywords = extract_keywords_from_chunk(text_segments[i])
        prompt = generate_image_prompt(keywords, text_segments[i], meta.get("title", ""))
        print(f"  Prompt: {prompt[:80]}...")

        # Fetch AI image
        theme = theme_keys[i % len(theme_keys)]
        print(f"  Fetching AI image (theme: {theme})...")
        image_data = fetch_ai_image(prompt, width=1280, height=720)

        if image_data is None:
            print(f"  ⚠ AI image fetch failed — using fallback solid background")
            # Fallback: create a solid-color frame
            img = Image.new("RGB", (1280, 720), color=THEMES[theme]["bg"])
        else:
            print(f"  ✓ AI image fetched ({len(image_data)} bytes)")

        # Create visual frame
        visual = create_visual_frame(
            image_data or b"", text_segments[i], i, actual_chunks, theme
        ) if image_data else create_visual_frame_fallback(theme, text_segments[i], i, actual_chunks)

        # Render chunk
        chunk_video = TEMP_DIR / f"ai_chunk_{i:03d}.mp4"
        ok = render_chunk_video(chunk["audio"], visual, chunk_video, chunk["duration"])
        if ok:
            chunk_videos.append(chunk_video)
            print(f"  ✓ Rendered: {chunk_video.name}")
        else:
            print(f"  ✗ Failed to render chunk {i+1}")

        # Rate limit for image API
        if i < actual_chunks - 1:
            time.sleep(2)

    if not chunk_videos:
        print("\nNo chunks rendered")
        return None

    # Stitch
    output_path = OUTPUT_DIR / f"{Path(video_path).stem}_ai.mp4"
    print(f"\nStitching {len(chunk_videos)} chunks...")
    if concat_chunks(chunk_videos, output_path):
        size_mb = output_path.stat().st_size / (1024 * 1024)
        print(f"\n✓ Generated: {output_path.name} ({size_mb:.1f}MB)")
        return output_path
    return None


def create_visual_frame_fallback(theme, chunk_text, chunk_index, total_chunks):
    """Fallback when AI image fails - use text on solid bg."""
    t = THEMES[theme]
    width, height = 1280, 720
    img = Image.new("RGB", (width, height), color=t["bg"])
    draw = ImageDraw.Draw(img)
    try:
        font_huge = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 56)
        font_med = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 26)
    except Exception:
        font_huge = font_med = ImageFont.load_default()

    draw.text((60, 50), f"Part {chunk_index+1} / {total_chunks}", font=font_med, fill=t["accent"])
    chunk_clean = chunk_text.strip()[:80]
    if chunk_clean:
        draw.text((60, 280), f'"{chunk_clean}"', font=font_huge, fill=t["text"])
    return img


def main():
    video_path = VIDEO_DIR / "best-free-ai-tools-2026.mp4"
    slug = "best-free-ai-tools-2026"

    if len(sys.argv) > 1:
        video_path = Path(sys.argv[1])
        slug = video_path.stem

    if not video_path.exists():
        print(f"Video not found: {video_path}")
        return

    result = process_video(video_path, slug)
    if result:
        print(f"\n🎬 AI-Image video: {result}")


if __name__ == "__main__":
    main()
