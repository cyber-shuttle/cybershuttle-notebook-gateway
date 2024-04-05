import json
from typing import Any
import socket

from cybershuttle_gateway.typing import KernelSpec, KernelMetadata, KernelProvisionerMetadata, KernelProvisionerConfig


def jsonify(
    data: dict,
) -> str:
    data = {k: v.decode() if isinstance(v, bytes) else v for k, v in data.items()}
    return json.dumps(data, ensure_ascii=False, indent=2)


def get_n_free_ports(min_port: int, max_port: int, n: int):
    choice = []
    for port in range(min_port, max_port + 1):
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
):
    remote_ports = [int(connection_info[p]) for p in port_names]
    local_ports = get_n_free_ports(min_port=9001, max_port=9999, n=len(remote_ports))
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
