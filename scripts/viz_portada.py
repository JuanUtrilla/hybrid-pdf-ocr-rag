#!/usr/bin/env python3
"""Portada de la animacion: la pagina, sus cajas y el contraste principal.

El primer fotograma de la animacion no resume nada por si solo. Esta lamina
si, y sigue siendo legible muy reducida.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw

from viz_common import (BLUE, CARD, FG, GREEN, H, MUTED, RED, W, canvas, card,
                        centered, fit, font, footer)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache", default="out/cache/cs224n_l01_p15")
    parser.add_argument("--out", default="out/figuras/portada.png")
    args = parser.parse_args()

    data = json.loads(Path(f"{args.cache}.json").read_text(encoding="utf-8"))
    page = Image.open(f"{args.cache}.png")

    img, d = canvas()
    y = 118
    y += centered(d, y, "La misma página.", font(56, "bold"), FG)
    y += centered(d, y + 6, "Dos lecturas distintas.", font(56, "bold"), FG) + 40

    box_h = 560
    thumb = fit(page, W - 150, box_h)
    card(d, (66, y, W - 66, y + box_h + 26), fill=CARD)
    pos = ((W - thumb.width) // 2, y + 13)
    img.paste(thumb, pos)

    # las cajas del detector, que anticipan de que va la animacion
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    sx, sy = thumb.width / data["size"][0], thumb.height / data["size"][1]
    for b in data["boxes"]:
        od.polygon([(pos[0] + x * sx, pos[1] + yy * sy) for x, yy in b["box"]],
                   fill=(96, 165, 250, 44), outline=(96, 165, 250, 225))
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    d = ImageDraw.Draw(img)
    y += box_h + 26 + 46

    # el contraste, en el tamano mas grande que cabe
    izq, der = 66, W // 2 + 16
    ancho = W // 2 - 82
    for x, etiqueta, valor, color in (
        (izq, "pdfplumber", str(len(data["native_text"])), RED),
        (der, "con OCR", f"{len(data['ocr_text_normalizado']):,}".replace(",", "."), GREEN),
    ):
        card(d, (x, y, x + ancho, y + 250), fill=CARD, outline=color, width=4)
        w = d.textlength(etiqueta, font=font(30, "bold"))
        d.text((x + (ancho - w) / 2, y + 26), etiqueta, font=font(30, "bold"), fill=color)
        f = font(126, "bold")
        w = d.textlength(valor, font=f)
        d.text((x + (ancho - w) / 2, y + 74), valor, font=f, fill=color)
    # la flecha entre los dos bloques
    d.text((W // 2 - 18, y + 96), "→", font=font(64, "bold"), fill=MUTED)
    y += 250 + 34

    y += centered(d, y, "caracteres extraídos de una diapositiva de clase", font(27), MUTED) + 34
    centered(d, y, "Stanford CS224n · Lecture 1 · diapositiva 15", font(23), (110, 120, 134))

    footer(d)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    img.save(args.out)
    print(f"{args.out}  {img.width}x{img.height}  {Path(args.out).stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
