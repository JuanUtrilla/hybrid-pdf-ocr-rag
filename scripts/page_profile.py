#!/usr/bin/env python3
"""Perfila cada pagina de un PDF antes de decidir si necesita OCR.

Emite un JSONL con una fila por pagina: caracteres nativos, imagenes,
cobertura de tinta del render y las senales de calidad del texto embebido.
Sobre ese perfil se puede evaluar cualquier politica de triaje sin volver
a abrir los PDF.
"""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from pathlib import Path

import numpy as np
import pdfplumber
import pypdfium2 as pdfium

INK_DPI = 110
INK_THRESHOLD = 200


def strip_accents(word: str) -> str:
    decomposed = unicodedata.normalize("NFKD", word.lower())
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def text_signals(text: str) -> dict:
    words = re.findall(r"[^\W\d_]+", text, flags=re.UNICODE)
    if len(words) < 20:
        return {"n_words": len(words), "single_letter_rate": None, "alpha_rate": None}
    normalized = [strip_accents(w) for w in words]
    return {
        "n_words": len(words),
        "single_letter_rate": sum(1 for w in normalized if len(w) == 1) / len(normalized),
        "alpha_rate": sum(c.isalpha() or c.isspace() for c in text) / max(1, len(text)),
    }


def ink_coverage(pdf_doc: pdfium.PdfDocument, page_idx: int) -> float:
    """Fraccion de pixeles oscuros del render. Distingue pagina en blanco de pagina con contenido."""
    bitmap = pdf_doc[page_idx].render(scale=INK_DPI / 72)
    gray = np.array(bitmap.to_pil().convert("L"))
    return float((gray < INK_THRESHOLD).mean())


def profile(pdf_path: Path, doc_id: str) -> list[dict]:
    rows: list[dict] = []
    pdf_doc = pdfium.PdfDocument(str(pdf_path))
    with pdfplumber.open(pdf_path) as pdf:
        for idx, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            rows.append(
                {
                    "doc_id": doc_id,
                    "page": idx + 1,
                    "native_chars": len(page.chars),
                    "native_text_chars": len(text.strip()),
                    "n_images": len(page.images),
                    "ink_coverage": round(ink_coverage(pdf_doc, idx), 5),
                    **text_signals(text),
                }
            )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Perfila paginas de PDF para el triaje de OCR")
    parser.add_argument("--pdf", required=True)
    parser.add_argument("--doc-id", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    rows = profile(Path(args.pdf), args.doc_id)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    blank = sum(1 for r in rows if r["ink_coverage"] < 0.005)
    print(f"{args.doc_id}: {len(rows)} paginas, {blank} en blanco -> {out}")


if __name__ == "__main__":
    main()
