#!/usr/bin/env python3
"""Extraccion hibrida PDF: texto nativo + OCR fallback.

Formato de salida compatible con el visor y con scripts RAG:

===== PÁGINA 1 [PLUMBER] =====
...

===== PÁGINA 2 [OCR] =====
# confianza media OCR: 0.987
...
"""

from __future__ import annotations

import argparse
import re
import time
from pathlib import Path

import cv2
import numpy as np
import pdfplumber
import pypdfium2 as pdfium
from rapidocr_onnxruntime import RapidOCR


def normalize_text(text: str) -> str:
    text = text.replace("\x0c", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def parse_pages(spec: str) -> set[int]:
    """Parsea paginas 1-indexed: '1,3,10-12'."""
    pages: set[int] = set()
    if not spec:
        return pages
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start, end = part.split("-", 1)
            pages.update(range(int(start), int(end) + 1))
        else:
            pages.add(int(part))
    return pages


def pdf_page_to_bgr(pdf_doc: pdfium.PdfDocument, page_idx: int, dpi: int) -> np.ndarray:
    scale = dpi / 72
    page = pdf_doc[page_idx]
    bitmap = page.render(scale=scale, rotation=0)
    rgb = np.array(bitmap.to_pil().convert("RGB"))
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)


def result_to_text(result, vthr: float = 0.5) -> str:
    """Reconstruye texto agrupando cajas OCR por filas."""
    if not result:
        return ""

    boxes = []
    for box, text, score in result:
        ys = [p[1] for p in box]
        xs = [p[0] for p in box]
        boxes.append(
            {
                "ymin": min(ys),
                "ymax": max(ys),
                "xmin": min(xs),
                "xmax": max(xs),
                "ycen": sum(ys) / len(ys),
                "h": max(ys) - min(ys),
                "text": text,
                "score": float(score),
            }
        )

    def v_overlap(a, b) -> float:
        inter = max(0.0, min(a["ymax"], b["ymax"]) - max(a["ymin"], b["ymin"]))
        return inter / max(1.0, min(a["h"], b["h"]))

    rows: list[list[dict]] = []
    for item in sorted(boxes, key=lambda b: (b["ycen"], b["xmin"])):
        placed = False
        for row in rows:
            if all(v_overlap(item, other) >= vthr for other in row):
                row.append(item)
                placed = True
                break
        if not placed:
            rows.append([item])

    lines: list[str] = []
    for row in rows:
        ordered = sorted(row, key=lambda b: b["xmin"])
        lines.append(" ".join(b["text"] for b in ordered))
    return normalize_text("\n".join(lines))


def mean_confidence(result) -> float:
    if not result:
        return 0.0
    scores = [float(item[2]) for item in result]
    return sum(scores) / len(scores) if scores else 0.0


def extract(args: argparse.Namespace) -> None:
    pdf_path = Path(args.pdf)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    force_ocr_pages = parse_pages(args.force_ocr_pages)

    t0 = time.perf_counter()
    ocr = RapidOCR(det_use_cuda=not args.cpu, cls_use_cuda=not args.cpu, rec_use_cuda=not args.cpu)

    pdf_doc = pdfium.PdfDocument(str(pdf_path))
    outputs: list[str] = []
    stats = {"PLUMBER": 0, "OCR": 0, "EMPTY": 0}

    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        max_pages = min(total_pages, args.max_pages) if args.max_pages else total_pages

        for page_idx in range(max_pages):
            page_no = page_idx + 1
            native_chars = len(pdf.pages[page_idx].chars)
            use_ocr = page_no in force_ocr_pages or native_chars < args.ocr_char_threshold

            if use_ocr:
                img = pdf_page_to_bgr(pdf_doc, page_idx, args.dpi)
                result, _elapsed = ocr(img)
                text = result_to_text(result)
                conf = mean_confidence(result)
                method = "OCR"
                body = f"# confianza media OCR: {conf:.3f}\n{text}"
            else:
                text = normalize_text(pdf.pages[page_idx].extract_text() or "")
                method = "PLUMBER" if text else "EMPTY"
                body = text

            stats[method] = stats.get(method, 0) + 1
            outputs.append(f"\n===== PÁGINA {page_no} [{method}] =====\n{body}\n")
            print(
                f"p.{page_no:03d}/{max_pages} {method:<7} "
                f"native_chars={native_chars:<5} text_chars={len(text):<5}"
            )

    out_path.write_text("".join(outputs), encoding="utf-8")
    elapsed = time.perf_counter() - t0
    print(f"\nTexto exportado: {out_path}")
    print(f"Stats: {stats} | tiempo={elapsed:.1f}s")


def main() -> None:
    parser = argparse.ArgumentParser(description="Extraccion hibrida PDF + OCR")
    parser.add_argument("--pdf", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--ocr-char-threshold", type=int, default=80)
    parser.add_argument("--force-ocr-pages", default="")
    parser.add_argument("--max-pages", type=int, default=0)
    parser.add_argument("--dpi", type=int, default=160)
    parser.add_argument("--cpu", action="store_true")
    args = parser.parse_args()
    extract(args)


if __name__ == "__main__":
    main()
