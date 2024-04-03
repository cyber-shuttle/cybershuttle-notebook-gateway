from typing import Any

from pydantic import BaseModel


class ProvisionRequest(BaseModel):

    username: str
    gateway_url: str
    cluster: str
    transport: str
    spec: dict[str, Any]
    connection_info: dict[str, Any]


class ClusterConfig(BaseModel):
    loginnode: str
    proxyjump: str
    scheduler: str
    argv: list[str]
    env: dict[str, Any]
    username: str
    lmod_modules: list[str]


class UserConfig(BaseModel):
    clusters: dict[str, ClusterConfig]
