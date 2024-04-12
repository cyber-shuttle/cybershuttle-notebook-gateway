from typing import Any

from pydantic import BaseModel, Field

from cybershuttle_gateway.api import SlurmAPI


class KernelProvisionerConfig(BaseModel):
    username: str
    gateway_url: str
    cluster: str
    transport: str
    spec: dict[str, Any]
    workdir: str = Field(default="")
    exec_path: str = Field(default="")
    user_scripts: str = Field(default="")


class KernelProvisionerMetadata(BaseModel):
    provisioner_name: str
    config: KernelProvisionerConfig


class KernelMetadata(BaseModel):
    kernel_provisioner: KernelProvisionerMetadata


class KernelSummary(BaseModel):
    display_name: str
    language: str
    provisioner_name: str
    username: str
    cluster: str
    transport: str
    spec: dict[str, str]


class KernelSpec(BaseModel):
    argv: list[str]
    display_name: str
    language: str
    env: dict[str, Any]
    metadata: KernelMetadata

    def summarize(self) -> KernelSummary:
        return KernelSummary(
            display_name=self.display_name,
            language=self.language,
            provisioner_name=self.metadata.kernel_provisioner.provisioner_name,
            username=self.metadata.kernel_provisioner.config.username,
            cluster=self.metadata.kernel_provisioner.config.cluster,
            transport=self.metadata.kernel_provisioner.config.transport,
            spec=self.metadata.kernel_provisioner.config.spec,
        )


class ProvisionRequest(KernelProvisionerConfig):
    connection_info: dict[str, Any]


class ClusterConfig(BaseModel):
    loginnode: str = Field(default="")
    proxyjump: str = Field(default="")
    scheduler: str = Field(default="")
    exec_path: str = Field(default="")
    argv: list[str] = Field(default=[])
    env: dict[str, Any] = Field(default={})
    username: str = Field(default="")
    compute_username: str = Field(default="")
    lmod_modules: list[str] = Field(default=[])
    workdir: str = Field(default="")


class UserConfig(BaseModel):
    clusters: dict[str, ClusterConfig]


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
    workdir: str

    class Config:
        arbitrary_types_allowed = True


class JobConfig(BaseModel):
    scheduler: str = "slurm"
    sb_cpus: int = Field(default=1)
    sb_mem_gb: int = Field(default=1)
    sb_partition: str = "cloud"
