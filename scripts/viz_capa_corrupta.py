#!/usr/bin/env python3
"""Lamina de la capa de texto que existe, parece valida y esta corrupta."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image

from viz_common import (AMBER, CARD, FG, GREEN, H, MUTED, RED, W, canvas, card,
                        centered, fit, font, footer, text_block)

ERRORES = [
    ("Vierta 6. de Diciembre de i 749", "Viernes"),
    ("paííáron fusMageftades", "pasaron sus Majestades"),
    ("Igíefia de la Cafa Profefla", "Iglesia de la Casa Profesa"),
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache", default="out/cache/gazeta_1750_p1")
    parser.add_argument("--profile", default="out/profiles/gazeta_1750.jsonl")
    parser.add_argument("--out", default="out/figuras/capa_corrupta.png")
    args = parser.parse_args()

    data = json.loads(Path(f"{args.cache}.json").read_text(encoding="utf-8"))
    page = Image.open(f"{args.cache}.png")
    perfil = [json.loads(l) for l in
              Path(args.profile).read_text(encoding="utf-8").splitlines()]
    # la cifra se lee del perfil, no se escribe a mano: es la de esta pagina concreta
    chars_pagina = next(r["native_chars"] for r in perfil if r["page"] == data["page"])

    img, d = canvas()
    y = 58
    y += centered(d, y, "El documento con el texto", font(50, "bold"), FG)
    y += centered(d, y + 2, "más corrupto de mi corpus", font(50, "bold"), FG)
    y += centered(d, y + 2, "nunca disparó la alarma", font(50, "bold"), AMBER) + 18
    y += centered(d, y, "Gaceta de Madrid · 1750 · archivo histórico del BOE",
                  font(23), MUTED) + 26

    box_h = 430
    thumb = fit(page, 520, box_h)
    card(d, (72, y, 660, y + box_h + 24), fill=CARD)
    img.paste(thumb, (72 + (588 - thumb.width) // 2, y + 12))

    # la cifra que enganya al triaje
    card(d, (686, y, W - 72, y + box_h + 24), fill=CARD, outline=AMBER, width=3)
    d.text((716, y + 30), "caracteres en esta página", font=font(22), fill=MUTED)
    d.text((716, y + 68), f"{chars_pagina:,}".replace(",", "."),
           font=font(74, "bold"), fill=AMBER)
    d.line((716, y + 176, W - 106, y + 176), fill=(58, 66, 82), width=2)
    text_block(d, (716, y + 200),
               "El BOE ya le pasó OCR hace años.\n\n"
               "El triaje cuenta caracteres, ve la página llena "
               "y la da por buena.\n\n"
               "Ningún umbral dispara.",
               font(23), FG, width=25, leading=1.4)
    y += box_h + 24 + 38

    card(d, (72, y, W - 72, y + 366), fill=CARD, outline=RED, width=3)
    d.text((104, y + 24), "Lo que contiene de verdad", font=font(27, "bold"), fill=RED)
    yy = y + 74
    for malo, bueno in ERRORES:
        d.text((104, yy), malo, font=font(24, "mono"), fill=RED)
        d.text((104, yy + 36), f"   debería decir:  {bueno}", font=font(22), fill=GREEN)
        yy += 96
    y += 366 + 34

    card(d, (72, y, W - 72, y + 130), fill=(31, 41, 55))
    d.text((104, y + 26), "El triaje mide cantidad.", font=font(29, "bold"), fill=FG)
    d.text((104, y + 70), "El problema era de calidad.", font=font(29, "bold"), fill=AMBER)

    footer(d)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    img.save(args.out)
    print(f"{args.out}  {img.width}x{img.height}")


if __name__ == "__main__":
    main()
