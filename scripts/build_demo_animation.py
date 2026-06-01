from __future__ import annotations

import json
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
FRAME_DIR = ROOT / "demo_artifacts" / "rdl_vc_demo_frames"
OUT_DIR = ROOT / "demo_artifacts"
WEBP_OUT = OUT_DIR / "rdl_vc_demo.webp"
GIF_OUT = OUT_DIR / "rdl_vc_demo.gif"
COVER_OUT = OUT_DIR / "rdl_vc_demo_cover.png"
WIDTH = 1280
HEIGHT = 720
DURATION_MS = 170


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Helvetica Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Helvetica.ttf",
        "/Library/Fonts/Arial Bold.ttf" if bold else "/Library/Fonts/Arial.ttf",
    ]
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    return ImageFont.load_default()


TITLE_FONT = font(22, bold=True)
BODY_FONT = font(20)
SMALL_FONT = font(14)


def draw_caption(image: Image.Image, caption: str) -> Image.Image:
    frame = image.convert("RGB")
    overlay = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    bar_h = 104
    draw.rectangle((0, HEIGHT - bar_h, WIDTH, HEIGHT), fill=(5, 8, 12, 214))
    draw.rectangle((0, HEIGHT - bar_h, WIDTH, HEIGHT - bar_h + 2), fill=(71, 215, 255, 190))
    draw.text((28, HEIGHT - 84), "RDL Evidence Map", fill=(237, 245, 248, 255), font=TITLE_FONT)
    lines = textwrap.wrap(caption, width=92)
    for idx, line in enumerate(lines[:2]):
        draw.text((28, HEIGHT - 50 + idx * 24), line, fill=(205, 218, 229, 255), font=BODY_FONT)
    draw.text((WIDTH - 248, HEIGHT - 33), "observed | derived | modeled", fill=(169, 183, 196, 255), font=SMALL_FONT)
    return Image.alpha_composite(frame.convert("RGBA"), overlay).convert("RGB")


def main() -> None:
    captions_path = FRAME_DIR / "captions.json"
    captions = json.loads(captions_path.read_text(encoding="utf-8"))
    frames: list[Image.Image] = []
    for item in captions:
        image = Image.open(item["file"]).convert("RGB")
        if image.size != (WIDTH, HEIGHT):
            image = image.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
        frames.append(draw_caption(image, item["caption"]))

    if not frames:
        raise SystemExit("No frames found.")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    frames[0].save(COVER_OUT)
    frames[0].save(
        WEBP_OUT,
        save_all=True,
        append_images=frames[1:],
        duration=DURATION_MS,
        loop=0,
        quality=82,
        method=6,
    )
    paletted = [frame.convert("P", palette=Image.Palette.ADAPTIVE, colors=128) for frame in frames]
    paletted[0].save(
        GIF_OUT,
        save_all=True,
        append_images=paletted[1:],
        duration=DURATION_MS,
        loop=0,
        optimize=True,
    )
    print(json.dumps({
        "frames": len(frames),
        "webp": str(WEBP_OUT),
        "gif": str(GIF_OUT),
        "cover": str(COVER_OUT),
        "webp_bytes": WEBP_OUT.stat().st_size,
        "gif_bytes": GIF_OUT.stat().st_size,
    }, indent=2))


if __name__ == "__main__":
    main()
