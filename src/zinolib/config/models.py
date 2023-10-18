from pydantic import BaseModel


class UserConfig(BaseModel):
    username: str
    password: str


class ServerV1Config(BaseModel):
    server: str
    port: str = "8001"


class Options(BaseModel):
    autoremove: bool = False
    timeout: int = 30
