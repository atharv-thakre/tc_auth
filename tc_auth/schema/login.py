from pydantic import BaseModel, EmailStr, Field, field_validator
from ..utils.password_policy import validate_password_strength


class SendOTPRequest(BaseModel):
    email: EmailStr
    frontend_url: str | None = None


class SendMagicLinkRequest(BaseModel):
    email: EmailStr
    frontend_url: str | None = None


class VerifyMagicLinkRequest(BaseModel):
    email: EmailStr
    otp: str = Field(min_length=1)


class LoginPasswordRequest(BaseModel):
    identifier: str = Field(min_length=1)
    password: str = Field(min_length=1)


class LoginOTPRequest(BaseModel):
    email: EmailStr
    otp: str = Field(min_length=6, max_length=6)
    password: str | None = None


class ForgotPasswordRequest(BaseModel):
    email: EmailStr
    otp: str = Field(min_length=6, max_length=6)
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        validate_password_strength(v)
        return v


class SignupPasswordRequest(BaseModel):
    name: str
    email: EmailStr
    handle: str | None = None
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        validate_password_strength(v)
        return v


class SignupOTPRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    otp: str = Field(min_length=6, max_length=6)
    handle: str | None = None

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        validate_password_strength(v)
        return v


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(min_length=1)
