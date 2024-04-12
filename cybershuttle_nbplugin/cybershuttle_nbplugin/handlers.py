import json
import os
import uuid
from pathlib import Path

import requests
import tornado
from jupyter_server.base.handlers import APIHandler
from jupyter_server.utils import url_path_join

"""
this is what the json body should look like

input_data = {
    "cluster": "gkeyll",
    "language": "python",
    "spec": {"cpus-per-task": 1, "time": "01:00:00"},
    "username": "yasith",
    "workdir": "/export",
}
"""


class RouteHandler(APIHandler):

    gateway_url = "http://74.235.88.134"

    @tornado.web.authenticated
    def get(self):
        user = self.get_query_argument("user")
        res = requests.get(f"{self.gateway_url}/kernelspecs?user={user}")
        self.finish(json.dumps(res.json()))

    @tornado.web.authenticated
    def post(self):

        input_data = self.get_json_body()

        # validate input_data
        if input_data is None:
            self.send_error(400)
        assert input_data is not None

        # create kernel json
        kernelspec = {
            "argv": ["{connection_info}"],
            "display_name": input_data["cluster"],
            "env": {},
            "language": input_data["language"],
            "metadata": {
                "kernel_provisioner": {
                    "config": {
                        "cluster": input_data["cluster"],
                        "gateway_url": self.gateway_url,
                        "spec": input_data["spec"],
                        "transport": "zmq",
                        "username": input_data["username"],
                        "workdir": input_data["workdir"],
                    },
                    "provisioner_name": "cybershuttle",
                }
            },
        }

        # save kernelspec in local directory with uuid
        path = Path(os.path.expanduser("~/.local/share/jupyter/kernels"))

        # hardcode kernel name to "<cluster_name>" to avoid 100s of kernespecs
        kernel_uuid = input_data["cluster"]

        (path / kernel_uuid).mkdir(exist_ok=True)

        with open(path / kernel_uuid / "kernel.json", "w") as f:
            json.dump(kernelspec, f)

        # return uuid to start the kernel
        self.finish(json.dumps({"name": kernel_uuid}))


def setup_handlers(web_app):
    host_pattern = ".*$"

    base_url = web_app.settings["base_url"]
    route_pattern = url_path_join(base_url, "cybershuttle-nbplugin", "kernelspec")
    handlers = [(route_pattern, RouteHandler)]
    web_app.add_handlers(host_pattern, handlers)
