import socket
from typing import Any

from cybershuttle_gateway.typing import KernelMetadata, KernelProvisionerConfig, KernelProvisionerMetadata, KernelSpec


def sanitize(
    data: dict,
) -> dict:
    return {k: v.decode() if isinstance(v, bytes) else v for k, v in data.items()}


def get_n_free_ports(choices: list[int], n: int):
    choice: list[int] = []
    for port in choices:
        if len(choice) == n:
            return choice
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind(("", port))
            sock.close()
            choice.append(port)
        except OSError:
            continue
    raise IOError("not enough free ports")


def generate_port_map(
    connection_info: dict[str, Any],
    port_names: list[str],
    reserved_ports: set[int],
):
    remote_ports = [int(connection_info[p]) for p in port_names]
    port_choices = sorted(set(range(9001, 10000)).difference(reserved_ports))
    local_ports = get_n_free_ports(choices=port_choices, n=len(remote_ports))
    return list(zip(remote_ports, local_ports))


def generate_kernel_spec(
    cluster: str,
    user: str,
    workdir: str,
    gateway_url: str,
) -> KernelSpec:

    return KernelSpec(
        argv=["{connection_info}"],
        display_name=f"cs_{cluster}",
        env={},
        language="python",
        metadata=KernelMetadata(
            kernel_provisioner=KernelProvisionerMetadata(
                provisioner_name="cybershuttle",
                config=KernelProvisionerConfig(
                    username=user,
                    gateway_url=gateway_url,
                    cluster=cluster,
                    transport="zmq",
                    spec={
                        "cpus-per-task": 1,
                        "time": "01:00:00",
                    },
                    workdir=workdir,
                ),
            )
        ),
    )
