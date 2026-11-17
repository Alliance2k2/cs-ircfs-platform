"""Page-preserving configurable chunking. Tokens here are whitespace estimates."""
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Chunk:
    text: str
    page: int
    heading: str
    ordinal: int


def chunk_pages(pages, size=512, overlap=64, strategy="recursive"):
    if not 32 <= size <= 2048 or not 0 <= overlap < size or strategy not in {"fixed", "recursive", "paragraph", "heading", "token"}:
        raise ValueError("Invalid chunk configuration")
    chunks = []
    for page, text in enumerate(pages, 1):
        heading = ""
        blocks = re.split(r"\n\s*\n", text) if strategy in {"recursive", "paragraph", "heading"} else [text]
        pending = []
        def emit(words):
            if words:
                chunks.append(Chunk(" ".join(words), page, heading, len(chunks)))
        for block in blocks:
            if strategy == "heading" and re.match(r"^#{1,6}\s", block):
                emit(pending)
                pending = []
                heading = block.splitlines()[0].lstrip("# ")[:200]
            words = block.split()
            if strategy in {"paragraph", "heading", "recursive"} and pending and len(pending) + len(words) > size:
                emit(pending)
                pending = pending[-overlap:] if overlap else []
            pending.extend(words)
            while len(pending) > size:
                emit(pending[:size])
                pending = pending[size-overlap:]
        emit(pending)
    if len(chunks) > 5000:
        raise ValueError("Too many chunks")
    return chunks
