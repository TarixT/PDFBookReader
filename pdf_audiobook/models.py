from dataclasses import dataclass, field


@dataclass
class TextChunk:
    index: int
    text: str


@dataclass
class AudioSegment:
    path: str
    sample_rate: int
    frames: int


@dataclass
class Chapter:
    title: str
    text: str
    start_page: int = 1
    chunks: list[TextChunk] = field(default_factory=list)


@dataclass
class Book:
    title: str
    source: str
    page_count: int
    chapters: list[Chapter]
