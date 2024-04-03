from typing import Any

from pydantic import BaseModel, Field

from cybershuttle_gateway.api import SlurmAPI


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


class NoUserConfigException(BaseException): ...


class JobState(BaseModel):
    api: SlurmAPI = Field(exclude=True)
    username: str
    gateway_url: str
    cluster: ClusterConfig
    transport: str
    spec: dict[str, Any]
    connection_info: dict[str, Any] = Field(exclude=True)
    port_map: list[tuple[int, int]]
    forwarding: bool

    class Config:
        arbitrary_types_allowed = True


class JobConfig(BaseModel):
    scheduler: str = "slurm"
    sb_cpus: int = 1
    sb_mem_gb: int = 1
    sb_partition: str = "cloud"
