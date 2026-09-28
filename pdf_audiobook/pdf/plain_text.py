"""Reconstruct prose paragraphs from positioned PDF lines, including drop caps."""
import re
from .text_cleaner import unwrap
from .chapter_detector import HEADING, is_numbered_title


def prose_page(layout: dict) -> str:
    lines = [dict(line) for line in layout["lines"]]
    if not lines:
        return ""
    body = max(layout["sizes"], key=layout["sizes"].get)
    removed = set()
    # A decorative capital may be a separate PDF object, below the first line
    # in extraction order. Match geometrically rather than sorting it as prose.
    for i, cap in enumerate(lines):
        if cap["size"] < body * 1.4 or not re.fullmatch(r'[“"‘\']?[A-Z]', cap["text"]):
            continue
        targets = [(j, line) for j, line in enumerate(lines) if j != i
                   and line["size"] < cap["size"]
                   and 0 <= line["x"] - cap["right"] < body * 3
                   and line["y"] < cap["bottom"] and line["bottom"] > cap["y"]
                   and re.match(r'[a-z]', line["text"])]
        if targets:
            j, target = min(targets, key=lambda pair: pair[1]["y"])
            target["text"] = cap["text"] + target["text"]
            target["x"] = cap["x"]
            target["drop_bottom"] = cap["bottom"]
            removed.add(i)
    lines = [line for i, line in enumerate(lines) if i not in removed]
    margin = min(line["x"] for line in lines if line["size"] <= body * 1.15)
    paragraphs, current = [], []
    previous = None
    drop_bottom = 0
    for line in lines:
        heading = (line["size"] > body * 1.15 or HEADING.fullmatch(line["text"])
                   or is_numbered_title(line["text"]))
        boundary = previous is not None and (
            heading or previous.get("heading")
            or line["y"] - previous["bottom"] > body * .65
            or (line["x"] > margin + body * .8
                and line["y"] >= drop_bottom
                and line["x"] > previous["x"] + body * .5))
        if boundary and current:
            paragraphs.append(unwrap("\n".join(current)))
            current = []
        current.append(line["text"])
        line["heading"] = bool(heading)
        drop_bottom = max(drop_bottom, line.get("drop_bottom", 0))
        previous = line
    if current:
        paragraphs.append(unwrap("\n".join(current)))
    return "\n\n".join(paragraphs)
