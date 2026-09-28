import unittest
from pdf_audiobook.text.chunker import chunk_text
from pdf_audiobook.pdf.chapter_detector import detect_chapters
from pdf_audiobook.pdf.text_cleaner import clean_pages, unwrap


class CoreTests(unittest.TestCase):
    def test_sentences(self):
        text = "First sentence is short. Second sentence is longer but fits.\n\nThird paragraph."
        chunks = chunk_text(text, 42)
        self.assertEqual(" ".join(chunks), " ".join(text.split()))
        self.assertTrue(all(len(c) <= 42 for c in chunks))
        self.assertEqual(chunks[0], "First sentence is short.")

    def test_long_sentence(self):
        text = "word " * 100
        chunks = chunk_text(text, 21)
        self.assertEqual(" ".join(chunks), text.strip())
        self.assertTrue(all(len(c) <= 21 for c in chunks))

    def test_oversized_word(self):
        with self.assertRaises(ValueError):
            chunk_text("x" * 30, 20)

    def test_empty(self):
        self.assertEqual(chunk_text(""), [])

    def test_headings(self):
        chapters = detect_chapters(["Preface text\nChapter One\nFirst story.", "CHAPTER II\nSecond story.\nPart Three\nThird story."], [])
        self.assertEqual([c.title for c in chapters], ["Front matter", "Chapter One", "CHAPTER II", "Part Three"])
        self.assertEqual(chapters[2].start_page, 2)

    def test_bookmarks(self):
        chapters = detect_chapters(["preface", "a", "b"], [[1, "A", 2], [2, "Nested", 2], [1, "B", 3]])
        self.assertEqual([c.title for c in chapters], ["Front matter", "A", "B"])
        self.assertEqual(chapters[1].text, "a")

    def test_fallback(self):
        self.assertEqual(len(detect_chapters(["text"]*21, [[1, "Invalid", 99]])), 3)

    def test_cleaning(self):
        pages = [f"Repeated header\nA broken nar-\nration line.\n{i}" for i in range(3)]
        self.assertEqual(unwrap(clean_pages(pages)[0]), "A broken narration line.")

    def test_numbered_uppercase_titles(self):
        pages = ["44 IT’S GOOD, RIGHT?\nThe rest of the celebration went off without a hitch.",
                 "The story continues on another page.",
                 "45\nTHE NEXT MORNING\nA new day began."]
        chapters = detect_chapters(clean_pages(pages), [])
        self.assertEqual([c.title for c in chapters], ["44 IT’S GOOD, RIGHT?", "45 THE NEXT MORNING"])
        self.assertIn("another page", chapters[0].text)
        self.assertEqual(chapters[1].start_page, 3)

    def test_numbered_body_and_contents_not_chapters(self):
        pages = ["Contents\n44 IT’S GOOD, RIGHT? .... 321\n45 THE NEXT MORNING .... 330",
                 "44 people attended the celebration.\nThey had a wonderful evening."]
        self.assertEqual(detect_chapters(clean_pages(pages), [])[0].title, "Section 1")

    def test_repeated_numbered_running_header(self):
        pages = ["44 THE CELEBRATION\nSome story text.", "44 THE CELEBRATION\nMore story text."]
        self.assertEqual(detect_chapters(clean_pages(pages), [])[0].title, "Section 1")

    def test_single_book_bookmark_does_not_hide_chapters(self):
        pages = ["44 IT’S GOOD, RIGHT?\nThe celebration ended.",
                 "45 THE NEXT MORNING\nA new day began."]
        chapters = detect_chapters(clean_pages(pages), [[1, "Entire book", 1]])
        self.assertEqual(len(chapters), 2)
        self.assertEqual(chapters[1].title, "45 THE NEXT MORNING")

    def test_nested_chapter_bookmarks(self):
        toc = [[1, "Book", 1], [2, "Part One", 1], [3, "Chapter 1", 1],
               [3, "Chapter 2", 2], [2, "Part Two", 3], [3, "Chapter 3", 3]]
        chapters = detect_chapters(["First story", "Second story", "Third story"], toc)
        self.assertEqual([c.title for c in chapters], ["Chapter 1", "Chapter 2", "Chapter 3"])

    def test_single_book_bookmark_still_allows_fallback(self):
        chapters = detect_chapters(["Story text"] * 21, [[1, "Whole book", 1]])
        self.assertEqual(len(chapters), 3)
