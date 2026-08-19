#!/usr/bin/env python3
"""Mide lo que el OCR anade sobre el texto nativo en las paginas que dispara el triaje.

Sin esta medida el umbral es un numero magico: se sabe cuantas paginas manda a
OCR, pero no si esas paginas contenian algo.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np
import pdfplumber
import pypdfium2 as pdfium
from rapidocr_onnxruntime import RapidOCR

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hybrid_pdf_extract import mean_confidence, result_to_text  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Rendimiento real del OCR por pagina")
    parser.add_argument("--pdf", required=True)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--threshold", type=int, default=80)
    parser.add_argument("--min-ink", type=float, default=0.005)
    parser.add_argument("--dpi", type=int, default=160)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    rows = [json.loads(l) for l in Path(args.profile).read_text(encoding="utf-8").splitlines()]
    targets = [r for r in rows if r["native_chars"] < args.threshold and r["ink_coverage"] >= args.min_ink]

    ocr = RapidOCR()
    doc = pdfium.PdfDocument(args.pdf)
    results = []
    with pdfplumber.open(args.pdf) as pdf:
        for r in targets:
            page = r["page"]
            native = (pdf.pages[page - 1].extract_text() or "").strip()
            img = np.array(doc[page - 1].render(scale=args.dpi / 72).to_pil().convert("RGB"))
            res, _ = ocr(cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
            text = result_to_text(res)
            results.append(
                {
                    "doc_id": r["doc_id"],
                    "page": page,
                    "native_chars": len(native),
                    "ocr_chars": len(text),
                    "gain_chars": len(text) - len(native),
                    "ocr_confidence": round(mean_confidence(res), 4),
                }
            )

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as fh:
        for row in results:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    nat = sum(r["native_chars"] for r in results)
    got = sum(r["ocr_chars"] for r in results)
    won = sum(1 for r in results if r["gain_chars"] > 200)
    print(f"{targets[0]['doc_id'] if targets else '?'}: {len(results)} paginas | "
          f"nativo={nat} car -> ocr={got} car (x{got/max(1,nat):.1f}) | "
          f"paginas con ganancia>200 car: {won}")


if __name__ == "__main__":
    main()
