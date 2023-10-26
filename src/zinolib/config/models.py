from typing import Optional

from pydantic import BaseModel


class UserConfig(BaseModel):
    username: str
    password: str


class OptionalUserConfig(BaseModel):
    username: Optional[str]
    password: Optional[str]


class ServerV1Config(BaseModel):
    server: str
    port: int = 8001


class Options(BaseModel):
    autoremove: bool = False
    timeout: int = 30
