"""Текстийг RAG chunk болгох."""


def chunk_text(text: str, size: int = 500, overlap: int = 80) -> list[str]:
    text = text.strip()
    if not text:
        return []
    if len(text) <= size:
        return [text]

    overlap = min(overlap, size // 2)
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + size
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= len(text):
            break
        start = end - overlap
    return chunks
