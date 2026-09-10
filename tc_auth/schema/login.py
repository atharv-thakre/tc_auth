from pydantic import BaseModel, EmailStr, Field


class SendOTPRequest(BaseModel):
    email: EmailStr


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
    password: str = Field(min_length=8)


class SignupPasswordRequest(BaseModel):
    name: str
    email: EmailStr
    handle: str | None = None
    password: str = Field(min_length=8)


class SignupOTPRequest(BaseModel):
    name: str
    email: EmailStr
    password: str = Field(min_length=8)
    otp: str = Field(min_length=6, max_length=6)
    handle: str | None = None
