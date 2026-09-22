import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text

from app.database.database import engine


with engine.connect() as connection:
    result = connection.execute(
        text("SELECT extname FROM pg_extension WHERE extname = 'vector'")
    )

    extension = result.fetchone()

    if extension:
        print("PostgreSQL connected.")
        print("pgvector is enabled.")
    else:
        print("PostgreSQL connected, but pgvector is NOT enabled.")