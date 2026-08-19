#!/usr/bin/env python3
"""Imagen del post de OCR: lo que ve cada metodo sobre la misma pagina."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image

from viz_common import (BG, CARD, FG, GREEN, H, MUTED, RED, W, canvas, card,
                        centered, fit, font, footer, text_block)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache", default="out/cache/cs224n_l01_p15")
    parser.add_argument("--out", default="out/figuras/post_ocr.png")
    args = parser.parse_args()

    data = json.loads(Path(f"{args.cache}.json").read_text(encoding="utf-8"))
    page = Image.open(f"{args.cache}.png")

    img, d = canvas()

    y = 62
    y += centered(d, y, "Una diapositiva sobre ChatGPT", font(52, "bold"), FG)
    y += centered(d, y + 4, "que tu pipeline no sabe leer", font(52, "bold"), FG) + 14
    y += centered(d, y, "Stanford CS224n · Lecture 1 · diapositiva 15", font(24), MUTED) + 34

    # la pagina, encajada en su tarjeta
    box_h = 470
    thumb = fit(page, W - 160, box_h)
    card(d, (72, y, W - 72, y + box_h + 28), fill=CARD)
    img.paste(thumb, ((W - thumb.width) // 2, y + 14))
    y += box_h + 28 + 40

    # los dos resultados
    col_w = (W - 72 * 2 - 26) // 2
    panels = [
        ("pdfplumber", len(data["native_text"]), data["native_text"], RED, 72,
         "El resto de la pagina:\ninvisible para el pipeline."),
        ("pdfplumber + OCR", len(data["ocr_text_normalizado"]),
         data["ocr_text_normalizado"], GREEN, 72 + col_w + 26, None),
    ]
    panel_h = 424
    for name, count, body, color, x, nota in panels:
        card(d, (x, y, x + col_w, y + panel_h), fill=CARD, outline=color, width=3)
        d.text((x + 26, y + 20), name, font=font(27, "bold"), fill=color)
        numero = f"{count:,}".replace(",", ".")
        d.text((x + 26, y + 58), numero, font=font(88, "bold"), fill=color)
        d.text((x + 26, y + 158), "caracteres extraídos", font=font(21), fill=MUTED)
        text_block(d, (x + 26, y + 202), body.replace("\n", " "), font(16, "mono"),
                   FG if count > 100 else MUTED, width=40, leading=1.44, max_lines=9)
        if nota:
            d.line((x + 26, y + 258, x + col_w - 26, y + 258), fill=(58, 66, 82), width=2)
            text_block(d, (x + 26, y + 282), nota, font(23), MUTED, width=30, leading=1.4)
    y += panel_h + 36

    card(d, (72, y, W - 72, y + 116), fill=(31, 41, 55))
    d.text((100, y + 24), "Toda la página es una captura de pantalla.", font=font(27, "bold"), fill=FG)
    d.text((100, y + 64), "El texto existe. Simplemente no está en la capa de texto.",
           font=font(24), fill=MUTED)

    footer(d)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    img.save(args.out)
    print(f"{args.out}  {img.width}x{img.height}")


if __name__ == "__main__":
    main()
