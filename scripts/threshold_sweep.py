#!/usr/bin/env python3
"""Barre el umbral de caracteres del triaje: cuántas páginas manda a OCR y cuántas están en blanco."""

import argparse
import glob
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from triage import BLANK_INK  # noqa: E402

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
    print("\nCada celda: páginas enviadas a OCR / de esas, las que no están en blanco.")


if __name__ == "__main__":
    main()
