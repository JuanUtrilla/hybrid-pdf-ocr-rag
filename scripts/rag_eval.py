#!/usr/bin/env python3
"""Mide si el OCR cambia lo que el RAG es capaz de recuperar.

Construye dos indices sobre el mismo corpus: uno con el texto tal cual lo deja
el pipeline hibrido, y otro ignorando el OCR y quedandose solo con el texto
nativo. Sobre ambos se lanzan las mismas preguntas, cuya respuesta vive dentro
de una imagen del PDF. La diferencia entre los dos recall es, literalmente, lo
que el OCR aporta al sistema final.
"""

from __future__ import annotations

import argparse
import glob
import json
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

WORDS_PER_CHUNK = 180
OVERLAP = 40


def load_pages(pattern: str) -> list[dict]:
    rows = []
    for path in sorted(glob.glob(pattern)):
        rows += [json.loads(l) for l in Path(path).read_text(encoding="utf-8").splitlines()]
    return rows


def chunk(pages: list[dict], use_ocr: bool) -> list[dict]:
    chunks = []
    for page in pages:
        if page["method"] == "EMPTY":
            continue
        text = page["text"] if (use_ocr or page["method"] != "OCR") else ""
        words = text.split()
        if not words:
            continue
        step = WORDS_PER_CHUNK - OVERLAP
        for start in range(0, max(1, len(words)), step):
            piece = " ".join(words[start:start + WORDS_PER_CHUNK])
            if piece.strip():
                chunks.append({"doc_id": page["doc_id"], "page": page["page"],
                               "method": page["method"], "text": piece})
            if start + WORDS_PER_CHUNK >= len(words):
                break
    return chunks


def evaluate(chunks: list[dict], questions: list[dict], top_k: int) -> dict:
    vectorizer = TfidfVectorizer(sublinear_tf=True, ngram_range=(1, 2), min_df=1)
    matrix = vectorizer.fit_transform([c["text"] for c in chunks])
    hits, detail = 0, []
    for q in questions:
        sims = cosine_similarity(vectorizer.transform([q["pregunta"]]), matrix)[0]
        order = sims.argsort()[::-1][:top_k]
        top = [chunks[i] for i in order]
        found = any(c["doc_id"] == q["doc_id"] and c["page"] == q["pagina_oro"] for c in top)
        hits += found
        detail.append({"id": q["id"], "encontrada": found,
                       "recuperado": [f"{c['doc_id']}:p{c['page']}[{c['method']}]" for c in top]})
    return {"n_chunks": len(chunks), "recall": hits / len(questions),
            "aciertos": hits, "total": len(questions), "detalle": detail}


def main() -> None:
    parser = argparse.ArgumentParser(description="Impacto del OCR sobre el recall del RAG")
    parser.add_argument("--pages", default="out/pages/*.jsonl")
    parser.add_argument("--questions", default="corpus/preguntas.json")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--out", default="out/rag_eval/impacto_ocr.json")
    args = parser.parse_args()

    pages = load_pages(args.pages)
    questions = json.loads(Path(args.questions).read_text(encoding="utf-8"))["preguntas"]

    resultados = {}
    for nombre, use_ocr in (("sin_ocr", False), ("con_ocr", True)):
        resultados[nombre] = evaluate(chunk(pages, use_ocr), questions, args.top_k)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(resultados, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Recall@{args.top_k} sobre {len(questions)} preguntas cuya respuesta esta dentro de una imagen\n")
    for nombre in ("sin_ocr", "con_ocr"):
        r = resultados[nombre]
        print(f"  {nombre:9s}  chunks={r['n_chunks']:5d}  recall={r['recall']:.2f}  "
              f"({r['aciertos']}/{r['total']})")
    print()
    for a, b in zip(resultados["sin_ocr"]["detalle"], resultados["con_ocr"]["detalle"]):
        marca = {(False, True): "  RECUPERADA POR EL OCR", (True, True): "", (False, False): "  fallan las dos",
                 (True, False): "  PERDIDA"}[(a["encontrada"], b["encontrada"])]
        print(f"  {a['id']}  sin_ocr={'si' if a['encontrada'] else 'no':2s}  "
              f"con_ocr={'si' if b['encontrada'] else 'no':2s}{marca}")
    print(f"\nDetalle: {out}")


if __name__ == "__main__":
    main()
