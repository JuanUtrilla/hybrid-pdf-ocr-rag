#!/usr/bin/env python3
"""Políticas de triaje: decide por página si merece la pena pasarla por OCR.

Compara la regla medida (poco texto nativo, tinta en el render y alguna imagen
embebida) con los umbrales de caracteres de siempre.
"""

import argparse
import glob
import json
from dataclasses import dataclass
from pathlib import Path

BLANK_INK = 0.005


@dataclass(frozen=True)
class TriagePolicy:
    max_native_chars: int = 150
    min_ink: float = BLANK_INK
    require_image: bool = True

    def needs_ocr(self, page: dict) -> bool:
        if page["native_chars"] >= self.max_native_chars:
            return False
        if page["ink_coverage"] < self.min_ink:
            return False          # página en blanco
        if self.require_image and page["n_images"] < 1:
            return False          # texto vectorial escaso: el OCR leería lo mismo
        return True


POLICIES = {
    "chars_10": TriagePolicy(10, 0.0, False),        # umbral heredado, sin medir
    "chars_80": TriagePolicy(80, 0.0, False),        # umbral heredado, sin medir
    "chars_1000": TriagePolicy(1000, 0.0, False),    # umbral heredado, sin medir
    "medido": TriagePolicy(150, BLANK_INK, True),    # derivada de los perfiles
}


def load_profiles(*patterns: str) -> list[dict]:
    rows: list[dict] = []
    for pattern in patterns:
        for path in sorted(glob.glob(pattern)):
            rows += [json.loads(l) for l in Path(path).read_text(encoding="utf-8").splitlines()]
    return rows


def load_yield(*patterns: str) -> dict[tuple[str, int], dict]:
    return {(r["doc_id"], r["page"]): r for r in load_profiles(*patterns)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Compara políticas de triaje")
    parser.add_argument("--profiles", nargs="+", required=True)
    parser.add_argument("--yield-files", nargs="*", default=[])
    parser.add_argument("--gain-threshold", type=int, default=200)
    args = parser.parse_args()

    pages = load_profiles(*args.profiles)
    gains = load_yield(*args.yield_files) if args.yield_files else {}

    print(f"{'política':12s}{'a OCR':>7s}{'% corpus':>10s}{'en blanco':>11s}"
          f"{'medidas':>9s}{'con ganancia':>14s}{'precisión':>11s}")
    for name, policy in POLICIES.items():
        fired = [p for p in pages if policy.needs_ocr(p)]
        blank = sum(1 for p in fired if p["ink_coverage"] < BLANK_INK)
        # la ganancia solo se conoce en las páginas a las que se pasó el OCR; el resto no cuenta
        measured = [gains[(p["doc_id"], p["page"])] for p in fired if (p["doc_id"], p["page"]) in gains]
        useful = sum(1 for g in measured if g["gain_chars"] > args.gain_threshold)
        prec = f"{100 * useful / len(measured):.0f}%" if measured else "-"
        print(f"{name:12s}{len(fired):7d}{100 * len(fired) / len(pages):9.1f}%{blank:11d}"
              f"{len(measured):9d}{useful:14d}{prec:>11s}")
    print(f"\n{len(pages)} páginas perfiladas. Precisión = páginas con ganancia (> {args.gain_threshold} "
          f"caracteres sobre el nativo) entre las medidas.")


if __name__ == "__main__":
    main()
