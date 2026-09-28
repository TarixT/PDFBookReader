import re


def chunk_text(text: str, max_chars: int = 500) -> list[str]:
    """Pack sentences, splitting oversized sentences only at word boundaries."""
    if max_chars < 20:
        raise ValueError("Chunk limit must be at least 20 characters.")
    result: list[str] = []
    current = ""
    # Flush at paragraph boundaries. Closing quotation marks belong to the
    # preceding sentence, and must not hide its punctuation from the splitter.
    units = re.split(r'(\n\s*\n)', text.strip())
    sentences = []
    for unit in units:
        if re.fullmatch(r'\n\s*\n', unit):
            sentences.append(None)
        else:
            sentences.extend(re.split(r'(?<=[.!?])\s+|(?<=[.!?][”"’\'])\s+', unit))
    for sentence in sentences:
        if sentence is None:
            if current:
                result.append(current)
                current = ""
            continue
        sentence = " ".join(sentence.split())
        if not sentence:
            continue
        pieces = [sentence]
        if len(sentence) > max_chars:
            pieces = []
            piece = ""
            for word in sentence.split():
                if len(word) > max_chars:
                    raise ValueError("A word exceeds the chunk limit; increase the limit or clean the text.")
                if len(piece) + len(word) + bool(piece) > max_chars:
                    pieces.append(piece)
                    piece = ""
                piece = f"{piece} {word}".strip()
            if piece:
                pieces.append(piece)
        for piece in pieces:
            if current and len(current) + len(piece) + 1 > max_chars:
                result.append(current)
                current = ""
            current = f"{current} {piece}".strip()
    if current:
        result.append(current)
    return result
