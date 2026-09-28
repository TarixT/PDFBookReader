import unittest
from collections import Counter
from pdf_audiobook.pdf.plain_text import prose_page
from pdf_audiobook.pdf.text_cleaner import clean_pages
from pdf_audiobook.text.chunker import chunk_text


class ProseTests(unittest.TestCase):
    def test_drop_cap_and_indented_paragraph(self):
        def line(text, x, y, right, bottom, size=12):
            return dict(text=text, x=x, y=y, right=right, bottom=bottom, size=size)
        layout = {"sizes": Counter({12: 200, 30: 2}), "lines": [
            line('ou want a ride?” Avery asked.', 85, 90, 400, 103),
            line('“Y', 60, 95, 82, 125, 30),
            line('They continued down the road.', 85, 106, 400, 119),
            line('“Great!” Derek replied.', 80, 135, 350, 148)]}
        text = prose_page(layout)
        self.assertTrue(text.startswith('“You want a ride?”'))
        self.assertIn('asked. They continued', text)
        self.assertIn('\n\n“Great!”', text)
        self.assertEqual(clean_pages([text])[0], text)

    def test_paragraphs_are_separate_chunks(self):
        self.assertEqual(chunk_text('One short paragraph.\n\nAnother short paragraph.', 500),
                         ['One short paragraph.', 'Another short paragraph.'])

    def test_quoted_sentence_boundary(self):
        text = '“This is a complete sentence.” Another sentence follows.'
        self.assertEqual(chunk_text(text, 35),
                         ['“This is a complete sentence.”', 'Another sentence follows.'])
