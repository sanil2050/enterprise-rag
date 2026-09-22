from app.ingestion.pdf_loader import extract_pdf_text


text = extract_pdf_text(
    "data/raw/employee_handbook.pdf"
)

print(text[:5000])