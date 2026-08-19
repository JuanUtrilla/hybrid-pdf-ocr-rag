#!/usr/bin/env python3
"""Reconstruye los espacios que el OCR pierde en capturas de pantalla.

El reconocedor devuelve cadenas como `Ihopethisemailfindsyouwell`. Indexar eso
produce un embedding sin relacion con el texto real y hace irrecuperable la
pagina. La reconstruccion no necesita un diccionario externo: el propio corpus
ya aporta uno, porque las paginas de texto nativo del mismo documento estan
bien segmentadas.

Segmentacion por programacion dinamica sobre el vocabulario observado,
puntuando cada particion por la frecuencia de sus palabras.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter
from pathlib import Path

MAX_WORD = 20
GLUED = re.compile(r"[A-Za-z]{12,}")


def build_vocabulary(texts: list[str], wordlist: Path | None = None) -> Counter:
    """Frecuencias del propio corpus, con una lista general como respaldo.

    El corpus aporta el vocabulario de dominio, que es el que mas importa. La
    lista general cubre el lenguaje corriente que aparece dentro de las
    capturas y que el corpus no contiene.
    """
    vocab: Counter = Counter()
    for text in texts:
        vocab.update(w.lower() for w in re.findall(r"[A-Za-z\']+", text))
    if wordlist and wordlist.exists():
        for line in wordlist.read_text(encoding="utf-8", errors="ignore").splitlines():
            word = line.strip().lower()
            if word.isalpha() and len(word) > 1:
                vocab[word] += 1          # peso minimo: solo evita el penalizador
    return vocab


def make_scorer(vocab: Counter):
    total = sum(vocab.values()) or 1
    floor = math.log(1e-9)

    def cost(word: str) -> float:
        count = vocab.get(word.lower(), 0)
        if count:
            return math.log(count / total)
        return floor - 3.0 * len(word)      # penaliza inventarse palabras largas

    return cost


def split_word(token: str, cost) -> list[str]:
    """Viterbi sobre las particiones de `token`."""
    n = len(token)
    best = [0.0] + [-math.inf] * n
    back = [0] * (n + 1)
    for i in range(1, n + 1):
        for j in range(max(0, i - MAX_WORD), i):
            score = best[j] + cost(token[j:i])
            if score > best[i]:
                best[i], back[i] = score, j
    pieces, i = [], n
    while i > 0:
        pieces.append(token[back[i]:i])
        i = back[i]
    return pieces[::-1]


def normalize(text: str, cost) -> str:
    def repl(match: re.Match) -> str:
        pieces = split_word(match.group(0), cost)
        return " ".join(pieces) if len(pieces) > 1 else match.group(0)

    return GLUED.sub(repl, text)


def main() -> None:
    parser = argparse.ArgumentParser(description="Reconstruye espacios en salida OCR")
    parser.add_argument("--vocab-from", nargs="+", required=True,
                        help="ficheros de texto nativo que aportan el vocabulario")
    parser.add_argument("--text", help="texto suelto a normalizar")
    parser.add_argument("--wordlist", default="/usr/share/dict/words",
                        help="lista de palabras general de respaldo")
    parser.add_argument("--demo", action="store_true")
    args = parser.parse_args()

    texts = [Path(f).read_text(encoding="utf-8", errors="replace") for f in args.vocab_from]
    cost = make_scorer(build_vocabulary(texts, Path(args.wordlist) if args.wordlist else None))

    if args.demo:
        samples = [
            "Ihopethisemailfindsyouwell.I'mwritingtoletyouknow",
            "officefornext2daysbecausemy9yearsongPeteris",
            "thisimageisthatamanisironingclothesonanironingboard",
        ]
        for s in samples:
            print(f"  antes : {s}\n  ahora : {normalize(s, cost)}\n")
        return

    if args.text:
        print(normalize(args.text, cost))


if __name__ == "__main__":
    main()
