import sys
import os

from pathlib import Path

from app.database.database import SessionLocal
from app.ingestion.service import ingest_pdf

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


DATA_DIR =Path("data/raw")


def main():

    pdf_files = sorted(
        DATA_DIR.glob("*.pdf")
    )

    if not pdf_files:
        print("No PDF files found.")
        return

    print(
        f"Found{len(pdf_files)} PDF file(s)."
    )

    db = SessionLocal()

    try:

        for pdf_file in pdf_files:

            try:

                ingest_pdf(
                    str(pdf_file),
                    db,
                )
            except Exception as error:

                db.rollback()

                print(
                    f"ERROR processing"
                    f"{pdf_file.name}:{error}"
                )
    finally:

        db.close()


if __name__ == "__main__":
    main()
