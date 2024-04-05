import asyncio
import signal
from typing import TYPE_CHECKING, Any, Dict, List, Literal, Optional

import traitlets
import urllib.parse
from jupyter_client.connect import KernelConnectionInfo, LocalPortCache
from jupyter_client.localinterfaces import is_local_ip, local_ips
from jupyter_client.provisioning.provisioner_base import KernelProvisionerBase

from cybershuttle_provisioners.api import CybershuttleAPI
from cybershuttle_provisioners.config import TEMPLATE_DIR


class CybershuttleProvisioner(KernelProvisionerBase):
    """
    Provision a Kernel via Cybershuttle REST API

    ---------------------------------------------
    [App @ Local]              | Cybershuttle API
    ---------------------------------------------
    submit job                 |-> runs a kernel
    app ports                <-| kernel ports

    """

    job_id = None
    job_state: Literal["UNKNOWN", "PENDING", "RUNNING"] = "UNKNOWN"
    awaiting_shutdown = False
    exec_node = None
    proc_portfwd = None
    num_retries = 0

    max_retries: int = 100
    ports_cached = False

    gateway_url: str = traitlets.Unicode(config=True)  # type: ignore
    cluster: str = traitlets.Unicode(config=True)  # type: ignore
    transport: str = traitlets.Unicode(config=True)  # type: ignore
    spec: dict = traitlets.Dict(config=True)  # type: ignore
    username: str = traitlets.Unicode(config=True)  # type: ignore
    template_dir = TEMPLATE_DIR
    fwd_ports = ["shell_port", "iopub_port", "stdin_port", "hb_port", "control_port"]

    def _reset_state(self):
        self.job_id = None
        self.job_state = "UNKNOWN"
        self.awaiting_shutdown = False
        self.exec_node = None
        self.proc_portfwd = None
        self.num_retries = 0

    @property
    def has_process(self) -> bool:
        """
        Returns true if this provisioner is currently managing a process.

        This property is asserted to be True immediately following a call to
        the provisioner's :meth:`launch_kernel` method.
        """
        return self.job_id is not None

    async def poll(self) -> Optional[int]:
        """
        Checks if kernel process is still running.

        If running, None is returned, otherwise the process's integer-valued exit code is returned.
        This method is called from :meth:`KernelManager.is_alive`.
        """

        # return exit code 0 if no process exists
        if not self.has_process:
            return 0

        # poll for job state
        assert self.job_id is not None
        state, node, eta, ports = self.api.poll_job_status(self.job_id)

        # case 1 - running state
        if state == "RUNNING":
            self.job_state = "RUNNING"
            self.exec_node = node
            self.log.debug(f"job {self.job_id} is RUNNING. NODE={self.exec_node}")
            # at this point both exec_node and connection_info must exist
            assert self.exec_node is not None
            assert self.connection_info is not None
            
            # NOTE not needed when connection_info is directly updated with gateway ip/ports
            # if self.proc_portfwd is None:
                # start port forwarding process
                # assert self.exec_node is not None
                # self.proc_portfwd = self.api.start_forwarding(job_id=self.job_id)
                # self.log.info(f"Started forwarding from gateway server to localhost")
            
            return None

        # case 2 - pending state
        if state == "PENDING":
            self.job_state = "PENDING"
            self.log.debug(f"job {self.job_id} is PENDING. NODE={self.exec_node}, ETA={eta}")
            return None

        # case 3 - error state
        if state == "ERROR":
            return 1

        # case 4 - complet-ing/ed state
        if self.awaiting_shutdown and state in ["COMPLETING", "COMPLETED", "UNKNOWN"]:
            self.job_state = "UNKNOWN"
            return 0

        # fallback - unknown state
        # give some time for job to show up in squeue
        if self.num_retries < self.max_retries:
            self.num_retries += 1
            self.log.warn(
                f"[{self.num_retries}/{self.max_retries}] Job {self.job_id} not in squeue. using state=PENDING"
            )
            self.job_state = "PENDING"
            return None
        else:
            self.log.warn(
                f"[{self.num_retries}/{self.max_retries}] Job {self.job_id} not in squeue. using state=UNKNOWN"
            )
            self.num_retries = 0
            self.job_state = "UNKNOWN"
            return 1

    async def wait(self) -> Optional[int]:
        """
        Waits for kernel process to terminate.

        This method is called from `KernelManager.finish_shutdown()` and
        `KernelManager.kill_kernel()` when terminating a kernel gracefully or
        immediately, respectively.

        """
        ret = 0
        if self.awaiting_shutdown:
            # Use busy loop at 1 second intervals, polling until the process is
            # not alive.  If we find the process is no longer alive, complete
            # its cleanup via the blocking wait().  Callers are responsible for
            # issuing calls to wait() using a timeout (see kill()).
            while await self.poll() is None:  # type:ignore[unreachable]
                await asyncio.sleep(5.0)

        # job is no longer alive, finish forwarding process
        if self.proc_portfwd is not None:
            self.proc_portfwd.terminate()
            self.log.info(f"Stopped forwarding from gateway server to localhost")
            ret = 0
            # Make sure all the fds get closed.
            for attr in ["stdout", "stderr", "stdin"]:
                fid = getattr(self.proc_portfwd, attr)
                if fid:
                    fid.close()

        # allow has_process to now return False
        self.awaiting_shutdown = False

        return ret

    async def send_signal(self, signum: int) -> None:
        """
        Sends signal identified by signum to the kernel process.

        This method is called from `KernelManager.signal_kernel()` to send the
        kernel process a signal.
        """
        if signum == 0:
            # no signal sent, just error checking
            await self.poll()
        else:
            assert self.job_id is not None
            self.api.signal_job(self.job_id, signum)

    async def kill(self, restart: bool = False) -> None:
        """
        Kill the kernel process.

        This is typically accomplished via a SIGKILL signal, which cannot be caught.
        This method is called from `KernelManager.kill_kernel()` when terminating
        a kernel immediately.

        restart is True if this operation will precede a subsequent launch_kernel request.
        """
        if self.job_state == "RUNNING":
            await self.send_signal(signal.SIGKILL)

    async def terminate(self, restart: bool = False) -> None:
        """
        Terminates the kernel process.

        This is typically accomplished via a SIGTERM signal, which can be caught, allowing
        the kernel provisioner to perform possible cleanup of resources.  This method is
        called indirectly from `KernelManager.finish_shutdown()` during a kernel's
        graceful termination.

        restart is True if this operation precedes a start launch_kernel request.
        """
        if self.job_state == "RUNNING":
            await self.send_signal(signal.SIGTERM)

    async def launch_kernel(self, cmd: List[str], **kwargs: Any) -> KernelConnectionInfo:
        """
        Launch the kernel process and return its connection information.

        This method is called from `KernelManager.launch_kernel()` during the
        kernel manager's start kernel sequence.
        """

        # reset state variables
        self._reset_state()

        # launch kernel
        self.job_id = self.api.launch_job(self.job_config)

        # get ports
        while True:
            state, node, eta, ports = self.api.poll_job_status(self.job_id)
            if state != "RUNNING":
                await asyncio.sleep(5.0)
            else:
                break

        # update connection info with new ip / ports
        patch = {}
        patch["ip"] = urllib.parse.urlparse(str(self.job_config.get("gateway_url"))).netloc
        for i, name in enumerate(self.fwd_ports):
            patch[name] = ports[i][1]
        self.connection_info.update(patch)
        self.log.info("updated connection info: %s", self.connection_info)

        return self.connection_info

    async def cleanup(self, restart: bool = False) -> None:
        """
        Cleanup any resources allocated on behalf of the kernel provisioner.

        This method is called from `KernelManager.cleanup_resources()` as part of
        its shutdown kernel sequence.

        restart is True if this operation precedes a start launch_kernel request.
        """
        if self.ports_cached and not restart:
            # provisioner is about to be destroyed, return cached ports
            lpc = LocalPortCache.instance()
            ports = (
                self.connection_info["shell_port"],
                self.connection_info["iopub_port"],
                self.connection_info["stdin_port"],
                self.connection_info["hb_port"],
                self.connection_info["control_port"],
            )
            for port in ports:
                if TYPE_CHECKING:
                    assert isinstance(port, int)
                lpc.return_port(port)

    async def shutdown_requested(self, restart: bool = False) -> None:
        """
        Allows the provisioner to determine if the kernel's shutdown has been requested.

        This method is called from `KernelManager.request_shutdown()` as part of
        its shutdown sequence.

        This method is optional and is primarily used in scenarios where the provisioner
        may need to perform other operations in preparation for a kernel's shutdown.
        """
        self.awaiting_shutdown = True

    async def pre_launch(self, **kwargs: Any) -> Dict[str, Any]:
        """
        Perform any steps in preparation for kernel process launch.

        This includes applying additional substitutions to the kernel launch command
        and environment. It also includes preparation of launch parameters.

        NOTE: Subclass implementations are advised to call this method as it applies
        environment variable substitutions from the local environment and calls the
        provisioner's :meth:`_finalize_env()` method to allow each provisioner the
        ability to cleanup the environment variables that will be used by the kernel.

        This method is called from `KernelManager.pre_start_kernel()` as part of its
        start kernel sequence.

        Returns the (potentially updated) keyword arguments that are passed to
        :meth:`launch_kernel()`.
        """

        # This should be considered temporary until a better division of labor can be defined.
        km = self.parent
        if km:
            if km.transport == "tcp" and not is_local_ip(km.ip):
                msg = (
                    "Can only launch a kernel on a local interface. "
                    f"This one is not: {km.ip}."
                    "Make sure that the '*_address' attributes are "
                    "configured properly. "
                    f"Currently valid addresses are: {local_ips()}"
                )
                raise RuntimeError(msg)
            # build the Popen cmd
            extra_arguments = kwargs.pop("extra_arguments", [])

            # write connection file / get default ports
            # TODO - change when handshake pattern is adopted
            if km.cache_ports and not self.ports_cached:
                lpc = LocalPortCache.instance()
                km.shell_port = lpc.find_available_port(km.ip)
                km.iopub_port = lpc.find_available_port(km.ip)
                km.stdin_port = lpc.find_available_port(km.ip)
                km.hb_port = lpc.find_available_port(km.ip)
                km.control_port = lpc.find_available_port(km.ip)
                self.ports_cached = True
            if "env" in kwargs:
                jupyter_session = kwargs["env"].get("JPY_SESSION_NAME", "")
                km.write_connection_file(jupyter_session=jupyter_session)
            else:
                km.write_connection_file()
            self.connection_info = km.get_connection_info()

            kernel_cmd = km.format_kernel_cmd(extra_arguments=extra_arguments)  # This needs to remain here for b/c
        else:
            extra_arguments = kwargs.pop("extra_arguments", [])
            kernel_cmd = self.kernel_spec.argv + extra_arguments

        # basic kernelspec checks
        if not self.gateway_url:
            raise RuntimeError("kernelspec is missing the cybershuttle gateway url.")
        if not self.transport:
            raise RuntimeError("kernelspec is missing the transport type.")
        if not self.cluster:
            raise RuntimeError("kernelspec is missing the cluster name.")
        if not self.spec:
            raise RuntimeError("kernelspec is missing the job specification.")
        if not self.username:
            raise RuntimeError(f"kernelspec is missing the username.")

        # create provisioner api
        self.api = CybershuttleAPI(logger=self.log, url=self.gateway_url, username=self.username)

        # build job config
        self.job_config = dict(
            username=self.username,
            gateway_url=self.gateway_url,
            cluster=self.cluster,
            transport=self.transport,
            spec=self.spec,
            connection_info=self.connection_info,
        )

        return await super().pre_launch(cmd=kernel_cmd, **kwargs)

    def get_shutdown_wait_time(self, recommended: float = 60) -> float:
        return 60

    def get_stable_start_time(self, recommended: float = 60) -> float:
        return 120
