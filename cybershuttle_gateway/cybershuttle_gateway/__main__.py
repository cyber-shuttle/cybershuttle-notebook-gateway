import json

import msgpack
from flask import Flask, request, render_template

from cybershuttle_gateway.__init__ import TEMPLATE_DIR
from cybershuttle_gateway.api import SlurmAPI
from cybershuttle_gateway.typing import ProvisionRequest

app = Flask(__name__)
state_var: dict[str, dict] = {}
fwd_ports = ["stdin_port", "shell_port", "iopub_port", "hb_port", "control_port"]
ignore_keys = ["api", "forwarding_process", "connection_info"]


def jsonify(data: dict) -> str:
    data = {k: v.decode() if isinstance(v, bytes) else v for k, v in data.items()}
    return json.dumps(data, ensure_ascii=False)


@app.route("/")
def hello():
    return render_template('index.html')


@app.route("/status/<job_id>", methods=["GET"])
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
def get_kernel_info(job_id: str):
    """
    Get Kernel Information

    Args:
        job_id (int): ID of provisioned kernel

    """
    info = state_var[job_id]
    return jsonify({k: v for k, v in info.items() if k not in ignore_keys})


@app.route("/provision/<method_name>/<channel_name>", methods=["POST"])
def provision_kernel(method_name: str, channel_name: str):
    """
    Provision Kernel using the given method and channel

    Args:
        method (str): supported = ["slurm-local", "slurm-remote"]
        channel (str): supported = ["zmq"]

    Return:
        job_id (str): ID of provisioned kernel

    """
    payload: dict = msgpack.loads(request.get_data())  # type: ignore
    data = ProvisionRequest(**payload)
    assert method_name == "slurm"
    assert channel_name == "zmq"

    arg_sbatch_opts = "\n".join([f"#SBATCH --{k}={v}" for k, v in data.sbatch_opts.items()])
    arg_env_vars = "\n".join([f"export {k}={v}" for k, v in data.env_vars.items()])
    arg_exec_command = " ".join(data.exec_command).format(connection_file="$tmpfile")
    arg_lmod_modules = "module load " + " ".join(data.lmod_modules) if len(data.lmod_modules) else ""
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
    api.ssh_prefix = api.build_ssh_command(data.username, data.loginnode, data.proxyjump)
    job_id = api.launch_job(job_script)
    state_var[str(job_id)] = {
        "api": api,
        **data.dict(),
        "ports": {k: data.connection_info[k] for k in fwd_ports},
        "forwarding": False,
    }
    return jsonify(dict(job_id=job_id))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=9000)
