"""Auth request/response schemas."""

from pydantic import BaseModel, Field


class SetupRequest(BaseModel):
    """First-run admin account creation (FR-5)."""

    username: str = Field(min_length=3, max_length=120)
    password: str = Field(min_length=8, max_length=200)


class LoginRequest(BaseModel):
    """Login credentials."""

    username: str
    password: str


class PasswordChangeRequest(BaseModel):
    """Password change payload (FR-3)."""

    current_password: str
    new_password: str = Field(min_length=8, max_length=200)


class AuthStatus(BaseModel):
    """Drives the first-run vs. login vs. app decision on the client."""

    initialized: bool
    authenticated: bool
    username: str | None = None
