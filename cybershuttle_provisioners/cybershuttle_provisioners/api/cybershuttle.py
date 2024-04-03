from logging import Logger
from subprocess import PIPE, Popen
from typing import Any

import msgpack
import requests


class CybershuttleAPI:

    def __init__(self, url: str, logger: Logger):
        super().__init__()
        self.url = url
        self.log = logger

    def poll_job_status(self, job_id: int) -> tuple[str, str, str]:
        """
        Checks if job is still running.

        Return:

        job_state (str) one of ["PENDING", "RUNNING", "UNKNOWN", "ERROR"]
        exec_node (str) url of worker node that job is running on

        """
        r = requests.get(f"{self.url}/status/{job_id}")
        state = "UNKNOWN"
        node = eta = ""
        if r.status_code == 200:
            data = r.json()
            state, node, eta = data["state"], data["node"], data["eta"]

        return state, node, eta

    def signal_job(self, job_id: int, signum: int) -> bool:
        """
        Issue signal to a running job.

        """
        r = requests.post(f"{self.url}/signal/{job_id}", data=msgpack.dumps(dict(signum=signum)))
        return r.status_code == 200

    def launch_job(self, job_config: dict[str, Any]) -> int:
        """
        Launch a new job and return its ID.

        """
        self.log.warn(job_config)
        r = requests.post(f"{self.url}/provision", data=msgpack.dumps(job_config))
        if r.status_code == 200:
            data: dict = r.json()  # type: ignore
            return data["job_id"]
        raise RuntimeError()

    def start_forwarding(
        self,
        job_id: int,
        connection_info: dict[str, Any],
    ) -> Popen[bytes]:
        """
        Create a process to forward remote job ports to local

        """

        r = requests.get(f"{self.url}/info/{job_id}")
        if r.status_code == 200:
            ports: dict[str, int] = r.json()["ports"]

        portfwd_cmd = []
        for p, remote_port in ports.items():
            assert p in connection_info
            local_port = connection_info[p]
            host = self.url.rsplit(":", 1)[0]
            portfwd_cmd.extend(["socat", f"tcp-listen:{local_port},fork", f"tcp:{host}:{remote_port}", "|"])
        portfwd_cmd.pop()  # remove last pipe
        portfwd_cmd_str = " ".join(portfwd_cmd)
        self.log.debug(f"Port forward command: {portfwd_cmd_str}")

        # start port forwarding process
        self.log.info(f"Forwarding ports from {self.url} to localhost")
        process = Popen(portfwd_cmd, stdout=PIPE, stderr=PIPE)
        self.log.info(f"Port forwarding started")
        return process
