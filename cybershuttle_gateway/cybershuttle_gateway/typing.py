from typing import Any

from pydantic import BaseModel


class ProvisionRequest(BaseModel):

    username: str
    loginnode: str
    proxyjump: str
    sbatch_opts: dict[str, str]
    env_vars: dict[str, str]
    exec_command: list[str]
    lmod_modules: list[str]
    connection_info: dict[str, Any]
