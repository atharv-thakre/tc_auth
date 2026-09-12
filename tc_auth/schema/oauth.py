from pydantic import BaseModel, ConfigDict

class CreateOAuth(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_id: int
    provider: str
    provider_user_id: str



class DeleteOAuth(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_id: int
    provider: str


class LinkOAuthRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    frontend_url: str | None = None
    provider_user_id: str | None = None



