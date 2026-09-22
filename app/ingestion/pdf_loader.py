from pathlib import Path
from pypdf import PdfReader


def clean_text(text: str) -> str:
    return "".join(
        char
        for char in text
        if char == "\n"
        or char == "\r"
        or char == "\t"
        or ord(char) >= 32
    )


def extract_pdf_pages(
    file_path: str,
) -> list[dict]:
    path = Path(file_path)
    reader = PdfReader(path)

    pages = []

    for page_number, page in enumerate(
        reader.pages,
        start=1,
    ):
        text = page.extract_text() or ""
        text = clean_text(text)

        if not text.strip():
            continue

        pages.append(
            {
                "page_number": page_number,
                "text": text.strip(),
            }
        )

    return pages