from sqlalchemy import text

from app.database.database import engine


def main():
    with engine.connect() as db:
        result = db.execute(
            text(
                """
                SELECT
                    m.id,
                    m.conversation_id,
                    m.role,
                    m.content,
                    m.created_at
                FROM messages m
                WHERE m.conversation_id = 8
                ORDER BY m.created_at
                """
            )
        )

        for row in result.mappings():
            print(
                f"{row['id']} | "
                f"{row['conversation_id']} | "
                f"{row['role']} | "
                f"{row['content'][:100]}"
            )


if __name__ == "__main__":
    main()