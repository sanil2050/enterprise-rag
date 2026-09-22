from sqlalchemy import text

from app.database.database import engine


CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS document_access (
    id SERIAL PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    role VARCHAR(100) NOT NULL,
    UNIQUE(document_id, role)
);
"""


def main():
    with engine.begin() as connection:
        connection.execute(text(CREATE_TABLE_SQL))

    print("document_access table is ready.")


if __name__ == "__main__":
    main()