import re
from pdf_audiobook.models import Chapter
from .text_cleaner import unwrap

HEADING = re.compile(r'^(?:chapter|part)\s+(?:\d+|[ivxlcdm]+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty)\b.{0,100}$', re.I)

NUMBERED = re.compile(r'^(\d{1,4})[.)]?\s+(.{2,100})$')


def is_numbered_title(line: str) -> bool:
    """Recognize short numbered uppercase titles, excluding contents entries."""
    match = NUMBERED.fullmatch(line.strip())
    if not match:
        return False
    title = match[2]
    return (title.isupper() and len(title.split()) <= 15
            and not re.search(r'\.{2,}|\s\d+\s*$', title))


def join_numbered_titles(page: str) -> str:
    """Join a separately extracted chapter number and its uppercase title."""
    lines = [line.strip() for line in page.splitlines()]
    for i in range(min(3, len(lines)-1)):
        if re.fullmatch(r'\d{1,4}[.)]?', lines[i]) and is_numbered_title(lines[i] + " " + lines[i+1]):
            lines[i:i+2] = [lines[i] + " " + lines[i+1]]
            break
    return "\n".join(lines)


def detect_chapters(pages: list[str], toc: list, section_pages: int = 10,
                    layout_titles: dict[int, str] | None = None) -> list[Chapter]:
    """Compare bookmark structure with headings; a book bookmark is not a chapter."""
    valid = [row for row in toc if len(row) >= 3 and 1 <= row[2] <= len(pages)]
    bookmark_chapters = []
    bookmark_destinations = 0
    layout_titles = layout_titles or {}
    if valid:
        # A common outline has one book node, parts beneath it, then chapters.
        # Prefer a level containing explicit chapter titles; otherwise use the
        # level with the most distinct destinations rather than the book node.
        levels = sorted({row[0] for row in valid})
        def level_score(level):
            rows = [row for row in valid if row[0] == level]
            chapter_pages = {row[2] for row in rows
                             if re.match(r'^chapter\s', str(row[1]), re.I)
                             or is_numbered_title(str(row[1]))}
            return len(chapter_pages), len({row[2] for row in rows}), -level
        level = max(levels, key=level_score)
        starts = sorted({row[2]: row[1] for row in valid if row[0] == level}.items())
        bookmark_destinations = len(starts)
        if starts[0][0] > 1:
            starts.insert(0, (1, "Front matter"))
        chapters = []
        for i, (page, title) in enumerate(starts):
            end = starts[i+1][0]-1 if i+1 < len(starts) else len(pages)
            text = unwrap("\n\n".join(pages[page-1:end]))
            if text:
                chapters.append(Chapter(str(title), text, page))
        bookmark_chapters = chapters
    # Only consider titles near the page top; repeated running headers are not chapters.
    candidates = {}
    counts = {}
    for p, page in enumerate(pages, 1):
        lines = page.splitlines()
        for index, line in enumerate(lines[:3]):
            if is_numbered_title(line) and any(x.strip() for x in lines[index+1:]):
                candidates[(p, index)] = line.strip()
                counts[line.strip()] = counts.get(line.strip(), 0) + 1
                break
    chapters = []
    title, start, buffer = "Front matter", 1, []
    found = False
    for p, page in enumerate(pages, 1):
        if p in layout_titles:
            if buffer and unwrap("\n".join(buffer)):
                chapters.append(Chapter(title, unwrap("\n".join(buffer)), start))
            title, start, buffer = layout_titles[p], p, []
            found = True
            # The title is metadata, not a separate spoken number/title chunk.
            page_lines = page.splitlines()
            for end in range(1, min(8, len(page_lines)) + 1):
                if " ".join(" ".join(page_lines[:end]).split()) == " ".join(title.split()):
                    page = "\n".join(page_lines[end:])
                    break
        for index, line in enumerate(page.splitlines()):
            numbered = candidates.get((p, index))
            if p not in layout_titles and (HEADING.fullmatch(line.strip()) or (numbered and counts[numbered] == 1)):
                if buffer and unwrap("\n".join(buffer)):
                    chapters.append(Chapter(title, unwrap("\n".join(buffer)), start))
                title, start, buffer = line.strip(), p, []
                found = True
            else:
                buffer.append(line)
        buffer.append("")
    if found:
        if buffer and unwrap("\n".join(buffer)):
            chapters.append(Chapter(title, unwrap("\n".join(buffer)), start))
        # A coarse or incomplete outline must not hide more specific headings.
        heading_count = sum(ch.title != "Front matter" for ch in chapters)
        bookmark_count = sum(ch.title != "Front matter" for ch in bookmark_chapters)
        return chapters if heading_count >= bookmark_count else bookmark_chapters
    if bookmark_destinations > 1:
        return bookmark_chapters
    return [Chapter(f"Section {i // section_pages + 1}", unwrap("\n\n".join(pages[i:i+section_pages])), i+1)
            for i in range(0, len(pages), section_pages) if any(pages[i:i+section_pages])]
