__version__ = "0.0.1"

import json
from os.path import dirname
from pathlib import Path

__template_dir__ = Path(dirname(__file__)) / "templates"


def jsonify(data: dict) -> str:
    data = {k: v.decode() if isinstance(v, bytes) else v for k, v in data.items()}
    return json.dumps(data, ensure_ascii=False)


from .cybershuttle import CybershuttleProvisioner
from .slurm_local import LocalSlurmProvisioner
from .slurm_remote import RemoteSlurmProvisioner
