import tempfile
import unittest
from pathlib import Path
import pymupdf
from pdf_audiobook.pdf.parser import parse_pdf
from pdf_audiobook.pdf.layout_detector import page_layout, detect_layout_titles


class LayoutTests(unittest.TestCase):
    def test_large_number_and_title_with_single_bookmark(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "book.pdf"
            with pymupdf.open() as doc:
                for number, title in [(44, "It's good, right?"), (45, "The next morning")]:
                    page = doc.new_page()
                    page.insert_text((140, 90), str(number), fontsize=23)
                    page.insert_text((190, 90), title, fontsize=23)
                    page.insert_textbox((60, 270, 530, 650),
                                        "The rest of the celebration went off without a hitch. " * 30,
                                        fontsize=12)
                doc.set_toc([[1, "Entire book", 1]])
                doc.save(path)
            book = parse_pdf(str(path))
            self.assertEqual(len(book.chapters), 2)
            self.assertEqual(book.chapters[0].title, "44 It's good, right?")
            self.assertEqual(book.chapters[1].start_page, 2)

    def test_drop_cap_is_not_a_chapter(self):
        with pymupdf.open() as doc:
            page = doc.new_page()
            page.insert_text((60, 100), "T", fontsize=36)
            page.insert_textbox((85, 90, 530, 650), "The story continues. " * 50, fontsize=12)
            self.assertEqual(detect_layout_titles([page_layout(page)]), {})
