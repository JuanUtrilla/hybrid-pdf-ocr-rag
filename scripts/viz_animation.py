#!/usr/bin/env python3
"""Animacion del pipeline completo, de la pagina a la respuesta del RAG.

Seis actos, pensados para verse sin sonido y en bucle en un feed:

  1. La pagina, y lo poco que da la capa de texto.
  2. Deteccion: aparecen las cajas que encuentra el detector.
  3. Reconocimiento: cada caja se convierte en texto.
  4. Normalizacion: se reconstruyen los espacios que pierde el reconocedor.
  5. Chunking: el texto se agrupa en fragmentos con su procedencia.
  6. Recuperacion: una pregunta encuentra el chunk que solo existe por el OCR.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw

from viz_common import (AMBER, BG, BLUE, CARD, FG, GREEN, H, MUTED, RED, W,
                        canvas, card, centered, fit, font, text_block)

FPS = 20


def ease(t: float) -> float:
    return 1 - (1 - t) ** 3


def header(d, titulo: str, paso: str, color):
    d.text((60, 46), paso, font=font(24, "bold"), fill=color)
    d.text((60, 84), titulo, font=font(42, "bold"), fill=FG)


def progress(d, idx: int, total: int = 6):
    x0, y0 = 60, H - 46
    ancho = (W - 120) // total
    for i in range(total):
        color = FG if i <= idx else (48, 55, 68)
        d.rounded_rectangle((x0 + i * ancho, y0, x0 + (i + 1) * ancho - 10, y0 + 7),
                            radius=4, fill=color)


def page_panel(img, d, page, top, alto):
    card(d, (60, top, W - 60, top + alto + 24), fill=CARD)
    thumb = fit(page, W - 140, alto)
    pos = ((W - thumb.width) // 2, top + 12)
    img.paste(thumb, pos)
    return pos, thumb


def scale_box(box, pos, thumb, size):
    sx, sy = thumb.width / size[0], thumb.height / size[1]
    return [(pos[0] + x * sx, pos[1] + y * sy) for x, y in box]


def frames_acto1(page, data):
    out = []
    for i in range(int(FPS * 2.2)):
        img, d = canvas()
        header(d, "La página", "PASO 1 / 6", MUTED)
        pos, thumb = page_panel(img, d, page, 150, 700)
        card(d, (60, 900, W - 60, 1080), fill=CARD, outline=RED, width=3)
        d.text((90, 926), "pdfplumber extrae", font=font(25), fill=MUTED)
        d.text((90, 968), f"{len(data['native_text'])} caracteres", font=font(64, "bold"), fill=RED)
        if i > FPS * 0.8:
            d.text((90, 1120), "El resto del contenido está dentro de imágenes.",
                   font=font(28, "bold"), fill=FG)
        progress(d, 0)
        out.append(img)
    return out


def frames_acto2(page, data):
    out, boxes = [], data["boxes"]
    total = int(FPS * 2.8)
    for i in range(total):
        img, d = canvas()
        header(d, "Detección: dónde hay texto", "PASO 2 / 6", BLUE)
        pos, thumb = page_panel(img, d, page, 150, 700)
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        visibles = min(len(boxes), int(ease(min(1.0, i / (total * 0.75))) * len(boxes)))
        for b in boxes[:visibles]:
            pts = scale_box(b["box"], pos, thumb, data["size"])
            od.polygon(pts, fill=(96, 165, 250, 46), outline=(96, 165, 250, 235))
        img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
        d = ImageDraw.Draw(img)
        card(d, (60, 900, W - 60, 1080), fill=CARD, outline=BLUE, width=3)
        d.text((90, 926), "cajas detectadas", font=font(25), fill=MUTED)
        d.text((90, 968), str(visibles), font=font(64, "bold"), fill=BLUE)
        d.text((90, 1120), "El detector no lee: solo marca dónde hay algo.",
               font=font(28, "bold"), fill=FG)
        progress(d, 1)
        out.append(img)
    return out


def frames_acto3(page, data):
    out = []
    boxes = sorted(data["boxes"], key=lambda b: (min(p[1] for p in b["box"])))
    total = int(FPS * 3.4)
    for i in range(total):
        img, d = canvas()
        header(d, "Reconocimiento: qué pone", "PASO 3 / 6", GREEN)
        pos, thumb = page_panel(img, d, page, 150, 470)
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        n = min(len(boxes), int(ease(min(1.0, i / (total * 0.8))) * len(boxes)))
        for b in boxes[:n]:
            od.polygon(scale_box(b["box"], pos, thumb, data["size"]),
                       fill=(74, 222, 128, 40), outline=(74, 222, 128, 210))
        img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
        d = ImageDraw.Draw(img)
        card(d, (60, 690, W - 60, 1180), fill=CARD, outline=GREEN, width=3)
        d.text((90, 712), "texto reconocido", font=font(25), fill=MUTED)
        cuerpo = " ".join(b["text"] for b in boxes[:n])
        text_block(d, (90, 756), cuerpo, font(19, "mono"), FG, width=62,
                   leading=1.45, max_lines=13)
        d.text((90, 1216), f"{len(cuerpo)} caracteres que no estaban en la capa de texto.",
               font=font(27, "bold"), fill=GREEN)
        progress(d, 2)
        out.append(img)
    return out


def frames_normalizacion(data):
    """El reconocedor pierde los espacios en tipografia apretada. Se recuperan."""
    out = []
    crudo = data["ocr_text"].replace("\n", " ")
    limpio = data["ocr_text_normalizado"].replace("\n", " ")
    total = int(FPS * 3.0)
    for i in range(total):
        img, d = canvas()
        header(d, "El OCR también estropea", "PASO 4 / 6", AMBER)
        card(d, (60, 190, W - 60, 560), fill=CARD, outline=RED, width=3)
        d.text((90, 212), "tal y como sale del reconocedor", font=font(24), fill=RED)
        text_block(d, (90, 256), crudo, font(19, "mono"), FG, width=58,
                   leading=1.45, max_lines=8)
        if i > FPS * 1.0:
            card(d, (60, 620, W - 60, 990), fill=CARD, outline=GREEN, width=3)
            d.text((90, 642), "tras reconstruir los espacios", font=font(24), fill=GREEN)
            text_block(d, (90, 686), limpio, font(19, "mono"), FG, width=58,
                       leading=1.45, max_lines=8)
        if i > FPS * 1.9:
            d.text((60, 1060), "Un embedding de 'Ihopethisemailfindsyouwell'",
                   font=font(28, "bold"), fill=FG)
            d.text((60, 1102), "no se parece a nada.", font=font(28, "bold"), fill=AMBER)
            d.text((60, 1164), "El vocabulario sale del propio corpus: las páginas",
                   font=font(24), fill=MUTED)
            d.text((60, 1200), "de texto nativo ya están bien segmentadas.",
                   font=font(24), fill=MUTED)
        progress(d, 3)
        out.append(img)
    return out


def frames_acto4(chunks):
    out = []
    total = int(FPS * 2.8)
    for i in range(total):
        img, d = canvas()
        header(d, "Chunking con procedencia", "PASO 5 / 6", AMBER)
        n = min(len(chunks), 1 + int(ease(min(1.0, i / (total * 0.7))) * (len(chunks) - 1)))
        y = 180
        for c in chunks[:n]:
            alto = 176
            color = GREEN if c["method"] == "OCR" else MUTED
            card(d, (60, y, W - 60, y + alto), fill=CARD, outline=color, width=2)
            d.text((88, y + 18), f"{c['doc']}  ·  página {c['page']}",
                   font=font(21, "bold"), fill=MUTED)
            etiqueta = f"[{c['method']}]"
            d.text((W - 88 - d.textlength(etiqueta, font=font(21, "bold")), y + 18),
                   etiqueta, font=font(21, "bold"), fill=color)
            text_block(d, (88, y + 56), c["text"], font(18, "mono"), FG, width=64,
                       leading=1.4, max_lines=4)
            y += alto + 18
        d.text((60, H - 130), "Cada fragmento recuerda de dónde salió.",
               font=font(28, "bold"), fill=FG)
        progress(d, 4)
        out.append(img)
    return out


def frames_acto5(pregunta, acierto):
    out = []
    total = int(FPS * 4.0)
    for i in range(total):
        img, d = canvas()
        header(d, "Y entonces el RAG responde", "PASO 6 / 6", GREEN)
        card(d, (60, 180, W - 60, 320), fill=(31, 41, 55), outline=BLUE, width=3)
        d.text((88, 202), "PREGUNTA", font=font(21, "bold"), fill=BLUE)
        text_block(d, (88, 238), pregunta, font(25, "bold"), FG, width=52, leading=1.3)

        if i > FPS * 0.7:
            card(d, (60, 360, W - 60, 560), fill=CARD, outline=RED, width=3)
            d.text((88, 384), "SIN OCR", font=font(23, "bold"), fill=RED)
            d.text((88, 424), "recall@5 = 0,00", font=font(52, "bold"), fill=RED)
            d.text((88, 496), "0 de 8 preguntas encuentran su página",
                   font=font(23), fill=MUTED)
        if i > FPS * 1.6:
            card(d, (60, 600, W - 60, 800), fill=CARD, outline=GREEN, width=3)
            d.text((88, 624), "CON OCR", font=font(23, "bold"), fill=GREEN)
            d.text((88, 664), "recall@5 = 0,88", font=font(52, "bold"), fill=GREEN)
            d.text((88, 736), "7 de 8, con solo un 7% más de chunks",
                   font=font(23), fill=MUTED)
        if i > FPS * 2.5:
            card(d, (60, 850, W - 60, 1030), fill=(31, 41, 55))
            d.text((88, 876), "El fragmento que responde", font=font(24), fill=MUTED)
            d.text((88, 918), acierto, font=font(30, "bold"), fill=GREEN)
            d.text((88, 968), "solo existe porque pasó por OCR.",
                   font=font(26), fill=FG)
        if i > FPS * 3.1:
            centered(d, 1120, "Perfila tu corpus antes de decidir.", font(34, "bold"), FG)
            centered(d, 1180, "github.com/JuanUtrilla/hybrid-pdf-ocr-rag",
                     font(24), MUTED)
        progress(d, 5)
        out.append(img)
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache", default="out/cache/cs224n_l01_p15")
    parser.add_argument("--out", default="out/figuras/pipeline")
    args = parser.parse_args()

    data = json.loads(Path(f"{args.cache}.json").read_text(encoding="utf-8"))
    page = Image.open(f"{args.cache}.png")

    chunks = [
        {"doc": "cs224n_l01", "page": 14, "method": "PLUMBER",
         "text": "Large language models are the current frontier of NLP research and deployment."},
        {"doc": "cs224n_l01", "page": 15, "method": "OCR",
         "text": "ChatGPT, GPT-4, and more. Hey please draft a polite mail to explain my boss "
                 "Jeremy that I would not be able to come to office for next 2 days."},
        {"doc": "cs224n_l01", "page": 16, "method": "PLUMBER",
         "text": "We will now look at how word vectors are learned from co-occurrence counts."},
    ]

    acto1 = frames_acto1(page, data)
    acto2 = frames_acto2(page, data)
    acto3 = frames_acto3(page, data)
    acto_norm = frames_normalizacion(data)
    acto4 = frames_acto4(chunks)
    acto5 = frames_acto5("What does the ChatGPT slide show about drafting an email?",
                         "cs224n_l01 · página 15 · [OCR]")
    frames = acto1 + acto2 + acto3 + acto_norm + acto4 + acto5

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    gif = out.with_suffix(".gif")
    small = [f.resize((W // 2, H // 2), Image.LANCZOS).quantize(colors=128) for f in frames]
    small[0].save(gif, save_all=True, append_images=small[1:],
                  duration=int(1000 / FPS), loop=0, optimize=True)
    print(f"{gif}  {len(frames)} frames  {gif.stat().st_size // 1024} KB")

    # MP4 via ffmpeg: LinkedIn reproduce video en bucle y con mejor calidad que un GIF
    import shutil
    import subprocess
    import tempfile

    mp4 = out.with_suffix(".mp4")
    with tempfile.TemporaryDirectory() as tmp:
        for i, f in enumerate(frames):
            f.save(Path(tmp) / f"{i:05d}.png")
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS),
             "-i", str(Path(tmp) / "%05d.png"), "-c:v", "libx264",
             "-pix_fmt", "yuv420p", "-crf", "20", "-movflags", "+faststart",
             str(mp4)],
            check=True)
    print(f"{mp4}  {mp4.stat().st_size // 1024} KB")

    # fotogramas sueltos, utiles como carrusel si se prefiere a un video
    # un fotograma tardio de cada acto, cuando la animacion ya ha llegado a su estado final
    cortes = [len(a) for a in (acto1, acto2, acto3, acto_norm, acto4, acto5)]
    inicios, acc = [], 0
    for c in cortes:
        inicios.append(acc); acc += c
    nombres = ["01_pagina", "02_deteccion", "03_reconocimiento",
               "04_normalizacion", "05_chunks", "06_rag"]
    claves = {n: inicios[i] + int(cortes[i] * 0.92) for i, n in enumerate(nombres)}
    for nombre, idx in claves.items():
        if idx < len(frames):
            frames[idx].save(out.parent / f"carrusel_{nombre}.png")
    print(f"carrusel: {len(claves)} laminas en {out.parent}")


if __name__ == "__main__":
    main()
