__version__ = "0.0.1"

import json
from os.path import dirname
from pathlib import Path

TEMPLATE_DIR = Path(dirname(__file__)) / "templates"


def jsonify(data: dict) -> str:
    data = {k: v.decode() if isinstance(v, bytes) else v for k, v in data.items()}
    return json.dumps(data, ensure_ascii=False)


from cybershuttle_provisioners.cybershuttle import CybershuttleProvisioner
from cybershuttle_provisioners.slurm_local import LocalSlurmProvisioner
from cybershuttle_provisioners.slurm_remote import RemoteSlurmProvisioner
