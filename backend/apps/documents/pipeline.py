import io
from typing import Generator


def extract_text_from_pdf(data: bytes) -> str:
    import fitz  # PyMuPDF
    doc = fitz.open(stream=data, filetype="pdf")
    pages = [page.get_text() for page in doc]
    return "\n".join(pages)


def extract_text_from_docx(data: bytes) -> str:
    from docx import Document
    doc = Document(io.BytesIO(data))
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


def extract_text_from_txt(data: bytes) -> str:
    return data.decode("utf-8", errors="ignore")


def extract_text(data: bytes, file_type: str) -> str:
    extractors = {
        "pdf": extract_text_from_pdf,
        "docx": extract_text_from_docx,
        "txt": extract_text_from_txt,
    }
    extractor = extractors.get(file_type)
    if not extractor:
        raise ValueError(f"Unsupported file type: {file_type}")
    return extractor(data)


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
