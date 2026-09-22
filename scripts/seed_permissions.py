from sqlalchemy import text

from app.database.database import engine


PERMISSIONS = {
    "company_policy.pdf": [
        "employee",
        "hr",
        "admin",
    ],
    "employee_handbook.pdf": [
        "employee",
        "hr",
        "admin",
    ],
    "leave_policy.pdf": [
        "employee",
        "hr",
        "admin",
    ],
    "product_manual.pdf": [
        "employee",
        "hr",
        "admin",
    ],
    "quarterly_report.pdf": [
        "finance",
        "admin",
    ],
    "security_policy.pdf": [
        "security",
        "admin",
    ],
}


def main():
    with engine.begin() as connection:

        for filename, roles in PERMISSIONS.items():

            document = connection.execute(
                text(
                    """
                    SELECT id
                    FROM documents
                    WHERE filename = :filename
                    """
                ),
                {"filename": filename},
            ).fetchone()

            if document is None:
                print(f"WARNING: {filename} not found")
                continue

            document_id = document[0]

            for role in roles:
                connection.execute(
                    text(
                        """
                        INSERT INTO document_access (
                            document_id,
                            role
                        )
                        VALUES (
                            :document_id,
                            :role
                        )
                        ON CONFLICT (
                            document_id,
                            role
                        )
                        DO NOTHING
                        """
                    ),
                    {
                        "document_id": document_id,
                        "role": role,
                    },
                )

    print("Permission rules seeded.")


if __name__ == "__main__":
    main()