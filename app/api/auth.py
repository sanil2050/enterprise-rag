from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pwdlib import PasswordHash
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.database.database import SessionLocal


router = APIRouter(tags=["Authentication"])

password_hash = PasswordHash.recommended()

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/token"
)


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


def authenticate_user(
    db: Session,
    username: str,
    password: str,
):
    result = db.execute(
        text(
            """
            SELECT
                id,
                username,
                hashed_password,
                role,
                is_active
            FROM users
            WHERE username = :username
            """
        ),
        {"username": username},
    ).mappings().first()

    if result is None:
        return None

    if not password_hash.verify(
        password,
        result["hashed_password"],
    ):
        return None

    if not result["is_active"]:
        return None

    return result


def create_access_token(
    username: str,
):
    expires = datetime.now(timezone.utc) + timedelta(
        minutes=settings.jwt_access_token_expire_minutes
    )

    payload = {
        "sub": username,
        "exp": expires,
    }

    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


@router.post("/token")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = authenticate_user(
        db=db,
        username=form_data.username,
        password=form_data.password,
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={
                "WWW-Authenticate": "Bearer",
            },
        )

    access_token = create_access_token(
        username=user["username"],
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={
            "WWW-Authenticate": "Bearer",
        },
    )

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )

        username = payload.get("sub")

        if not username:
            raise credentials_exception

    except jwt.InvalidTokenError:
        raise credentials_exception

    user = db.execute(
        text(
            """
            SELECT
                id,
                username,
                role,
                is_active
            FROM users
            WHERE username = :username
            """
        ),
        {"username": username},
    ).mappings().first()

    if user is None or not user["is_active"]:
        raise credentials_exception

    return user