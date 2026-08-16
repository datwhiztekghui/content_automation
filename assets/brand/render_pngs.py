"""Render AIInfoRoom brand PNGs from geometry (exact text, no AI wordmark garble)."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT = Path(__file__).resolve().parent
W = H = 1024


def draw_mark(img: Image.Image, cx: float, cy: float, scale: float = 1.0, glow: bool = True) -> None:
    d = ImageDraw.Draw(img, "RGBA")

    def p(x: float, y: float) -> tuple[float, float]:
        return (cx + (x - 256) * scale, cy + (y - 256) * scale)

    if glow:
        glow_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow_layer)
        r = int(200 * scale)
        for i in range(12, 0, -1):
            a = int(18 * (i / 12))
            rr = r * i / 12
            gd.ellipse(
                [cx - rr, cy + 20 * scale - rr, cx + rr, cy + 20 * scale + rr],
                fill=(125, 249, 255, a),
            )
        img.alpha_composite(glow_layer)

    cyan = (125, 249, 255, 230)
    cyan_edge = (92, 235, 255, 255)
    white = (232, 255, 255, 250)
    glass_fill_l = (46, 180, 210, 70)
    glass_fill_r = (46, 180, 210, 55)
    glass_top = (166, 251, 255, 90)
    floor = (20, 90, 100, 120)

    d.polygon([p(256, 360), p(150, 300), p(256, 240), p(362, 300)], fill=floor, outline=cyan_edge)
    d.polygon([p(150, 300), p(150, 170), p(256, 110), p(256, 240)], fill=glass_fill_l, outline=cyan)
    d.polygon([p(362, 300), p(362, 170), p(256, 110), p(256, 240)], fill=glass_fill_r, outline=cyan)
    d.polygon([p(256, 78), p(170, 128), p(256, 178), p(342, 128)], fill=glass_top, outline=(166, 251, 255, 240))

    beam = Image.new("RGBA", img.size, (0, 0, 0, 0))
    bd = ImageDraw.Draw(beam)
    y0 = p(251, 145)[1]
    y1 = p(261, 340)[1]
    bw = max(4.0, 10 * scale)
    bx = cx - bw / 2
    bd.rounded_rectangle([bx, y0, bx + bw, y1], radius=max(2, int(5 * scale)), fill=(255, 255, 255, 245))
    br = max(8.0, 18 * scale)
    bd.ellipse([cx - br, y1 - br * 0.3, cx + br, y1 + br * 1.2], fill=(125, 249, 255, 80))
    bd.ellipse([cx - br * 0.4, y1 - br * 0.15, cx + br * 0.4, y1 + br * 0.5], fill=(255, 255, 255, 230))
    beam = beam.filter(ImageFilter.GaussianBlur(radius=max(1, int(2 * scale))))
    img.alpha_composite(beam)
    d.rounded_rectangle([bx, y0, bx + bw, y1], radius=max(2, int(5 * scale)), fill=(255, 255, 255, 230))
    d.ellipse([cx - 6 * scale, y1 - 4 * scale, cx + 6 * scale, y1 + 8 * scale], fill=white)


def _wordmark(
    draw: ImageDraw.ImageDraw,
    origin: tuple[float, float],
    font: ImageFont.ImageFont,
    *,
    tracking: float = 0.0,
    ai_gap: float = 6.0,
) -> float:
    """Draw AIInfoRoom with readable capital I (not confused with lowercase L)."""
    x, y = origin
    # Per-glyph: A | I (extra gap) | Info | Room — AI stays cyan block
    parts: list[tuple[str, tuple[int, int, int, int], float]] = [
        ("A", (125, 249, 255, 255), tracking),
        ("I", (125, 249, 255, 255), ai_gap),  # serifed look via font + gap after A
        ("Info", (244, 251, 255, 255), tracking),
        ("Room", (155, 179, 188, 255), tracking),
    ]
    for text, color, extra in parts:
        draw.text((x, y), text, font=font, fill=color)
        bbox = draw.textbbox((x, y), text, font=font)
        # Draw top/bottom bars on capital I so it never reads as "l"
        if text == "I":
            left, top, right, bottom = bbox
            mid = (left + right) / 2
            bar_w = max(10.0, (right - left) * 2.2)
            bar_h = max(3.0, (bottom - top) * 0.08)
            draw.rectangle([mid - bar_w / 2, top, mid + bar_w / 2, top + bar_h], fill=color)
            draw.rectangle([mid - bar_w / 2, bottom - bar_h, mid + bar_w / 2, bottom], fill=color)
        x = bbox[2] + extra
    return x


def main() -> None:
    candidates = [
        Path(r"C:\Windows\Fonts\segoeuib.ttf"),
        Path(r"C:\Windows\Fonts\arialbd.ttf"),
        Path(r"C:\Windows\Fonts\arial.ttf"),
    ]
    font_path = next((c for c in candidates if c.exists()), None)

    av = Image.new("RGBA", (W, H), (5, 11, 16, 255))
    draw_mark(av, W // 2, H // 2 + 20, scale=1.55)
    av.save(OUT / "aiinforoom_avatar.png")

    mk = Image.new("RGBA", (W, H), (5, 11, 16, 255))
    draw_mark(mk, W // 2, H // 2 + 10, scale=1.55)
    mk.save(OUT / "aiinforoom_mark.png")

    lw, lh = 1600, 480
    lk = Image.new("RGBA", (lw, lh), (5, 11, 16, 255))
    draw_mark(lk, 220, lh // 2 + 10, scale=0.85)
    d = ImageDraw.Draw(lk)
    font = ImageFont.truetype(str(font_path), 96) if font_path else ImageFont.load_default()
    font_sm = ImageFont.truetype(str(font_path), 22) if font_path else ImageFont.load_default()
    _wordmark(d, (420, 175), font, tracking=-2.0, ai_gap=8.0)
    d.text((424, 290), "CLEAR AI & TECH THAT MATTERS", font=font_sm, fill=(90, 122, 134, 255))
    lk.save(OUT / "aiinforoom_lockup.png")

    bw, bh = 840, 192
    bdg = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
    d = ImageDraw.Draw(bdg, "RGBA")
    d.rounded_rectangle(
        [8, 16, bw - 8, bh - 16],
        radius=28,
        fill=(5, 11, 16, 200),
        outline=(46, 211, 232, 100),
        width=2,
    )
    draw_mark(bdg, 96, bh // 2 + 4, scale=0.32, glow=False)
    font_b = ImageFont.truetype(str(font_path), 64) if font_path else ImageFont.load_default()
    _wordmark(d, (175, 62), font_b, tracking=-1.0, ai_gap=6.0)
    bdg.save(OUT / "aiinforoom_badge.png")
    print("rendered:", sorted(p.name for p in OUT.glob("*.png")))


if __name__ == "__main__":
    main()
