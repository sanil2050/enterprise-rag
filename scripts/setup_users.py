from sqlalchemy import text

from app.database.database import engine


CREATE_USERS_TABLE = """
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    hashed_password VARCHAR(500) NOT NULL,
    role VARCHAR(100) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


def main():
    with engine.begin() as connection:
        connection.execute(text(CREATE_USERS_TABLE))

    print("users table is ready.")


if __name__ == "__main__":
    main()