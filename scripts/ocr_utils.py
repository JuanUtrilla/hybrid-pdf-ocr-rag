"""Utilidades de OCR compartidas: render de página, texto por filas y confianza."""

import re

import cv2
import numpy as np
import pypdfium2 as pdfium


def normalize_text(text: str) -> str:
    text = text.replace("\x0c", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def pdf_page_to_bgr(pdf_doc: pdfium.PdfDocument, page_idx: int, dpi: int) -> np.ndarray:
    bitmap = pdf_doc[page_idx].render(scale=dpi / 72, rotation=0)
    rgb = np.array(bitmap.to_pil().convert("RGB"))
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)


def result_to_text(result, vthr: float = 0.5) -> str:
    """Reconstruye el texto agrupando las cajas del OCR por filas."""
    if not result:
        return ""

    boxes = []
    for box, text, score in result:
        ys = [p[1] for p in box]
        xs = [p[0] for p in box]
        boxes.append({
            "ymin": min(ys), "ymax": max(ys), "xmin": min(xs), "xmax": max(xs),
            "ycen": sum(ys) / len(ys), "h": max(ys) - min(ys),
            "text": text, "score": float(score),
        })

    def v_overlap(a, b) -> float:
        inter = max(0.0, min(a["ymax"], b["ymax"]) - max(a["ymin"], b["ymin"]))
        return inter / max(1.0, min(a["h"], b["h"]))

    rows: list[list[dict]] = []
    for item in sorted(boxes, key=lambda b: (b["ycen"], b["xmin"])):
        for row in rows:
            if all(v_overlap(item, other) >= vthr for other in row):
                row.append(item)
                break
        else:
            rows.append([item])

    lines = [" ".join(b["text"] for b in sorted(row, key=lambda b: b["xmin"])) for row in rows]
    return normalize_text("\n".join(lines))


def mean_confidence(result) -> float:
    if not result:
        return 0.0
    return sum(float(item[2]) for item in result) / len(result)
