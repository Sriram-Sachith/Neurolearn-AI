from app.core.config import get_settings
from app.core.security import hash_password
from app.models.user import User
from sqlalchemy.orm import Session


def ensure_demo_user(db: Session) -> None:
    settings = get_settings()
    user = db.query(User).filter(User.email == settings.demo_email).first()
    if user:
        return
    db.add(
        User(
            name=settings.demo_name,
            email=settings.demo_email,
            password_hash=hash_password(settings.demo_password),
        )
    )
    db.commit()
