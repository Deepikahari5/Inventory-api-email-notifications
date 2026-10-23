from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import commit_or_conflict
from app.core.exceptions import AuthenticationError, ConflictError, PermissionDeniedError
from app.core.security import (
    REFRESH,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    utcnow,
    verify_password,
)
from app.models.refresh_token import RefreshToken
from app.models.user import User, UserRole
from app.repositories.user_repository import RefreshTokenRepository, UserRepository
from app.schemas.user import TokenPair, UserCreate


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.users = UserRepository(db)
        self.refresh_tokens = RefreshTokenRepository(db)

    def register(self, payload: UserCreate) -> User:
        username = payload.username.strip().lower()
        email = payload.email.strip().lower()
        if self.users.get_by_username(username):
            raise ConflictError("Username is already registered")
        if self.users.get_by_email(email):
            raise ConflictError("Email is already registered")
        user = User(
            username=username,
            email=email,
            full_name=payload.full_name,
            hashed_password=hash_password(payload.password),
            role=UserRole.EMPLOYEE.value,
        )
        self.users.add(user)
        commit_or_conflict(self.db, "Username or email is already registered")
        return user

    def login(self, username: str, password: str) -> TokenPair:
        user = self.users.get_by_username(username.strip().lower())
        if user is None or not verify_password(password, user.hashed_password):
            raise AuthenticationError("Incorrect username or password")
        if not user.is_active:
            raise PermissionDeniedError("Account is disabled")
        return self._issue_pair(user)

    def refresh(self, refresh_token: str) -> TokenPair:
        payload = decode_token(refresh_token, REFRESH)
        record = self.refresh_tokens.get_by_jti(payload["jti"])
        if record is None or record.revoked:
            raise AuthenticationError("Refresh token has been revoked")
        user = self.users.get(int(payload["sub"]))
        if user is None or not user.is_active:
            raise AuthenticationError("User is not available")
        record.revoked = True
        return self._issue_pair(user)

    def logout(self, refresh_token: str) -> None:
        payload = decode_token(refresh_token, REFRESH)
        record = self.refresh_tokens.get_by_jti(payload["jti"])
        if record is not None and not record.revoked:
            record.revoked = True
            self.db.commit()

    def seed_admin(self) -> None:
        settings = get_settings()
        if not (settings.admin_username and settings.admin_email and settings.admin_password):
            return
        username = settings.admin_username.strip().lower()
        if self.users.get_by_username(username):
            return
        admin = User(
            username=username,
            email=settings.admin_email.strip().lower(),
            full_name="Administrator",
            hashed_password=hash_password(settings.admin_password),
            role=UserRole.ADMIN.value,
        )
        self.users.add(admin)
        commit_or_conflict(self.db, "Administrator account already exists")

    def _issue_pair(self, user: User) -> TokenPair:
        access = create_access_token(user.id)
        refresh = create_refresh_token(user.id)
        self.refresh_tokens.add(RefreshToken(jti=refresh.jti, user_id=user.id, expires_at=refresh.expires_at))
        self.db.commit()
        return TokenPair(access_token=access.token, refresh_token=refresh.token)
