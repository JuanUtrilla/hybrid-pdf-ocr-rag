#!/usr/bin/env python3
"""Extraccion hibrida del corpus aplicando la politica de triaje medida.

Genera un JSONL por documento con una fila por pagina: el texto finalmente
elegido, de donde salio y las senales que motivaron la decision. Guardar el
origen es lo que permite auditar despues una respuesta del RAG.
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
from hybrid_pdf_extract import mean_confidence, normalize_text, result_to_text  # noqa: E402
from ocr_normalize import build_vocabulary, make_scorer, normalize  # noqa: E402
from triage import POLICIES  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Extraccion hibrida con triaje medido")
    parser.add_argument("--pdf", required=True)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--policy", default="medido", choices=sorted(POLICIES))
    parser.add_argument("--dpi", type=int, default=160)
    parser.add_argument("--vocab", default="out/native/vocab_en.txt")
    parser.add_argument("--wordlist", default="/usr/share/dict/words")
    args = parser.parse_args()

    policy = POLICIES[args.policy]
    profile = {r["page"]: r for r in
               (json.loads(l) for l in Path(args.profile).read_text(encoding="utf-8").splitlines())}

    vocab_path = Path(args.vocab)
    cost = make_scorer(build_vocabulary(
        [vocab_path.read_text(encoding="utf-8", errors="replace")] if vocab_path.exists() else [],
        Path(args.wordlist) if args.wordlist else None))

    ocr = None
    doc = pdfium.PdfDocument(args.pdf)
    rows = []
    with pdfplumber.open(args.pdf) as pdf:
        for idx, page in enumerate(pdf.pages):
            page_no = idx + 1
            meta = profile[page_no]
            native = normalize_text(page.extract_text() or "")

            if meta["ink_coverage"] < policy.min_ink:
                rows.append({"page": page_no, "method": "EMPTY", "text": "",
                             "ocr_confidence": None, **_signals(meta)})
                continue

            if not policy.needs_ocr(meta):
                rows.append({"page": page_no, "method": "PLUMBER", "text": native,
                             "ocr_confidence": None, **_signals(meta)})
                continue

            if ocr is None:
                from rapidocr_onnxruntime import RapidOCR
                ocr = RapidOCR()
            img = np.array(doc[idx].render(scale=args.dpi / 72).to_pil().convert("RGB"))
            res, _ = ocr(cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
            text = normalize(result_to_text(res), cost)
            # el OCR solo sustituye al texto nativo si aporta mas de lo que habia
            method, chosen = ("OCR", text) if len(text) > len(native) else ("PLUMBER", native)
            rows.append({"page": page_no, "method": method, "text": chosen,
                         "ocr_confidence": round(mean_confidence(res), 4), **_signals(meta)})

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps({"doc_id": profile[row["page"]]["doc_id"], **row},
                                ensure_ascii=False) + "\n")
    counts: dict[str, int] = {}
    for r in rows:
        counts[r["method"]] = counts.get(r["method"], 0) + 1
    print(f"{Path(args.pdf).stem}: {counts} -> {out}")


def _signals(meta: dict) -> dict:
    return {"native_chars": meta["native_chars"], "n_images": meta["n_images"],
            "ink_coverage": meta["ink_coverage"]}


if __name__ == "__main__":
    main()
