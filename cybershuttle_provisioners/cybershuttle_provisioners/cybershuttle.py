import asyncio
import signal
import urllib.parse
from typing import TYPE_CHECKING, Any, Dict, List, Literal, Optional

import traitlets
from jupyter_client.connect import KernelConnectionInfo, LocalPortCache
from jupyter_client.localinterfaces import is_local_ip, local_ips
from jupyter_client.provisioning.provisioner_base import KernelProvisionerBase

from cybershuttle_provisioners.api import CybershuttleAPI
from cybershuttle_provisioners.config import TEMPLATE_DIR

localhost = "127.0.0.1"


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

    gateway_url: str = traitlets.Unicode(config=True)  # type: ignore
    cluster: str = traitlets.Unicode(config=True)  # type: ignore
    transport: str = traitlets.Unicode(config=True)  # type: ignore
    spec: dict = traitlets.Dict(config=True)  # type: ignore
    username: str = traitlets.Unicode(config=True)  # type: ignore
    workdir: str = traitlets.Unicode(config=True)  # type: ignore
    template_dir = TEMPLATE_DIR
    fwd_ports = ["shell_port", "iopub_port", "stdin_port", "hb_port", "control_port"]
    cached_ports = None

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
        if state in ["PENDING", "CONFIGURING"]:
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
        ret: Optional[int] = 0
        if self.awaiting_shutdown:
            self.log.warning(f"cleanup(): waiting for job {self.job_id} to terminate...")
            # Use busy loop at 1 second intervals, polling until the process is
            # not alive.  If we find the process is no longer alive, complete
            # its cleanup via the blocking wait().  Callers are responsible for
            # issuing calls to wait() using a timeout (see kill()).
            while {ret := await self.poll()} is None:
                await asyncio.sleep(1.0)
            assert ret is not None

        # allow has_process to now return False
        self.log.warning(f"cleanup(): job {self.job_id} successfully terminated.")
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
        assert self.awaiting_shutdown == True
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
        assert self.awaiting_shutdown == True
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
        self.reset_connection_info()

        # launch kernel
        job_config = dict(
            username=self.username,
            workdir=self.workdir,
            gateway_url=self.gateway_url,
            cluster=self.cluster,
            transport=self.transport,
            spec=self.spec,
            connection_info=self.connection_info,
        )
        self.job_id = self.api.launch_job(job_config)

        # get ports
        while True:
            state, node, eta, ports = self.api.poll_job_status(self.job_id)
            if state != "RUNNING":
                await asyncio.sleep(5.0)
            else:
                break
        self.update_connection_info(self.gateway_url, ports, **kwargs)

        return self.connection_info

    async def cleanup(self, restart: bool = False) -> None:
        """
        Cleanup any resources allocated on behalf of the kernel provisioner.

        This method is called from `KernelManager.cleanup_resources()` as part of
        its shutdown kernel sequence.

        restart is True if this operation precedes a start launch_kernel request.
        """
        if not restart:
            # provisioner is about to be destroyed, return cached portsa
            assert self.cached_ports is not None
            lpc = LocalPortCache.instance()
            for port in self.cached_ports:
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

        extra_arguments = kwargs.pop("extra_arguments", [])
        kernel_cmd = self.kernel_spec.argv + extra_arguments

        # create provisioner api
        self.api = CybershuttleAPI(logger=self.log, url=self.gateway_url, username=self.username)

        # define cached ports to use during provisioner lifecycle
        # TODO move this port selection logic to gateway API.
        if self.cached_ports is None:
            lpc = LocalPortCache.instance()
            self.cached_ports = [
                lpc.find_available_port(localhost),
                lpc.find_available_port(localhost),
                lpc.find_available_port(localhost),
                lpc.find_available_port(localhost),
                lpc.find_available_port(localhost),
            ]

        return await super().pre_launch(cmd=kernel_cmd, **kwargs)

    def reset_connection_info(self) -> None:
        km = self.parent
        assert km is not None
        assert self.cached_ports is not None
        km.ip = localhost
        [km.shell_port, km.iopub_port, km.stdin_port, km.hb_port, km.control_port] = self.cached_ports
        self.connection_info = km.get_connection_info()
        # ensure kernelmanager is using tcp transport
        if km.transport != "tcp":
            raise RuntimeError("only tcp transport is supported")
        self.log.info("reset connection info: %s", self.connection_info)

    def update_connection_info(self, gateway_url: str, ports: list[tuple[int, int]], **kwargs) -> None:
        # point kernelmanager ip to gateway_ip
        km = self.parent
        assert km is not None
        km.ip = urllib.parse.urlparse(gateway_url).netloc.split(":")[0]

        # write returned ports to connection file
        for i, name in enumerate(self.fwd_ports):
            setattr(km, name, ports[i][1])
        if "env" in kwargs:
            jupyter_session = kwargs["env"].get("JPY_SESSION_NAME", "")
            km.write_connection_file(jupyter_session=jupyter_session)
        else:
            km.write_connection_file()
        kwargs.pop("extra_arguments", [])
        self.connection_info = km.get_connection_info()
        self.log.info("updated connection info: %s", self.connection_info)

    def get_shutdown_wait_time(self, recommended: float = 5.0) -> float:
        return 5.0

    def get_stable_start_time(self, recommended: float = 10.0) -> float:
        return 120.0
