from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import verify_password
from app.models.entities import User


class AuthService:
    def __init__(self, session: Session):
        self.session = session

    def authenticate(self, username: str, password: str) -> User | None:
        user = self.session.scalar(select(User).where(User.username == username, User.is_active.is_(True)))
        if not user:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user
