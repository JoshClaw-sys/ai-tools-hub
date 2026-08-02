#!/usr/bin/env python3
"""
YouTube companion video generator for AI Tools Hub.

Generates MP4 videos by combining:
- TTS audio (from tts_service.py)
- Title cards rendered as PNG via PIL
- Animated backgrounds generated via ffmpeg

Output: MP4 video files ready for YouTube upload.

Usage:
  python3 make_videos.py --article best-free-ai-tools-2026
  python3 make_videos.py --all
"""
import os
import sys
import json
import subprocess
import argparse
from pathlib import Path
from datetime import datetime

# PIL for rendering text
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).parent
ARTICLES_DIR = ROOT / "articles"
AUDIO_DIR = ROOT / "audio"
VIDEO_DIR = ROOT / "videos"
TEMP_DIR = VIDEO_DIR / "temp"
VIDEO_DIR.mkdir(exist_ok=True)
TEMP_DIR.mkdir(exist_ok=True)

# Font paths (Debian/Ubuntu default)
FONT_BOLD_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REGULAR_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

# Visual themes
THEMES = {
    "dark_indigo": {
        "bg_color": (10, 10, 20),       # #0a0a14
        "accent_color": (99, 102, 241), # #6366f1
        "secondary_color": (139, 92, 246), # #8b5cf6
        "title_color": (241, 241, 245), # #f1f1f5
    },
    "dark_amber": {
        "bg_color": (10, 10, 20),
        "accent_color": (245, 158, 11), # #f59e0b
        "secondary_color": (239, 68, 68), # #ef4444
        "title_color": (254, 243, 199), # #fef3c7
    },
    "dark_teal": {
        "bg_color": (10, 10, 20),
        "accent_color": (45, 212, 191), # #2dd4bf
        "secondary_color": (6, 182, 212), # #06b6d4
        "title_color": (207, 250, 254), # #cffafe
    },
}


def check_ffmpeg():
    """Verify ffmpeg is installed."""
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"], capture_output=True, text=True, timeout=10
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


def render_title_card_png(title, subtitle, theme_name="dark_indigo", width=1280, height=720):
    """Render a title card as a PNG image using PIL."""
    theme = THEMES.get(theme_name, THEMES["dark_indigo"])

    # Create image with background color
    img = Image.new("RGB", (width, height), color=theme["bg_color"])
    draw = ImageDraw.Draw(img)

    # Load fonts
    try:
        font_title = ImageFont.truetype(FONT_BOLD_PATH, 72)
        font_subtitle = ImageFont.truetype(FONT_REGULAR_PATH, 36)
        font_brand = ImageFont.truetype(FONT_BOLD_PATH, 28)
    except Exception:
        font_title = ImageFont.load_default()
        font_subtitle = ImageFont.load_default()
        font_brand = ImageFont.load_default()

    # Draw title (multi-line if needed)
    title_lines = []
    words = title.split()
    current_line = ""
    for word in words:
        if len(current_line + " " + word) > 25:
            title_lines.append(current_line.strip())
            current_line = word
        else:
            current_line += " " + word
    if current_line:
        title_lines.append(current_line.strip())

    # Center title vertically
    line_height = 80
    total_height = len(title_lines) * line_height
    start_y = (height - total_height) // 2 - 30

    for i, line in enumerate(title_lines):
        bbox = draw.textbbox((0, 0), line, font=font_title)
        text_width = bbox[2] - bbox[0]
        x = (width - text_width) // 2
        draw.text((x, start_y + i * line_height), line, font=font_title, fill=theme["accent_color"])

    # Subtitle (date)
    bbox = draw.textbbox((0, 0), subtitle, font=font_subtitle)
    text_width = bbox[2] - bbox[0]
    x = (width - text_width) // 2
    draw.text((x, start_y + total_height + 30), subtitle, font=font_subtitle, fill=theme["title_color"])

    # Brand "AI Tools Hub" at bottom
    brand = "AI Tools Hub"
    bbox = draw.textbbox((0, 0), brand, font=font_brand)
    text_width = bbox[2] - bbox[0]
    x = (width - text_width) // 2
    draw.text((x, height - 60), brand, font=font_brand, fill=theme["secondary_color"])

    # Save
    output_path = TEMP_DIR / f"title_card_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.png"
    img.save(output_path)
    return output_path


def generate_video_from_image(image_path, audio_path, output_path, duration=None):
    """Generate MP4 from a still image + audio (for title cards with audio)."""
    # Get audio duration if not specified
    if duration is None:
        try:
            result = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", str(audio_path)],
                capture_output=True, text=True, timeout=10
            )
            duration = float(result.stdout.strip())
        except Exception:
            duration = 482.0

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", str(image_path),
        "-i", str(audio_path),
        "-c:v", "libx264", "-tune", "stillimage",
        "-c:a", "aac", "-b:a", "128k",
        "-pix_fmt", "yuv420p",
        "-shortest",
        "-t", str(duration),
        str(output_path)
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        return result.returncode == 0, result.stderr[:300] if result.returncode != 0 else ""
    except Exception as e:
        return False, str(e)


def generate_animated_background(output_path, duration_seconds, theme_name="dark_indigo"):
    """Generate an animated background using ffmpeg color cycling."""
    theme = THEMES.get(theme_name, THEMES["dark_indigo"])
    bg_hex = "0x{:02x}{:02x}{:02x}".format(*theme["bg_color"])
    accent_hex = "0x{:02x}{:02x}{:02x}".format(*theme["accent_color"])

    # Simple background: solid color with subtle hue cycling
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"color=c={bg_hex}:size=1280x720:duration={duration_seconds}:rate=24",
        "-vf", f"hue=h=10*sin(2*PI*t/{duration_seconds})",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-pix_fmt", "yuv420p",
        str(output_path)
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        return result.returncode == 0, result.stderr[:200] if result.returncode != 0 else ""
    except Exception as e:
        return False, str(e)


def get_audio_duration(audio_path):
    """Get duration of audio file in seconds."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(audio_path)],
            capture_output=True, text=True, timeout=10
        )
        return float(result.stdout.strip())
    except Exception:
        return 60.0


def generate_video_for_article(article_dir, theme="dark_indigo"):
    """Generate complete video for one article."""
    slug = article_dir.name
    audio_path = AUDIO_DIR / f"{slug}.mp3"
    meta_file = article_dir / "meta.json"

    if not audio_path.exists():
        print(f"  ✗ No audio for {slug} — run tts_service.py first")
        return False

    if not meta_file.exists():
        print(f"  ✗ No meta for {slug}")
        return False

    meta = json.loads(meta_file.read_text())
    duration = get_audio_duration(audio_path)
    print(f"  Audio duration: {duration:.1f}s")

    # Step 1: Render title card as PNG
    print(f"  [1/3] Title card...")
    title_png = render_title_card_png(
        meta["short_title"],
        f"AI Tools Hub · {meta['date_display']}",
        theme,
    )

    # Step 2: Convert PNG + audio into title clip (4s)
    title_clip = TEMP_DIR / f"{slug}_title.mp4"
    # Use 4 seconds for title card, use first 4s of audio
    audio_4s = TEMP_DIR / f"{slug}_title_4s.mp3"
    subprocess.run([
        "ffmpeg", "-y", "-i", str(audio_path),
        "-t", "4", "-c", "copy", str(audio_4s)
    ], capture_output=True, timeout=10)

    ok, err = generate_video_from_image(title_png, audio_4s, title_clip, duration=4)
    title_png.unlink(missing_ok=True)
    audio_4s.unlink(missing_ok=True)
    if not ok:
        print(f"  ✗ Title clip failed: {err}")
        return False

    # Step 3: Generate animated background for the main content (uses full audio minus title)
    print(f"  [2/3] Main video ({duration - 4:.1f}s)...")
    # Use audio starting from 4s for the main video
    audio_main = TEMP_DIR / f"{slug}_main.mp3"
    subprocess.run([
        "ffmpeg", "-y", "-ss", "4", "-i", str(audio_path),
        "-c", "copy", str(audio_main)
    ], capture_output=True, timeout=10)

    # Create main video: animated bg + remaining audio
    main_video = TEMP_DIR / f"{slug}_main.mp4"
    theme_bg = THEMES.get(theme, THEMES["dark_indigo"])
    bg_hex = "0x{:02x}{:02x}{:02x}".format(*theme_bg["bg_color"])
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"color=c={bg_hex}:size=1280x720:duration={duration-4}:rate=24",
        "-i", str(audio_main),
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        "-pix_fmt", "yuv420p",
        "-shortest",
        str(main_video)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    audio_main.unlink(missing_ok=True)
    if result.returncode != 0:
        print(f"  ✗ Main video failed: {result.stderr[:300]}")
        return False

    # Step 4: Concatenate title + main
    print(f"  [3/3] Combining...")
    final_video = VIDEO_DIR / f"{slug}.mp4"

    concat_list = TEMP_DIR / f"{slug}_list.txt"
    concat_list.write_text(f"file '{title_clip}'\nfile '{main_video}'\n")

    result = subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list),
        "-c", "copy", str(final_video)
    ], capture_output=True, text=True, timeout=60)

    # Cleanup
    title_clip.unlink(missing_ok=True)
    main_video.unlink(missing_ok=True)
    concat_list.unlink(missing_ok=True)

    if result.returncode != 0:
        print(f"  ✗ Concat failed: {result.stderr[:200]}")
        return False

    size_mb = final_video.stat().st_size / (1024 * 1024)
    final_duration = get_audio_duration(final_video)
    print(f"  ✓ Generated: {final_video.name} ({size_mb:.1f}MB, {final_duration:.0f}s)")
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--article", help="Article slug to generate video for")
    parser.add_argument("--theme", default="dark_indigo", choices=list(THEMES.keys()),
                        help="Visual theme")
    parser.add_argument("--all", action="store_true", help="Generate videos for all articles with audio")
    args = parser.parse_args()

    if not check_ffmpeg():
        print("ERROR: ffmpeg not installed")
        print("Install with: sudo apt install ffmpeg")
        return

    print("=" * 60)
    print(f"YouTube Companion Video Generator")
    print(f"Theme: {args.theme}")
    print("=" * 60)

    if args.article:
        article_dir = ARTICLES_DIR / args.article
        if not article_dir.exists():
            print(f"Article not found: {args.article}")
            return
        generate_video_for_article(article_dir, args.theme)
    elif args.all:
        for article_dir in sorted(ARTICLES_DIR.iterdir()):
            if not article_dir.is_dir():
                continue
            if not (article_dir / "meta.json").exists():
                continue
            audio = AUDIO_DIR / f"{article_dir.name}.mp3"
            if not audio.exists():
                print(f"\n⊘ Skipping {article_dir.name} (no audio)")
                continue
            print(f"\n→ {article_dir.name}")
            generate_video_for_article(article_dir, args.theme)
    else:
        print("Usage:")
        print("  python3 make_videos.py --article best-free-ai-tools-2026")
        print("  python3 make_videos.py --all")


if __name__ == "__main__":
    main()
