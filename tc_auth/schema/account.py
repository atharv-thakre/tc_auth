from pydantic import BaseModel, EmailStr, ConfigDict, field_validator
from ..utils.password_policy import validate_password_strength


class SuperUpdateSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_id: int 
    name: str | None = None
    email: EmailStr | None = None
    handle: str | None = None
    avatar_url: str | None = None
    phone: str | None = None
    role: str | None = None  
    status: str | None = None  
    password: str | None = None

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str | None) -> str | None:
        if v is not None:
            validate_password_strength(v)
        return v


class SuperCreateSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    email: EmailStr | None = None
    handle: str | None = None
    avatar_url: str | None = None
    phone: str | None = None
    role: str | None = None  
    status: str | None = None  
    password: str | None = None

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str | None) -> str | None:
        if v is not None:
            validate_password_strength(v)
        return v


class SuperDeleteSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_id: int


class UpdatePassword(BaseModel):
    model_config = ConfigDict(extra="forbid")
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        validate_password_strength(v)
        return v


class UpdateSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    email: EmailStr | None = None
    handle: str | None = None
    avatar_url: str | None = None
    phone: str | None = None
