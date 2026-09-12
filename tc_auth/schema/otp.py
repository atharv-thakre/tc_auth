from pydantic import BaseModel, ConfigDict
from typing import Literal


class CreateOTP(BaseModel):
    model_config = ConfigDict(extra="forbid")

    identifier: str
    purpose: Literal["signup", "login", "reset", "verify"] = "login"
    expiry: int = 60 * 5  # 5 minutes


class DeleteOTP(BaseModel):
    model_config = ConfigDict(extra="forbid")

    identifier: str
    purpose: Literal["signup", "login", "reset", "verify"] = "login"



