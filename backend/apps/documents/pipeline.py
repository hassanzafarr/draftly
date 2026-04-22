import re
from typing import Generator


def extract_text_from_pdf(file_path: str) -> str:
    import fitz  # PyMuPDF
    doc = fitz.open(file_path)
    pages = []
    for page in doc:
        pages.append(page.get_text())
    return "\n".join(pages)


def extract_text_from_docx(file_path: str) -> str:
    from docx import Document
    doc = Document(file_path)
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


def extract_text_from_txt(file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def extract_text(file_path: str, file_type: str) -> str:
    extractors = {
        "pdf": extract_text_from_pdf,
        "docx": extract_text_from_docx,
        "txt": extract_text_from_txt,
    }
    extractor = extractors.get(file_type)
    if not extractor:
        raise ValueError(f"Unsupported file type: {file_type}")
    return extractor(file_path)


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> Generator[dict, None, None]:
    """Yield dicts with content and char_offset. Splits on word boundaries."""
    words = text.split()
    i = 0
    char_offset = 0
    while i < len(words):
        chunk_words = words[i: i + chunk_size]
        content = " ".join(chunk_words)
        yield {"content": content, "char_offset": char_offset}
        char_offset += len(content)
        i += chunk_size - overlap
