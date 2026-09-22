from pwdlib import PasswordHash
from sqlalchemy import text

from app.database.database import engine


password_hash = PasswordHash.recommended()


USERS = [
    {
        "username": "alice",
        "password": "employee123",
        "role": "employee",
    },
    {
        "username": "bob",
        "password": "finance123",
        "role": "finance",
    },
    {
        "username": "admin",
        "password": "admin123",
        "role": "admin",
    },
]


def main():
    with engine.begin() as connection:

        for user in USERS:

            hashed_password = password_hash.hash(
                user["password"]
            )

            connection.execute(
                text(
                    """
                    INSERT INTO users (
                        username,
                        hashed_password,
                        role,
                        is_active
                    )
                    VALUES (
                        :username,
                        :hashed_password,
                        :role,
                        TRUE
                    )
                    ON CONFLICT (username)
                    DO UPDATE SET
                        hashed_password = EXCLUDED.hashed_password,
                        role = EXCLUDED.role,
                        is_active = TRUE
                    """
                ),
                {
                    "username": user["username"],
                    "hashed_password": hashed_password,
                    "role": user["role"],
                },
            )

    print("Development users created.")


if __name__ == "__main__":
    main()