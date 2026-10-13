#!/usr/bin/env python3
"""Extracción híbrida de un documento con la política de triaje medida.

Una fila por página con el texto elegido, su procedencia (PLUMBER, OCR o EMPTY)
y las señales que motivaron la decisión. Cada página pasa por el grafo de ingest_graph.py.
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import pdfplumber
import pypdfium2 as pdfium

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ingest_graph import build_ingest_graph  # noqa: E402
from ocr_normalize import build_vocabulary, make_scorer  # noqa: E402
from triage import POLICIES  # noqa: E402


def _signals(meta: dict) -> dict:
    return {"native_chars": meta["native_chars"], "n_images": meta["n_images"],
            "ink_coverage": meta["ink_coverage"]}


def main() -> None:
    parser = argparse.ArgumentParser(description="Extracción híbrida con triaje medido")
    parser.add_argument("--pdf", required=True)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--policy", default="medido", choices=sorted(POLICIES))
    parser.add_argument("--dpi", type=int, default=160)
    parser.add_argument("--vocab", default="out/native/vocab_en.txt")
    parser.add_argument("--wordlist", default="/usr/share/dict/words")
    args = parser.parse_args()

    profile = {r["page"]: r for r in
               (json.loads(l) for l in Path(args.profile).read_text(encoding="utf-8").splitlines())}

    vocab_path = Path(args.vocab)
    cost = make_scorer(build_vocabulary(
        [vocab_path.read_text(encoding="utf-8", errors="replace")] if vocab_path.exists() else [],
        Path(args.wordlist) if args.wordlist else None))

    rows = []
    with pdfplumber.open(args.pdf) as pdf:
        graph = build_ingest_graph(pdf, pdfium.PdfDocument(args.pdf), POLICIES[args.policy], cost, args.dpi)
        for idx in range(len(pdf.pages)):
            meta = profile[idx + 1]
            state = graph.invoke({"idx": idx, "meta": meta})
            rows.append({"page": idx + 1, "method": state["method"], "text": state["text"],
                         "ocr_confidence": state["ocr_confidence"], **_signals(meta)})

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps({"doc_id": profile[row["page"]]["doc_id"], **row},
                                ensure_ascii=False) + "\n")
    counts = Counter(r["method"] for r in rows)
    print(f"{Path(args.pdf).stem}: {dict(counts)} -> {out}")


if __name__ == "__main__":
    main()
