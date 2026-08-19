#!/usr/bin/env python3
"""Politica de triaje: decide por pagina si merece la pena llamar al OCR.

La regla no viene de un umbral elegido a ojo. Sale de perfilar 2.497 paginas
y observar que las paginas donde el OCR aporta algo comparten tres rasgos:
poco texto nativo, tinta en el render y al menos una imagen embebida.

Las tres senales atacan un modo de fallo distinto:

- `native_chars`   : la pagina no entrega texto suficiente.
- `ink_coverage`   : descarta paginas en blanco, que no hay nada que leer.
- `n_images`       : el contenido esta rasterizado, que es cuando el OCR gana.
"""

from __future__ import annotations

import argparse
import glob
import json
from dataclasses import dataclass
from pathlib import Path

BLANK_INK = 0.005


@dataclass(frozen=True)
class TriagePolicy:
    """Politica de triaje evaluable sobre un perfil de pagina."""

    max_native_chars: int = 150
    min_ink: float = BLANK_INK
    require_image: bool = True

    def needs_ocr(self, page: dict) -> bool:
        if page["native_chars"] >= self.max_native_chars:
            return False
        if page["ink_coverage"] < self.min_ink:
            return False          # pagina en blanco: renderizarla es tirar computo
        if self.require_image and page["n_images"] < 1:
            return False          # texto vectorial escaso: el OCR leera lo mismo
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
    parser = argparse.ArgumentParser(description="Compara politicas de triaje")
    parser.add_argument("--profiles", nargs="+", required=True)
    parser.add_argument("--yield-files", nargs="*", default=[])
    parser.add_argument("--gain-threshold", type=int, default=200)
    args = parser.parse_args()

    pages = load_profiles(*args.profiles)
    gains = load_yield(*args.yield_files) if args.yield_files else {}

    print(f"{'politica':14s}{'a OCR':>8s}{'% corpus':>10s}{'en blanco':>11s}{'con ganancia':>14s}{'precision':>11s}")
    print("-" * 68)
    for name, policy in POLICIES.items():
        fired = [p for p in pages if policy.needs_ocr(p)]
        blank = sum(1 for p in fired if p["ink_coverage"] < BLANK_INK)
        if gains:
            useful = sum(1 for p in fired
                         if gains.get((p["doc_id"], p["page"]), {}).get("gain_chars", 0) > args.gain_threshold)
            prec = f"{100*useful/len(fired):.0f}%" if fired else "-"
        else:
            useful, prec = 0, "n/d"
        print(f"{name:14s}{len(fired):8d}{100*len(fired)/len(pages):9.1f}%{blank:11d}"
              f"{useful:14d}{prec:>11s}")
    print(f"\n{len(pages)} paginas perfiladas. 'con ganancia' = el OCR anadio mas de "
          f"{args.gain_threshold} caracteres sobre el texto nativo.")


if __name__ == "__main__":
    main()
