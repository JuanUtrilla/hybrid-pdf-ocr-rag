#!/usr/bin/env python3
"""Recall@k del retriever según qué texto se indexa de las páginas que pasaron por OCR.

Las preguntas tienen la respuesta dentro de una imagen del PDF. Se comparan tres índices:

- solo_nativo:      esas páginas con su texto de pdfplumber, como si no hubiera triaje.
- sin_paginas_ocr:  esas páginas fuera del índice (la cota inferior de la primera versión).
- hibrido:          esas páginas con el texto del OCR.
"""

import argparse
import glob
import json
import sys
from pathlib import Path

import pdfplumber
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ocr_utils import normalize_text  # noqa: E402

WORDS_PER_CHUNK = 180
OVERLAP = 40
VARIANTS = ("solo_nativo", "sin_paginas_ocr", "hibrido")


def load_pages(pattern: str) -> list[dict]:
    rows = []
    for path in sorted(glob.glob(pattern)):
        rows += [json.loads(l) for l in Path(path).read_text(encoding="utf-8").splitlines()]
    return rows


def native_text_of_ocr_pages(pages: list[dict], pdf_dir: Path) -> dict[tuple[str, int], str]:
    """Texto de pdfplumber de las páginas que el triaje mandó a OCR."""
    wanted: dict[str, list[int]] = {}
    for p in pages:
        if p["method"] == "OCR":
            wanted.setdefault(p["doc_id"], []).append(p["page"])
    texts = {}
    for doc_id, page_numbers in wanted.items():
        with pdfplumber.open(pdf_dir / f"{doc_id}.pdf") as pdf:
            for n in page_numbers:
                texts[(doc_id, n)] = normalize_text(pdf.pages[n - 1].extract_text() or "")
    return texts


def page_text(page: dict, variant: str, native: dict) -> tuple[str, str]:
    if page["method"] != "OCR" or variant == "hibrido":
        return page["text"], page["method"]
    if variant == "solo_nativo":
        return native[(page["doc_id"], page["page"])], "PLUMBER"
    return "", "OCR"


def chunk(pages: list[dict], variant: str, native: dict) -> list[dict]:
    chunks = []
    step = WORDS_PER_CHUNK - OVERLAP
    for page in pages:
        if page["method"] == "EMPTY":
            continue
        text, method = page_text(page, variant, native)
        words = text.split()
        for start in range(0, len(words), step):
            piece = " ".join(words[start:start + WORDS_PER_CHUNK])
            chunks.append({"doc_id": page["doc_id"], "page": page["page"],
                           "method": method, "text": piece})
            if start + WORDS_PER_CHUNK >= len(words):
                break
    return chunks


def contains_answer(text: str, evidence: list[str]) -> bool:
    text = " ".join(text.lower().split())
    return all(term in text for term in evidence)


def evaluate(chunks: list[dict], questions: list[dict], top_k: int) -> dict:
    vectorizer = TfidfVectorizer(sublinear_tf=True, ngram_range=(1, 2), min_df=1)
    matrix = vectorizer.fit_transform([c["text"] for c in chunks])
    hits, answered, detail = 0, 0, []
    for q in questions:
        sims = cosine_similarity(vectorizer.transform([q["pregunta"]]), matrix)[0]
        order = sims.argsort()[::-1][:top_k]
        top = [chunks[i] for i in order]
        gold = [c for c in top if c["doc_id"] == q["doc_id"] and c["page"] == q["pagina_oro"]]
        found = bool(gold)
        # la página correcta puede recuperarse solo por el título; la respuesta tiene que estar en el texto
        has_answer = any(contains_answer(c["text"], q["evidencia"]) for c in gold)
        hits += found
        answered += has_answer
        detail.append({"id": q["id"], "encontrada": found, "con_respuesta": has_answer,
                       "recuperado": [f"{c['doc_id']}:p{c['page']}[{c['method']}]" for c in top]})
    return {"n_chunks": len(chunks), "recall": hits / len(questions), "aciertos": hits,
            "recall_respuesta": answered / len(questions), "con_respuesta": answered,
            "total": len(questions), "detalle": detail}


def main() -> None:
    parser = argparse.ArgumentParser(description="Impacto del OCR sobre el recall")
    parser.add_argument("--pages", default="out/pages/*.jsonl")
    parser.add_argument("--pdf-dir", default="data/pdf")
    parser.add_argument("--questions", default="corpus/preguntas.json")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--out", default="out/rag_eval/impacto_ocr.json")
    args = parser.parse_args()

    pages = load_pages(args.pages)
    questions = json.loads(Path(args.questions).read_text(encoding="utf-8"))["preguntas"]
    native = native_text_of_ocr_pages(pages, Path(args.pdf_dir))

    results = {v: evaluate(chunk(pages, v, native), questions, args.top_k) for v in VARIANTS}

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Top-{args.top_k} sobre {len(questions)} preguntas: página correcta / página con la respuesta\n")
    for name, r in results.items():
        print(f"  {name:16s} chunks={r['n_chunks']:5d}  página={r['aciertos']}/{r['total']}  "
              f"respuesta={r['con_respuesta']}/{r['total']}")
    print()
    mark = {(True, True): "R", (True, False): "p", (False, False): "-"}
    print("  R = página y respuesta, p = solo la página, - = ninguna")
    for rows in zip(*(results[v]["detalle"] for v in VARIANTS)):
        marks = "  ".join(f"{v}={mark[(r['encontrada'], r['con_respuesta'])]}" for v, r in zip(VARIANTS, rows))
        print(f"  {rows[0]['id']}  {marks}")
    print(f"\nDetalle: {out}")


if __name__ == "__main__":
    main()
