#!/usr/bin/env python3
"""Cachea el render y el resultado del OCR de una pagina.

Guarda las cajas de deteccion, el texto reconocido y la confianza de cada una,
para que las visualizaciones no tengan que reejecutar el OCR.
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

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hybrid_pdf_extract import result_to_text  # noqa: E402
from ocr_normalize import build_vocabulary, make_scorer, normalize  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Cachea render + OCR de una pagina")
    parser.add_argument("--pdf", required=True)
    parser.add_argument("--page", type=int, required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--dpi", type=int, default=200)
    parser.add_argument("--vocab", default="out/native/vocab_en.txt")
    parser.add_argument("--wordlist", default="/usr/share/dict/words")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{Path(args.pdf).stem}_p{args.page}"

    with pdfplumber.open(args.pdf) as pdf:
        native = (pdf.pages[args.page - 1].extract_text() or "").strip()

    doc = pdfium.PdfDocument(args.pdf)
    rgb = np.array(doc[args.page - 1].render(scale=args.dpi / 72).to_pil().convert("RGB"))
    cv2.imwrite(str(out_dir / f"{stem}.png"), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))

    from rapidocr_onnxruntime import RapidOCR
    result, _ = RapidOCR()(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
    result = result or []

    vocab_path = Path(args.vocab)
    cost = make_scorer(build_vocabulary(
        [vocab_path.read_text(encoding="utf-8", errors="replace")] if vocab_path.exists() else [],
        Path(args.wordlist) if args.wordlist else None))

    boxes = [{"box": [[float(x), float(y)] for x, y in box],
              "text": text, "score": float(score)} for box, text, score in result]
    payload = {
        "pdf": args.pdf, "page": args.page, "dpi": args.dpi,
        "size": [rgb.shape[1], rgb.shape[0]],
        "native_text": native,
        "ocr_text": result_to_text(result),
        "ocr_text_normalizado": normalize(result_to_text(result), cost),
        "boxes": boxes,
    }
    (out_dir / f"{stem}.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    print(f"{stem}: {len(boxes)} cajas, nativo={len(native)} car, ocr={len(payload['ocr_text'])} car")


if __name__ == "__main__":
    main()
