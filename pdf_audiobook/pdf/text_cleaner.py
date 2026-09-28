import re
from collections import Counter


def clean_pages(pages: list[str]) -> list[str]:
    """Remove recurring margin lines conservatively, preserving heading lines."""
    from .chapter_detector import join_numbered_titles
    pages = [join_numbered_titles(page) for page in pages]
    lines = [[line.strip() for line in page.strip().splitlines()] for page in pages]
    margins: Counter = Counter()
    for page in lines:
        margins.update(set(page[:1] + page[-1:]))
    repeated = {line for line, count in margins.items()
                if len(lines) >= 3 and count >= max(3, len(lines) * .6)
                and not re.match(r'^(chapter|part)\b', line, re.I)}
    result = []
    for page in lines:
        kept = [line for i, line in enumerate(page)
                if not ((i == 0 or i == len(page)-1) and line in repeated)
                and not re.fullmatch(r'(?:page\s+)?\d+(?:\s+of\s+\d+)?', line, re.I)]
        result.append("\n".join(kept))
    return result


def unwrap(text: str) -> str:
    text = re.sub(r'(\w)-\n(?=[a-z])', r'\1', text)
    return re.sub(r'[^\S\n]+', ' ', re.sub(r'(?<!\n)\n(?!\n)', ' ', text)).strip()
