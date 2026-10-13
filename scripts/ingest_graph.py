"""Grafo de ingesta por página: texto nativo, triaje y, si hace falta, OCR."""

from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from ocr_utils import mean_confidence, normalize_text, pdf_page_to_bgr, result_to_text
from ocr_normalize import normalize
from triage import TriagePolicy


class PageState(TypedDict, total=False):
    idx: int
    meta: dict
    native: str
    text: str
    method: str
    ocr_confidence: float | None


def build_ingest_graph(pdf, pdf_doc, policy: TriagePolicy, cost, dpi: int):
    """`pdf` es el documento abierto con pdfplumber y `pdf_doc` el de pypdfium2."""
    ocr = None

    def native(state: PageState) -> PageState:
        return {"native": normalize_text(pdf.pages[state["idx"]].extract_text() or "")}

    def route(state: PageState) -> str:
        meta = state["meta"]
        if meta["ink_coverage"] < policy.min_ink:
            return "empty"
        return "ocr" if policy.needs_ocr(meta) else "keep_native"

    def empty(state: PageState) -> PageState:
        return {"method": "EMPTY", "text": "", "ocr_confidence": None}

    def keep_native(state: PageState) -> PageState:
        return {"method": "PLUMBER", "text": state["native"], "ocr_confidence": None}

    def run_ocr(state: PageState) -> PageState:
        nonlocal ocr
        if ocr is None:
            from rapidocr_onnxruntime import RapidOCR
            ocr = RapidOCR()
        res, _ = ocr(pdf_page_to_bgr(pdf_doc, state["idx"], dpi))
        text = normalize(result_to_text(res), cost)
        # el OCR solo sustituye al texto nativo si aporta más de lo que había
        if len(text) > len(state["native"]):
            method, chosen = "OCR", text
        else:
            method, chosen = "PLUMBER", state["native"]
        return {"method": method, "text": chosen, "ocr_confidence": round(mean_confidence(res), 4)}

    graph = StateGraph(PageState)
    graph.add_node("native", native)
    graph.add_node("empty", empty)
    graph.add_node("keep_native", keep_native)
    graph.add_node("ocr", run_ocr)
    graph.add_edge(START, "native")
    graph.add_conditional_edges("native", route, ["empty", "keep_native", "ocr"])
    for node in ("empty", "keep_native", "ocr"):
        graph.add_edge(node, END)
    return graph.compile()
