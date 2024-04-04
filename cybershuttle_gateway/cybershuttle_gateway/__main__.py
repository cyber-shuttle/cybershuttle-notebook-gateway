from __future__ import annotations

import argparse
import json
import logging
import os
from functools import wraps
from pathlib import Path
from typing import overload, Any

import msgpack
from flask import Flask, render_template, request

from cybershuttle_gateway.api import SlurmAPI
from cybershuttle_gateway.config import TEMPLATE_DIR
from cybershuttle_gateway.exceptions import NoUserConfigException
from cybershuttle_gateway.typing import JobConfig, JobState, KernelSpec, ProvisionRequest, UserConfig
from cybershuttle_gateway.util import generate_kernel_spec, generate_port_map, jsonify

app = Flask(__name__)
app.logger.setLevel(logging.DEBUG)
state_var: dict[str, JobState] = {}
fwd_ports = ["shell_port", "iopub_port", "stdin_port", "hb_port", "control_port"]


def get_gateway_url():
    return request.host_url.rstrip("/")


@overload
def get_user_config() -> dict[str, UserConfig]: ...


@overload
def get_user_config(user: str) -> UserConfig: ...


def get_user_config(user: str | None = None) -> UserConfig | dict[str, UserConfig]:
    with open(config_file, "r") as f:
        user_config: dict[str, Any] = json.load(f)
    if user is not None:
        if user not in user_config:
            raise NoUserConfigException()
        data = UserConfig(**user_config[user])
        return data
    else:
        dic = {}
        for user in user_config:
            data = UserConfig(**user_config[user])
            dic[user] = data
        return dic

@overload
def get_available_kernels() -> dict[tuple[str, str], KernelSpec]: ...


@overload
def get_available_kernels(user: str) -> dict[str, KernelSpec]: ...


def get_available_kernels(
    user: str | None = None,
) -> dict[str, KernelSpec] | dict[tuple[str, str], KernelSpec]:
    if user is not None:
        userdata: dict[str, KernelSpec] = {}
        u = get_user_config(user)
        for cluster_name in u.clusters:
            userdata[cluster_name] = generate_kernel_spec(cluster_name, user, get_gateway_url())
        return userdata
    else:
        alldata: dict[tuple[str, str], KernelSpec] = {}
        user_config = get_user_config()
        for user, u in user_config.items():
            for cluster_name in u.clusters:
                alldata[(user, cluster_name)] = generate_kernel_spec(cluster_name, user, get_gateway_url())
        return alldata


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
    # generate params
    gateway_url = get_gateway_url()
    kernel_summaries = {k: v.summarize() for k, v in get_available_kernels().items()}
    defaults = JobConfig()
    # render UI
    return render_template(
        "index.html",
        gateway_url=gateway_url,
        kernels=kernel_summaries,
        defaults=defaults,
    )


@app.route("/kernelspecs")
@validate_auth
def get_kernels():
    username = request.args.get("user", type=str, default="")
    kernels = get_available_kernels(username)
    return jsonify({k: v.dict() for k, v in kernels.items()})


@app.route("/status/<job_id>", methods=["GET"])
@validate_auth
def get_kernel_status(job_id: str):
    """
    Get Kernel status

    Args:
        job_id (str): ID of provisioned kernel

    """
    if job_id not in state_var:
        return "Job Not Found", 404
    state = state_var[job_id]
    assert state.api is not None
    (job_state, job_node, job_eta) = state.api.poll_job_status(int(job_id))
    if job_state == "RUNNING" and state.forwarding == False:
        state.api.start_forwarding(
            username=state.cluster.username,
            compute_username=state.cluster.compute_username,
            execnode=job_node,
            port_map=state.port_map,
            proxyjump=state.cluster.proxyjump,
            loginnode=state.cluster.loginnode,
        )
        state.forwarding = True
    return jsonify(dict(state=job_state, node=job_node, eta=job_eta, ports=state.port_map))


@app.route("/signal/<job_id>", methods=["POST"])
@validate_auth
def signal_kernel(job_id: str):
    """
    Issue Signal to Kernel Process

    Args:
        job_id (str): ID of provisioned kernel

    """
    if job_id not in state_var:
        return "Job Not Found", 404
    info = state_var[job_id]
    payload: dict = msgpack.loads(request.get_data())  # type: ignore
    signum = payload["signum"]
    assert info.api is not None
    result = info.api.signal_job(int(job_id), signum)
    return jsonify(dict(success=result))


@app.route("/info/<job_id>", methods=["GET"])
@validate_auth
def get_kernel_info(job_id: str):
    """
    Get Kernel Information

    Args:
        job_id (int): ID of provisioned kernel

    """
    # username, gateway_url, cluster, transport, spec, port_map, forwarding
    if job_id not in state_var:
        return "Job Not Found", 404
    return state_var[job_id].json()


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
    cluster_cfg = user_config.clusters[data.cluster]

    arg_sbatch_opts = "\n".join([f"#SBATCH --{k}={v}" for k, v in data.spec.items()])
    arg_env_vars = "\n".join([f"export {k}={v}" for k, v in cluster_cfg.env.items()])
    arg_exec_command = " ".join(cluster_cfg.argv).format(connection_file="$tmpfile")
    arg_lmod_modules = "module load " + " ".join(cluster_cfg.lmod_modules) if len(cluster_cfg.lmod_modules) else ""
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
    api.ssh_prefix = api.build_ssh_command(cluster_cfg.username, cluster_cfg.loginnode, cluster_cfg.proxyjump)
    job_id = api.launch_job(job_script)
    # save job state
    state_var[job_id] = JobState(
        api=api,
        username=data.username,
        gateway_url=data.gateway_url,
        cluster=cluster_cfg,
        transport=data.transport,
        spec=data.spec,
        connection_info=data.connection_info,
        port_map=generate_port_map(data.connection_info, fwd_ports),
        forwarding=False,
    )
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
