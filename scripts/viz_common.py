#!/usr/bin/env python3
"""Paleta, tipografia y primitivas comunes de las visualizaciones.

Formato pensado para el feed de LinkedIn: vertical 4:5, fondo oscuro para
destacar sobre el fondo blanco del feed, y cuerpos de texto grandes porque
la mayoria lo vera en un movil.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1200, 1500                      # 4:5, el formato que mas espacio ocupa en el feed

BG = (14, 17, 23)
CARD = (24, 28, 37)
CARD_ALT = (30, 35, 46)
FG = (232, 237, 243)
MUTED = (139, 148, 158)
RED = (248, 113, 113)
GREEN = (74, 222, 128)
BLUE = (96, 165, 250)
AMBER = (251, 191, 36)

FONTS = Path("/usr/share/fonts/truetype/dejavu")


def font(size: int, weight: str = "regular") -> ImageFont.FreeTypeFont:
    name = {"regular": "DejaVuSans.ttf", "bold": "DejaVuSans-Bold.ttf",
            "light": "DejaVuSans-ExtraLight.ttf", "mono": "DejaVuSansMono.ttf",
            "mono-bold": "DejaVuSansMono-Bold.ttf"}[weight]
    return ImageFont.truetype(str(FONTS / name), size)


def canvas(w: int = W, h: int = H, color=BG) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", (w, h), color)
    return img, ImageDraw.Draw(img)


def card(draw: ImageDraw.ImageDraw, box, fill=CARD, outline=None, radius: int = 18, width: int = 3):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def text_block(draw, xy, body: str, fnt, fill, width: int, leading: float = 1.35,
               max_lines: int | None = None) -> int:
    """Escribe texto ajustado y devuelve la altura ocupada."""
    lines: list[str] = []
    for raw in body.splitlines():
        lines += textwrap.wrap(raw, width=width) or [""]
    if max_lines and len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1][: max(0, width - 3)] + "..."
    x, y = xy
    step = int(fnt.size * leading)
    for line in lines:
        draw.text((x, y), line, font=fnt, fill=fill)
        y += step
    return y - xy[1]


def centered(draw, y: int, body: str, fnt, fill, w: int = W) -> int:
    width = draw.textlength(body, font=fnt)
    draw.text(((w - width) / 2, y), body, font=fnt, fill=fill)
    return int(fnt.size * 1.3)


def fit(img: Image.Image, box_w: int, box_h: int) -> Image.Image:
    scale = min(box_w / img.width, box_h / img.height)
    return img.resize((max(1, int(img.width * scale)), max(1, int(img.height * scale))),
                      Image.LANCZOS)


def footer(draw, handle: str = "github.com/JuanUtrilla/hybrid-pdf-ocr-rag"):
    f = font(21)
    draw.text((60, H - 58), handle, font=f, fill=MUTED)
