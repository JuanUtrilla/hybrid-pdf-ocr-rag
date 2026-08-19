#!/usr/bin/env python3
"""Barre el umbral de caracteres del triaje sobre los perfiles ya calculados.

Responde a la pregunta que ninguna de las implementaciones previas medía:
cuantas paginas manda a OCR cada umbral, y cuantas de esas paginas estan
realmente en blanco.
"""

from __future__ import annotations

import argparse
import glob
import json
from pathlib import Path

BLANK_INK = 0.005
THRESHOLDS = [10, 40, 80, 150, 300, 600, 1000]


def load(profile_dir: Path) -> dict[str, list[dict]]:
    docs: dict[str, list[dict]] = {}
    for path in sorted(glob.glob(str(profile_dir / "*.jsonl"))):
        rows = [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines()]
        if rows:
            docs[rows[0]["doc_id"]] = rows
    return docs


def main() -> None:
    parser = argparse.ArgumentParser(description="Barrido del umbral de triaje OCR")
    parser.add_argument("--profiles", default="out/profiles")
    args = parser.parse_args()

    docs = load(Path(args.profiles))
    head = "documento".ljust(20) + "pags".rjust(6) + "".join(f"th={t}".rjust(11) for t in THRESHOLDS)
    print(head)
    print("-" * len(head))

    totals = {t: [0, 0] for t in THRESHOLDS}
    for doc_id, rows in docs.items():
        cells = []
        for th in THRESHOLDS:
            fired = [r for r in rows if r["native_chars"] < th]
            useful = [r for r in fired if r["ink_coverage"] >= BLANK_INK]
            totals[th][0] += len(fired)
            totals[th][1] += len(useful)
            cells.append(f"{len(fired)}/{len(useful)}".rjust(11))
        print(doc_id.ljust(20) + str(len(rows)).rjust(6) + "".join(cells))

    n = sum(len(r) for r in docs.values())
    print("-" * len(head))
    print("TOTAL".ljust(20) + str(n).rjust(6)
          + "".join(f"{totals[t][0]}/{totals[t][1]}".rjust(11) for t in THRESHOLDS))
    print("\nCada celda es paginas_enviadas_a_OCR / de_esas_las_que_no_estan_en_blanco.")


if __name__ == "__main__":
    main()
