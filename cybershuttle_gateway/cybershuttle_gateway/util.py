import json
from typing import Any


def jsonify(
    data: dict,
) -> str:
    data = {k: v.decode() if isinstance(v, bytes) else v for k, v in data.items()}
    return json.dumps(data, ensure_ascii=False, indent=2)


def generate_port_map(
    connection_info: dict[str, Any],
    port_names: list[str],
):
    remote_ports = [int(connection_info[p]) for p in port_names]
    # TODO assign 5 random ports instead
    local_ports = [9100, 9200, 9300, 9400, 9500]
    return list(zip(remote_ports, local_ports))


def generate_kernel_spec(
    cluster: str,
    user: str,
    gateway_url: str,
):
    return {
        "argv": ["{connection_info}"],
        "display_name": f"cs_{cluster}",
        "env": {},
        "language": "python",
        "metadata": {
            "kernel_provisioner": {
                "config": {
                    "gateway_url": gateway_url,
                    "cluster": cluster,
                    "transport": "zmq",
                    "spec": {
                        "cpus-per-task": "1",
                        "time": "01:00:00",
                    },
                    "username": user,
                },
                "provisioner_name": "cybershuttle",
            }
        },
    }
