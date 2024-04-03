import argparse
import json
import os
from functools import wraps
from pathlib import Path

import msgpack
from flask import Flask, render_template, request

from cybershuttle_gateway.api import SlurmAPI
from cybershuttle_gateway.config import TEMPLATE_DIR
from cybershuttle_gateway.typing import ProvisionRequest, UserConfig

app = Flask(__name__)
state_var: dict[str, dict] = {}
fwd_ports = ["stdin_port", "shell_port", "iopub_port", "hb_port", "control_port"]
ignore_keys = ["api", "forwarding_process", "connection_info"]


class NoUserConfigException(BaseException): ...


def jsonify(data: dict) -> str:
    data = {k: v.decode() if isinstance(v, bytes) else v for k, v in data.items()}
    return json.dumps(data, ensure_ascii=False, indent=2)


def get_gateway_url():
    return request.host_url.rstrip("/")


def get_user_config(user: str) -> UserConfig:
    with open(config_file, "r") as f:
        user_config = json.load(f)
    if user not in user_config:
        raise NoUserConfigException()
    return UserConfig(**user_config[user])


def get_available_kernels(user: str) -> dict[str, dict]:
    data = {}
    user_config = get_user_config(user)
    for cluster_name in user_config.clusters:
        data[cluster_name] = {
            "argv": ["{connection_info}"],
            "display_name": f"cs_{cluster_name}",
            "env": {},
            "language": "python",
            "metadata": {
                "kernel_provisioner": {
                    "config": {
                        "gateway_url": get_gateway_url(),
                        "cluster": cluster_name,
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
    return data


class JobConfig:
    scheduler: str = "slurm"
    sb_cpus: int = 1
    sb_mem_gb: int = 1
    sb_partition: str = "cloud"


def validate_auth(f):
    @wraps(f)
    def wrapper(*args, **kw):
        username = request.args.get("user", type=str, default="")
        try:
            get_user_config(username)
        except NoUserConfigException:
            return "Unauthorized", 403
        return f(*args, **kw)

    return wrapper


@app.route("/")
def admin_panel():
    username = "admin"
    return render_template(
        "index.html",
        gateway_url=get_gateway_url(),
        kernels=get_available_kernels(username),
        defaults=JobConfig(),
    )


@app.route("/kernelspecs")
@validate_auth
def get_kernels():
    username = request.args.get("user", type=str, default="")
    kernels = get_available_kernels(username)
    return jsonify(kernels)


@app.route("/status/<job_id>", methods=["GET"])
@validate_auth
def get_kernel_status(job_id: str):
    """
    Get Kernel status

    Args:
        job_id (str): ID of provisioned kernel

    """
    info = state_var[job_id]
    api: SlurmAPI = info["api"]  # type: ignore
    assert api is not None

    (state, node, eta) = api.poll_job_status(int(job_id))

    if state == "RUNNING" and info["forwarding"] == False:
        api.start_forwarding(
            username=info["username"],
            execnode=node,
            fwd_ports=fwd_ports,
            connection_info=info["ports"],
            proxyjump=info.get("proxyjump", ""),
            loginnode=info.get("loginnode", ""),
        )
        info["forwarding"] = True
    return jsonify(dict(state=state, node=node, eta=eta))


@app.route("/signal/<job_id>", methods=["POST"])
@validate_auth
def signal_kernel(job_id: str):
    """
    Issue Signal to Kernel Process

    Args:
        job_id (str): ID of provisioned kernel

    """
    payload: dict = msgpack.loads(request.get_data())  # type: ignore
    signum = payload["signum"]
    info = state_var[job_id]
    api: SlurmAPI = info["api"]  # type: ignore
    assert api is not None

    result = api.signal_job(int(job_id), signum)
    return jsonify(dict(success=result))


@app.route("/info/<job_id>", methods=["GET"])
@validate_auth
def get_kernel_info(job_id: str):
    """
    Get Kernel Information

    Args:
        job_id (int): ID of provisioned kernel

    """
    info = state_var[job_id]
    return jsonify({k: v for k, v in info.items() if k not in ignore_keys})


@app.route("/provision", methods=["POST"])
@validate_auth
def provision_kernel():
    """
    Provision Kernel using the given method and channel

    Return:
        job_id (str): ID of provisioned kernel

    """
    payload: dict = msgpack.loads(request.get_data())  # type: ignore
    data = ProvisionRequest(**payload)

    username = request.args.get("user", type=str, default="")
    user_config = get_user_config(username)
    cluster_args = user_config.clusters[data.cluster]

    arg_sbatch_opts = "\n".join([f"#SBATCH --{k}={v}" for k, v in data.spec.items()])
    arg_env_vars = "\n".join([f"export {k}={v}" for k, v in cluster_args.env.items()])
    arg_exec_command = " ".join(cluster_args.argv).format(connection_file="$tmpfile")
    arg_lmod_modules = "module load " + " ".join(cluster_args.lmod_modules) if len(cluster_args.lmod_modules) else ""
    arg_connection_info = jsonify(data.connection_info)

    with open(TEMPLATE_DIR / "sbatch.sh", "r") as f:
        job_script = f.read().format(
            SBATCH_OPTS=arg_sbatch_opts,
            CONNECTION_INFO=arg_connection_info,
            ENV_VARS=arg_env_vars,
            LMOD_MODULES=arg_lmod_modules,
            EXEC_COMMAND=arg_exec_command,
        )

    api = SlurmAPI(app.logger)
    api.ssh_prefix = api.build_ssh_command(data.username, cluster_args.loginnode, cluster_args.proxyjump)
    job_id = api.launch_job(job_script)
    state_var[str(job_id)] = {
        "api": api,
        **data.dict(),
        "ports": {k: data.connection_info[k] for k in fwd_ports},
        "forwarding": False,
    }
    return jsonify(dict(job_id=job_id))


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("--host", "-H", type=str, default="0.0.0.0", help="Host to run gateway server")
    parser.add_argument("--port", "-p", type=int, default=9000, help="Port to run gateway server")
    parser.add_argument("--config_file", "-f", type=str, default="~/.local/etc/cybershuttle/user_config.json")
    args = parser.parse_args()

    # make config file path absolute
    config_file = Path(os.path.expandvars(args.config_file)).expanduser().absolute()
    print(f"config_file={config_file}")

    app.run(host=args.host, port=args.port)
