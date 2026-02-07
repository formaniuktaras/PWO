from sqlalchemy.orm import Session

from app.models.entities import AuditLog, User


class AuditService:
    def __init__(self, session: Session, user: User | None):
        self.session = session
        self.user = user

    def log(self, action: str, table: str, row_id: str, details: str | None = None) -> None:
        self.session.add(
            AuditLog(
                user_id=self.user.id if self.user else None,
                action=action,
                table_name=table,
                row_id=row_id,
                details=details,
            )
        )
