#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import shutil
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont


REPO_ROOT = Path.cwd()
ARTIFACT_DIR = REPO_ROOT / "demo_artifacts" / "v3_product_demo"
STATES_PATH = ARTIFACT_DIR / "states.json"
FRAMES_DIR = Path("/private/tmp/v3_product_demo_frames")
WIDTH = 1920
HEIGHT = 1080
FPS = 24


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/Library/Fonts/Arial.ttf",
    ]
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    return ImageFont.load_default()


FONT_TITLE = font(40, True)
FONT_BODY = font(27)
FONT_SMALL = font(20, True)
FONT_PILL = font(18, True)


def ease(value: float) -> float:
    return value * value * (3.0 - 2.0 * value)


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font_obj: ImageFont.ImageFont, max_width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        trial = f"{current} {word}".strip()
        if draw.textbbox((0, 0), trial, font=font_obj)[2] <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def crop_motion(image: Image.Image, state: dict, t: float) -> tuple[Image.Image, tuple[float, float, float]]:
    focus = state.get("focus", [WIDTH / 2, HEIGHT / 2])
    zoom_start, zoom_end = state.get("zoom", [1.0, 1.03])
    z = zoom_start + (zoom_end - zoom_start) * ease(t)
    crop_w = WIDTH / z
    crop_h = HEIGHT / z
    cx = float(focus[0])
    cy = float(focus[1])
    left = max(0.0, min(WIDTH - crop_w, cx - crop_w / 2))
    top = max(0.0, min(HEIGHT - crop_h, cy - crop_h / 2))
    cropped = image.crop((left, top, left + crop_w, top + crop_h))
    return cropped.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS), (left, top, z)


def transformed_box(box: list[int], transform: tuple[float, float, float]) -> tuple[int, int, int, int]:
    left, top, z = transform
    x1, y1, x2, y2 = box
    return (
        int((x1 - left) * z),
        int((y1 - top) * z),
        int((x2 - left) * z),
        int((y2 - top) * z),
    )


def draw_caption(frame: Image.Image, state: dict, state_index: int, state_count: int, progress: float) -> Image.Image:
    overlay = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    panel = (56, 792, 1035, 1015)
    draw.rounded_rectangle(panel, radius=22, fill=(8, 13, 20, 198), outline=(255, 255, 255, 44), width=1)
    draw.rounded_rectangle((80, 817, 190, 848), radius=15, fill=(0, 145, 190, 232))
    draw.text((108, 823), f"{state_index + 1:02d}/{state_count:02d}", fill=(255, 255, 255), font=FONT_PILL, anchor="mm")
    draw.text((80, 868), state["title"], fill=(255, 255, 255), font=FONT_TITLE)
    lines = wrap_text(draw, state["body"], FONT_BODY, 875)
    for i, line in enumerate(lines[:3]):
        draw.text((80, 925 + i * 34), line, fill=(219, 237, 244), font=FONT_BODY)
    draw.rounded_rectangle((0, HEIGHT - 7, int(WIDTH * progress), HEIGHT), radius=0, fill=(0, 154, 205, 230))
    return Image.alpha_composite(frame.convert("RGBA"), overlay)


def draw_spotlight(frame: Image.Image, state: dict, transform: tuple[float, float, float], t: float) -> Image.Image:
    box = state.get("spotlight")
    if not box or t > 0.44:
        return frame
    overlay = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    x1, y1, x2, y2 = transformed_box(box, transform)
    margin = 10 + int(6 * math.sin(t * math.pi * 10) ** 2)
    rect = (x1 - margin, y1 - margin, x2 + margin, y2 + margin)
    alpha = int(210 * (1.0 - t / 0.44))
    draw.rounded_rectangle(rect, radius=14, outline=(0, 190, 235, alpha), width=5)
    draw.rounded_rectangle(rect, radius=14, fill=(0, 190, 235, int(alpha * 0.08)))
    return Image.alpha_composite(frame, overlay)


def main() -> None:
    if not STATES_PATH.exists():
        raise SystemExit(f"Missing {STATES_PATH}. Run capture_v3_demo_states.mjs first.")

    with STATES_PATH.open("r", encoding="utf-8") as handle:
        spec = json.load(handle)

    states = spec["states"]
    total_frames = int(round(sum(state["duration"] for state in states) * FPS))
    shutil.rmtree(FRAMES_DIR, ignore_errors=True)
    FRAMES_DIR.mkdir(parents=True, exist_ok=True)

    source_images = [
        Image.open(ARTIFACT_DIR / state["image"]).convert("RGB").resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
        for state in states
    ]

    frame_index = 0
    fade_frames = int(0.55 * FPS)
    for state_index, (state, source) in enumerate(zip(states, source_images)):
        segment_frames = int(round(state["duration"] * FPS))
        previous_source = source_images[state_index - 1] if state_index > 0 else None
        previous_state = states[state_index - 1] if state_index > 0 else None
        for i in range(segment_frames):
            local_t = i / max(1, segment_frames - 1)
            frame, transform = crop_motion(source, state, local_t)
            frame = frame.convert("RGBA")
            if previous_source is not None and previous_state is not None and i < fade_frames:
                prev_frame, _ = crop_motion(previous_source, previous_state, 1.0)
                alpha = ease(i / fade_frames)
                frame = Image.blend(prev_frame.convert("RGBA"), frame, alpha)
            frame = draw_spotlight(frame, state, transform, local_t)
            frame = draw_caption(frame, state, state_index, len(states), frame_index / max(1, total_frames - 1))
            frame = frame.convert("RGB")
            output = FRAMES_DIR / f"frame_{frame_index:05d}.jpg"
            frame.save(output, "JPEG", quality=92, optimize=True, progressive=False)
            frame_index += 1

    poster = Image.open(FRAMES_DIR / "frame_00000.jpg")
    poster.save(ARTIFACT_DIR / "v3_epistemic_product_demo_poster.jpg", "JPEG", quality=94)
    print(f"rendered {frame_index} frames to {FRAMES_DIR}")
    print(f"poster {ARTIFACT_DIR / 'v3_epistemic_product_demo_poster.jpg'}")


if __name__ == "__main__":
    main()
