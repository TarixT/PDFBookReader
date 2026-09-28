from pathlib import Path
from pdf_audiobook.models import Book
from .text_cleaner import clean_pages
from .chapter_detector import detect_chapters
from .layout_detector import page_layout, detect_layout_titles
from .plain_text import prose_page


def parse_pdf(path: str, report=lambda *args: None, checkpoint=lambda: None) -> Book:
    import pymupdf
    pages = []
    layouts = []
    with pymupdf.open(path) as doc:
        if doc.needs_pass:
            raise ValueError("Encrypted PDF: save an unlocked copy first.")
        for index, page in enumerate(doc):
            checkpoint()
            pages.append(page.get_text(sort=True))
            layouts.append(page_layout(page))
            report("PDF parsing", index+1, len(doc))
        if not any(page.strip() for page in pages):
            raise ValueError("No extractable text. Scanned PDFs require OCR before import.")
        report("Chapter detection", 0, 1)
        layout_titles = detect_layout_titles(layouts)
        report(f"Large-font chapter headings found: {len(layout_titles)}", len(layout_titles), max(1, len(pages)))
        report("Building plain-text paragraphs", 0, len(pages))
        plain_pages = []
        for index, layout in enumerate(layouts):
            checkpoint()
            plain_pages.append(prose_page(layout))
            report("Building plain-text paragraphs", index+1, len(pages))
        chapters = detect_chapters(clean_pages(plain_pages), doc.get_toc(), layout_titles=layout_titles)
        if not chapters:
            raise ValueError("No narratable text remains after PDF cleanup.")
        report(f"Chapter detection complete: {len(chapters)} chapters", len(chapters), len(chapters))
        return Book(doc.metadata.get("title") or Path(path).stem, str(Path(path).resolve()), len(pages), chapters)
