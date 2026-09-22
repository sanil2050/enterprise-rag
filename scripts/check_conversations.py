from sqlalchemy import text

from app.database.database import engine


def main():
    with engine.connect() as db:
        result = db.execute(
            text(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_name IN ('conversations', 'messages')
                ORDER BY table_name
                """
            )
        )

        print(result.fetchall())


if __name__ == "__main__":
    main()