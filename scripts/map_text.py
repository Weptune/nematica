"""The map's fixed text sample (docs/MAP.md): public-domain books from Project Gutenberg, headers removed,
concatenated in this order and tokenised with the GPT-NeoX tokenizer (shared by Pythia and Mamba).
Writes data/external/books/tokens.npy (first 200,000 tokens)."""
import re
import sys
import subprocess
from pathlib import Path

import numpy as np

BOOKS = [1342, 2701, 84, 98, 1661, 11, 345, 1400]      # Austen, Melville, Shelley, Dickens, Doyle, Carroll, Stoker, Dickens
OUT = Path(__file__).resolve().parents[1] / "data/external/books"


def clean(t):
    a = re.search(r"\*\*\* ?START OF (THE|THIS) PROJECT GUTENBERG EBOOK.*?\*\*\*", t)
    b = re.search(r"\*\*\* ?END OF (THE|THIS) PROJECT GUTENBERG EBOOK", t)
    return t[a.end() if a else 0: b.start() if b else len(t)].strip()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    texts = []
    for b in BOOKS:
        f = OUT / f"pg{b}.txt"
        if not f.exists():
            subprocess.run(["curl", "-sSfL", "-o", str(f), f"https://www.gutenberg.org/cache/epub/{b}/pg{b}.txt"], check=True)
        texts.append(clean(f.read_text(encoding="utf-8", errors="ignore")))
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained("EleutherAI/pythia-70m")
    ids = tok("\n\n".join(texts))["input_ids"]
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 200_000
    np.save(OUT / "tokens.npy", np.array(ids[:n], dtype=np.int32))
    print(len(ids), "tokens in total; saved", min(n, len(ids)))


if __name__ == "__main__":
    main()
