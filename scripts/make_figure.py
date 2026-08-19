#!/usr/bin/env python3
"""Genera la figura antes/despues para una pagina concreta del corpus."""

from __future__ import annotations

import argparse
import sys
import textwrap
from pathlib import Path

import cv2
import matplotlib
import numpy as np
import pdfplumber
import pypdfium2 as pdfium

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hybrid_pdf_extract import result_to_text  # noqa: E402
from rapidocr_onnxruntime import RapidOCR  # noqa: E402


def panel(ax, title, body, color, limit):
    ax.set_title(f"{title} ({len(body)} car.)", fontsize=12, fontweight="bold",
                 color=color, loc="left", pad=8)
    ax.axis("off")
    for spine in ("left",):
        ax.spines[spine].set_visible(False)
    shown = body[:limit] + ("\n[...]" if len(body) > limit else "")
    wrapped = "\n".join(textwrap.fill(l, 52) for l in shown.splitlines() if l.strip())
    ax.text(0.01, 0.99, wrapped or "(nada)", va="top", ha="left", fontsize=7.4,
            family="monospace", transform=ax.transAxes,
            bbox=dict(boxstyle="round,pad=0.6", facecolor="#fafafa", edgecolor=color, lw=1.6))


def main() -> None:
    parser = argparse.ArgumentParser(description="Figura antes/despues de OCR")
    parser.add_argument("--pdf", required=True)
    parser.add_argument("--page", type=int, required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--limit", type=int, default=1500)
    parser.add_argument("--caption", default="")
    args = parser.parse_args()

    with pdfplumber.open(args.pdf) as pdf:
        native = (pdf.pages[args.page - 1].extract_text() or "").strip()

    doc = pdfium.PdfDocument(args.pdf)
    render = np.array(doc[args.page - 1].render(scale=200 / 72).to_pil().convert("RGB"))
    text = result_to_text(RapidOCR()(cv2.cvtColor(render, cv2.COLOR_RGB2BGR))[0])

    fig, axes = plt.subplots(1, 3, figsize=(15, 5.6),
                             gridspec_kw={"width_ratios": [1.25, 1, 1], "wspace": 0.12})
    axes[0].imshow(render)
    axes[0].axis("off")
    axes[0].set_title("La pagina", fontsize=13, fontweight="bold", loc="left", pad=8)
    panel(axes[1], "pdfplumber", native, "#b3261e", args.limit)
    panel(axes[2], "OCR", text, "#1b5e20", args.limit)

    if args.caption:
        fig.suptitle(args.caption, fontsize=14, fontweight="bold", y=0.98)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.out, dpi=150, bbox_inches="tight")
    print(f"{args.out}  |  pdfplumber={len(native)} car  ocr={len(text)} car  "
          f"x{len(text)/max(1,len(native)):.1f}")


if __name__ == "__main__":
    main()
