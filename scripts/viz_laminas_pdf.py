#!/usr/bin/env python3
"""Empaqueta las laminas de la animacion en un unico PDF.

Util cuando conviene leer los pasos con calma, o imprimirlos, en vez de ver
pasar la animacion.
"""

from __future__ import annotations

import argparse
import glob
from pathlib import Path

from PIL import Image


def main() -> None:
    parser = argparse.ArgumentParser(description="Laminas de la animacion en PDF")
    parser.add_argument("--laminas", default="out/figuras/paso_*.png")
    parser.add_argument("--out", default="out/figuras/pipeline_laminas.pdf")
    args = parser.parse_args()

    rutas = sorted(glob.glob(args.laminas))
    if not rutas:
        raise SystemExit(f"sin laminas en {args.laminas}")

    paginas = [Image.open(r).convert("RGB") for r in rutas]
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    paginas[0].save(out, save_all=True, append_images=paginas[1:], resolution=150.0)
    print(f"{out}  {len(paginas)} laminas  {out.stat().st_size // 1024} KB")
    for r in rutas:
        print(f"   {Path(r).name}")


if __name__ == "__main__":
    main()
