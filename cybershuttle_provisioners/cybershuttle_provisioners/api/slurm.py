import re
from logging import Logger
from subprocess import PIPE, Popen, TimeoutExpired, check_output
from typing import Any


class SlurmAPI:

    def __init__(self, logger: Logger, ssh_prefix: list[str] = []):
        super().__init__()
        self.log = logger
        self.ssh_prefix = ssh_prefix

    def poll_job_status(self, job_id: int) -> tuple[str, str, str]:
        """
        Checks if SLURM job is still running.

        Return:

        job_state (str) one of ["PENDING", "RUNNING", "UNKNOWN", "ERROR"]
        exec_node (str) url of worker node that job is running on

        """

        # poll for job state
        self.log.info(f"requesting job state: {job_id}")
        prefix = self.ssh_prefix.copy()
        if len(prefix) > 0:
            prefix.append("-T")
        poll_command = prefix + ["bash", "-c", f"squeue -h -j {job_id} -o '%T %B %S'"]
        self.log.debug(f"poll command: {' '.join(poll_command)}")
        state = "UNKNOWN"
        node = eta = stdout = ""
        try:
            stdout = check_output(poll_command).decode().strip()
            self.log.info(f"got job state: {stdout}")
        except:
            state = "ERROR"
            self.log.error(f"error in poll command")

        if len(splits := stdout.split(" ")) == 3:
            state, node, eta = splits

        return state, node, eta

    def signal_job(self, job_id: int, signum: int) -> bool:
        """
        Issue signal to a running job.

        """

        signal_cmd = self.ssh_prefix + ["bash", "--login", "-c", f"scancel -s {signum} {job_id}"]
        signal_cmd_str = " ".join(signal_cmd)
        self.log.info(f"signaling kernel job ({job_id}): {signal_cmd_str}")
        status = None
        try:
            check_output(signal_cmd).decode().strip()
            self.log.info(f"kernel job signaled ({job_id})")
            status = True
        except:
            self.log.error(f"error when signaling kernel job")
            status = False
        return status

    def launch_job(self, job_script: str) -> int:
        """
        Launch a SLURM job and return its ID.

        """

        # build spawn_cmd
        spawn_cmd = self.ssh_prefix + ["bash", "--login", "-c", "sbatch --parsable"]
        spawn_cmd_str = " ".join(spawn_cmd)
        self.log.info(f"Launching Kernel: {spawn_cmd_str}")

        try:
            spawn_process = Popen(spawn_cmd, stdout=PIPE, stderr=PIPE, stdin=PIPE)
            stdout, stderr = spawn_process.communicate(input=job_script.encode(), timeout=10.0)
            stdout = stdout.decode().strip()
            stderr = stderr.decode().strip()
            # check exit code
            if not spawn_process.returncode == 0:
                raise RuntimeError(f"SSH command returned error code {spawn_process.returncode}:\n{stderr}\n")
        except TimeoutExpired:
            raise RuntimeError(f"SSH command timed out:\n{spawn_cmd_str}\n")
        self.log.info(f"Kernel Launched: {stdout}")

        # get SLURM job id from stdout
        job_id = re.search(r"(\d+)", stdout, re.IGNORECASE)
        if job_id is None:
            raise RuntimeError("Cannot find SLURM Job ID in stdout")
        job_id = int(job_id.group(1))
        self.log.debug(f"SLURM Job ID: {job_id}")

        return job_id

    def build_ssh_command(self, username: str, loginnode: str, proxyjump: str = "") -> list[str]:
        """
        Create an SSH command for the given credentials and target

        """
        assert len(username) > 0
        assert len(loginnode) > 0

        ssh_command = ["ssh", "-tA"]
        if len(proxyjump) > 0:
            ssh_command.extend(["-J", f"{username}@{proxyjump}"])
        ssh_command.extend([f"{username}@{loginnode}"])

        self.log.debug(f"SSH command: {ssh_command}")

        return ssh_command

    def start_forwarding(
        self,
        username: str,
        execnode: str,
        fwd_ports: list[str],
        connection_info: dict[str, Any],
        proxyjump: str = "",
        loginnode: str = "",
    ) -> Popen[bytes]:
        """
        Create a process to forward ports via SSH

        """

        # assertions
        assert len(username) > 0
        assert len(execnode) > 0
        assert len(fwd_ports) > 0
        for p in fwd_ports:
            assert p in connection_info

        proxyjump_args = []
        if len(proxyjump) > 0 and len(loginnode) > 0:
            proxyjump_args.extend(["-J", f"{username}@{proxyjump},{username}@{loginnode}"])
        elif len(loginnode) > 0:
            proxyjump_args.extend(["-J", f"{username}@{loginnode}"])

        portfwd_args = []
        for p in fwd_ports:
            port = connection_info[p]
            portfwd_args.extend(["-L", f"{port}:localhost:{port}"])

        ssh_command = ["ssh", "-fNA", "-o", "StrictHostKeyChecking=no"] + proxyjump_args + portfwd_args
        ssh_command.append(f"{username}@{execnode}")

        # start port forwarding process
        self.log.info(f"Starting SSH tunnel from {execnode} to localhost")
        self.log.debug(f'SSH command: {" ".join(ssh_command)}')
        process = Popen(ssh_command, stdout=PIPE, stderr=PIPE)
        self.log.info(f"SSH tunnel is now active")
        return process
