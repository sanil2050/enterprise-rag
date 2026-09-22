from app.database.database import SessionLocal
from sqlalchemy import text


def main():
    db = SessionLocal()

    try:
        entities = db.execute(
            text("SELECT COUNT(*) FROM graph_entities")
        ).scalar()

        relationships = db.execute(
            text("SELECT COUNT(*) FROM graph_relationships")
        ).scalar()

        print(f"Graph entities: {entities}")
        print(f"Graph relationships: {relationships}")

    finally:
        db.close()


if __name__ == "__main__":
    main()