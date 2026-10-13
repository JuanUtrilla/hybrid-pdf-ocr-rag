#!/usr/bin/env python3
"""Responde las preguntas de evaluación con el LLM, con contexto solo nativo y con OCR.

Una respuesta cuenta como correcta si contiene todos los términos de `evidencia`, y
como bien citada si alguna cita apunta a la página correcta. En GPU la salida varía un
poco entre ejecuciones aunque la temperatura sea 0, así que se repite varias veces.
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from qa_graph import DEFAULT_MODEL, TfidfRetriever, build_qa_graph  # noqa: E402
from rag_eval import chunk, contains_answer, load_pages, native_text_of_ocr_pages  # noqa: E402

VARIANTS = ("solo_nativo", "hibrido")


def main() -> None:
    parser = argparse.ArgumentParser(description="Calidad de la respuesta con y sin OCR")
    parser.add_argument("--pages", default="out/pages/*.jsonl")
    parser.add_argument("--pdf-dir", default="data/pdf")
    parser.add_argument("--questions", default="corpus/preguntas.json")
    parser.add_argument("--model", default=os.environ.get("RAG_MODEL", DEFAULT_MODEL))
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--out", default="out/rag_eval/respuestas.json")
    args = parser.parse_args()

    pages = load_pages(args.pages)
    questions = json.loads(Path(args.questions).read_text(encoding="utf-8"))["preguntas"]
    native = native_text_of_ocr_pages(pages, Path(args.pdf_dir))

    results = {"modelo": args.model, "top_k": args.top_k, "runs": args.runs}
    for variant in VARIANTS:
        retriever = TfidfRetriever(chunks=chunk(pages, variant, native), k=args.top_k)
        graph = build_qa_graph(retriever, args.model)
        runs = []
        for _ in range(args.runs):
            rows = []
            for q in questions:
                t0 = time.perf_counter()
                state = graph.invoke({"question": q["pregunta"]})
                gold = f"{q['doc_id']}:p{q['pagina_oro']}"
                rows.append({
                    "id": q["id"],
                    "respuesta": state["answer"],
                    "citas": state["citations"],
                    "correcta": contains_answer(state["answer"], q["evidencia"]),
                    "cita_correcta": any(c.startswith(gold + "[") for c in state["citations"]),
                    "segundos": round(time.perf_counter() - t0, 1),
                })
            runs.append(rows)
        results[variant] = runs

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")

    n = len(questions)
    print(f"Modelo: {args.model}, top-{args.top_k}, {n} preguntas, {args.runs} ejecuciones\n")
    for variant in VARIANTS:
        ok = [sum(r["correcta"] for r in run) for run in results[variant]]
        cited = [sum(r["cita_correcta"] for r in run) for run in results[variant]]
        print(f"  {variant:12s} correctas por ejecución={ok}  citan la página correcta={cited}")
    print()
    print("  Aciertos de cada pregunta en las ejecuciones (solo_nativo / hibrido):")
    for i, q in enumerate(questions):
        a = sum(run[i]["correcta"] for run in results["solo_nativo"])
        b = sum(run[i]["correcta"] for run in results["hibrido"])
        print(f"  {q['id']}  {a}/{args.runs}  {b}/{args.runs}")
    print(f"\nDetalle: {out}")


if __name__ == "__main__":
    main()
