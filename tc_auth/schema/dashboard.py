from pydantic import BaseModel, ConfigDict, EmailStr, Field


class OAuthConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_id: str = Field(min_length=1)
    client_secret: str = Field(min_length=1)
    redirect_uri: str = Field(min_length=1)



class EmailConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    host: str = Field(min_length=1)
    port: int = Field(ge=1, le=65535)
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)
    sender: EmailStr
    sender_name: str | None = None
    use_tls: bool = True


class JWTConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    secret_key: str = Field(min_length=1)
    algorithm: str = Field(min_length=1)
    session_duration_days: int = Field(ge=1)
    dual_token_mode: bool = False
    access_token_expire_minutes: int | None = Field(default=None, ge=1)
    refresh_token_expire_days: int | None = Field(default=None, ge=1)