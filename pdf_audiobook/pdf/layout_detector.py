"""Recognize numbered chapter headings using PDF font sizes and positions."""
import re
from collections import Counter


def page_layout(page) -> dict:
    lines = []
    sizes = Counter()
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            spans = [span for span in line["spans"] if span["text"].strip()]
            if not spans:
                continue
            text = " ".join(span["text"].strip() for span in spans)
            for span in spans:
                sizes[round(span["size"], 1)] += len(span["text"].strip())
            lines.append({"text": text, "size": min(span["size"] for span in spans),
                          "x": line["bbox"][0], "right": line["bbox"][2],
                          "y": line["bbox"][1], "bottom": line["bbox"][3]})
    return {"height": page.rect.height, "lines": sorted(lines, key=lambda x: x["y"]), "sizes": sizes}


def detect_layout_titles(layouts: list[dict]) -> dict[int, str]:
    """Use the dominant body font as a baseline; require a numbered heading."""
    sizes = Counter()
    for layout in layouts:
        sizes.update(layout["sizes"])
    if not sizes:
        return {}
    body_size = sizes.most_common(1)[0][0]
    candidates = {}
    for page, layout in enumerate(layouts, 1):
        lines = layout["lines"]
        for index, line in enumerate(lines):
            if line["y"] > layout["height"] * .4 or line["size"] < body_size * 1.18:
                continue
            title = line["text"].strip()
            if re.fullmatch(r'\d{1,4}[.)]?', title) and index+1 < len(lines):
                following = lines[index+1]
                if (following["size"] >= body_size * 1.18
                        and following["y"] - line["bottom"] < body_size * 3):
                    title += " " + following["text"].strip()
            if (re.fullmatch(r'\d{1,4}[.)]?\s+\D.{1,100}', title)
                    and len(title.split()) <= 16
                    and not re.search(r'\.{2,}|\s\d+\s*$', title)
                    and any(other["y"] > line["bottom"] and other["size"] < line["size"]
                            for other in lines)):
                candidates[page] = title
                break
    counts = Counter(candidates.values())
    return {page: title for page, title in candidates.items() if counts[title] == 1}
