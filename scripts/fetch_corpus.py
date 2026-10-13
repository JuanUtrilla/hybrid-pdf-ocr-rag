#!/usr/bin/env python3
"""Descarga el corpus público de evaluación y registra el SHA-256 de cada PDF.

Los PDF no se versionan: pertenecen a sus autores y solo se usan para medir.
"""

import argparse
import hashlib
import json
from pathlib import Path

import httpx

TIMEOUT = 300.0


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description="Descarga el corpus público")
    parser.add_argument("--corpus", default="corpus/corpus.json")
    parser.add_argument("--dest", default="data/pdf")
    parser.add_argument("--only", nargs="*", help="ids concretos a descargar")
    args = parser.parse_args()

    spec = json.loads(Path(args.corpus).read_text(encoding="utf-8"))
    dest = Path(args.dest)
    dest.mkdir(parents=True, exist_ok=True)

    out = dest / "manifest.json"
    # con --only se actualizan esas entradas sin perder las demás
    previous = json.loads(out.read_text(encoding="utf-8")) if out.exists() else []
    entries = {d["id"]: d for d in previous}
    with httpx.Client(follow_redirects=True, timeout=TIMEOUT) as client:
        for doc in spec["documentos"]:
            if args.only and doc["id"] not in args.only:
                continue
            target = dest / f"{doc['id']}.pdf"
            if target.exists():
                print(f"[ya está] {doc['id']}")
            else:
                response = client.get(doc["url"])
                response.raise_for_status()
                target.write_bytes(response.content)
                print(f"[bajado ] {doc['id']} {len(response.content)//1024} KB")
            entries[doc["id"]] = {"id": doc["id"], "sha256": sha256(target),
                                  "bytes": target.stat().st_size, "url": doc["url"]}

    order = [d["id"] for d in spec["documentos"]]
    manifest = sorted(entries.values(), key=lambda d: order.index(d["id"]))
    out.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nManifiesto: {out} ({len(manifest)} documentos)")


if __name__ == "__main__":
    main()
