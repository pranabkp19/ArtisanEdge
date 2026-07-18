from datetime import datetime

from pydantic import BaseModel, Field, field_validator


# ── Request Schemas ──────────────────────────────────────────────

class RegisterRequest(BaseModel):
    """Body for POST /auth/register."""
    phone_number: str = Field(
        ..., min_length=10, max_length=15,
        description="10–15 digit phone number",
        examples=["9876543210"],
    )
    full_name: str = Field(
        ..., min_length=2, max_length=100,
        examples=["Ramesh Vishwakarma"],
    )
    password: str = Field(
        ..., min_length=6, max_length=128,
        description="Minimum 6 characters",
    )
    role: str = Field(
        default="weaver",
        description="weaver | cooperative_admin | buyer | officer | ngo | admin",
    )
    language_pref: str = Field(default="en", max_length=5)
    region: str | None = Field(default=None, max_length=50)

    @field_validator("phone_number")
    @classmethod
    def phone_must_be_digits(cls, v: str) -> str:
        stripped = v.strip().replace("+", "").replace("-", "").replace(" ", "")
        if not stripped.isdigit():
            raise ValueError("Phone number must contain only digits (and optional +/- separators)")
        return stripped

    @field_validator("role")
    @classmethod
    def role_must_be_valid(cls, v: str) -> str:
        allowed = {"weaver", "cooperative_admin", "buyer", "officer", "ngo", "admin"}
        if v not in allowed:
            raise ValueError(f"Role must be one of {allowed}")
        return v


class LoginRequest(BaseModel):
    """Body for POST /auth/login."""
    phone_number: str = Field(..., min_length=10, max_length=15)
    password: str = Field(..., min_length=1)


class RefreshRequest(BaseModel):
    """Body for POST /auth/refresh."""
    refresh_token: str


# ── Response Schemas ─────────────────────────────────────────────

class UserOut(BaseModel):
    """Public user representation (never includes password_hash)."""
    id: int
    phone_number: str
    full_name: str
    role: str
    language_pref: str
    region: str | None = None
    created_at: datetime
    is_active: bool

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    """Returned on successful login."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserOut


class ErrorResponse(BaseModel):
    """Standard error envelope."""
    error: bool = True
    code: str
    message: str
    details: dict | None = None
