from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parent


def hex_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))


def rounded_mask(size: int, radius: int) -> Image.Image:
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0, size - 1, size - 1), radius=radius, fill=255)
    return mask


def gradient_background(size: int) -> Image.Image:
    top = hex_rgb("#151518")
    bottom = hex_rgb("#0c0c0d")
    center = (size * 0.56, size * 0.43)
    max_dist = math.hypot(size, size) * 0.72
    img = Image.new("RGB", (size, size))
    px = img.load()
    for y in range(size):
        vertical = y / (size - 1)
        for x in range(size):
            radial = 1 - min(math.hypot(x - center[0], y - center[1]) / max_dist, 1)
            t = max(0, min(1, vertical * 0.62 + (1 - radial) * 0.38))
            color = tuple(int(top[i] * (1 - t) + bottom[i] * t) for i in range(3))
            px[x, y] = color
    return img


def draw_polyline(layer: Image.Image, points: list[tuple[float, float]], width: int, fill: tuple[int, int, int, int]) -> None:
    draw = ImageDraw.Draw(layer)
    scaled = [(int(x), int(y)) for x, y in points]
    draw.line(scaled, fill=fill, width=width, joint="curve")
    r = width // 2
    for x, y in scaled:
        draw.ellipse((x - r, y - r, x + r, y + r), fill=fill)


def render_icon(size: int) -> Image.Image:
    scale = size / 1024
    radius = int(210 * scale)
    mask = rounded_mask(size, radius)

    bg = gradient_background(size).convert("RGBA")
    bg.putalpha(mask)

    glow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    strokes = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    nodes = Image.new("RGBA", (size, size), (0, 0, 0, 0))

    blue = hex_rgb("#4d8dff")
    cyan = (210, 248, 255)
    focus = (int(642 * scale), int(504 * scale))

    paths = [
        [(260 * scale, 270 * scale), (398 * scale, 292 * scale), (520 * scale, 390 * scale), focus],
        [(210 * scale, 466 * scale), (370 * scale, 462 * scale), (518 * scale, 488 * scale), focus],
        [(268 * scale, 718 * scale), (410 * scale, 660 * scale), (532 * scale, 570 * scale), focus],
    ]

    for width_mul, alpha, blur in ((64, 76, 22), (38, 128, 9)):
        for path in paths:
            draw_polyline(glow, path, int(width_mul * scale), (*blue, alpha))
        glow = glow.filter(ImageFilter.GaussianBlur(int(blur * scale)))

    for path in paths:
        draw_polyline(strokes, path, int(30 * scale), (*blue, 235))
        draw_polyline(strokes, path, int(11 * scale), (180, 224, 255, 245))

    node_draw = ImageDraw.Draw(nodes)
    for x, y in [(260, 270), (210, 466), (268, 718), (398, 292), (370, 462), (410, 660)]:
        cx, cy = int(x * scale), int(y * scale)
        outer = int(32 * scale)
        inner = int(14 * scale)
        node_draw.ellipse((cx - outer, cy - outer, cx + outer, cy + outer), fill=(*blue, 46))
        node_draw.ellipse((cx - inner, cy - inner, cx + inner, cy + inner), fill=(*blue, 245))

    focus_layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    focus_draw = ImageDraw.Draw(focus_layer)
    fx, fy = focus
    for r, alpha in [(122, 58), (74, 112), (38, 220)]:
        rr = int(r * scale)
        focus_draw.ellipse((fx - rr, fy - rr, fx + rr, fy + rr), fill=(77, 205, 255, alpha))
    focus_layer = focus_layer.filter(ImageFilter.GaussianBlur(int(12 * scale)))
    focus_draw = ImageDraw.Draw(focus_layer)
    rr = int(25 * scale)
    focus_draw.ellipse((fx - rr, fy - rr, fx + rr, fy + rr), fill=(*cyan, 255))
    focus_draw.line((fx - int(76 * scale), fy, fx + int(76 * scale), fy), fill=(230, 252, 255, 220), width=max(1, int(6 * scale)))
    focus_draw.line((fx, fy - int(76 * scale), fx, fy + int(76 * scale)), fill=(230, 252, 255, 220), width=max(1, int(6 * scale)))

    edge = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    edge_draw = ImageDraw.Draw(edge)
    inset = int(22 * scale)
    edge_draw.rounded_rectangle(
        (inset, inset, size - inset - 1, size - inset - 1),
        radius=radius - inset,
        outline=(255, 255, 255, 20),
        width=max(1, int(3 * scale)),
    )

    out = Image.alpha_composite(bg, glow)
    out = Image.alpha_composite(out, strokes)
    out = Image.alpha_composite(out, nodes)
    out = Image.alpha_composite(out, focus_layer)
    out = Image.alpha_composite(out, edge)
    out.putalpha(mask)
    return out


def main() -> None:
    large = render_icon(1024)
    large.save(ROOT / "fusefable_icon.png")
    large.resize((256, 256), Image.Resampling.LANCZOS).save(ROOT / "fusefable_icon_256.png")


if __name__ == "__main__":
    main()
