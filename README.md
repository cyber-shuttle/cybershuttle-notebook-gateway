# Cybershuttle Notebook Gateway

## Installation

```bash
# clone the repository
git clone git@github.com:cyber-shuttle/cybershuttle-notebook-gateway.git
# cd into project directory
cd cybershuttle-notebook-gateway/
# install micromamba (recommended)
"${SHELL}" <(curl -L https://micro.mamba.pm/install.sh)
# create an environment with python 3.10
micromamba env create -n cybershuttle --file environment.yml
# activate environment
micromamba activate cybershuttle
```

### Running the Project

```bash
# start the cybershuttle gateway
python -m cybershuttle_gateway
# start jupyter lab
python -m jupyter lab
```

### Adding New Kernels

```bash
# cd to jupyter kernel directory
cd $HOME/.local/share/jupyter/kernels
# create new kernel
mkdir <kernel_name>
# add kernel.json script
touch <kernel_name>/kernel.json
```

### Example for kernel.json
```json
{
  "argv": ["ipython", "kernel", "-f", "{connection_file}"],
  "display_name": "cybershuttle",
  "env": {},
  "language": "python",
  "metadata": {
    "kernel_provisioner": {
      "config": {
        "gateway_url": "http://localhost:9000",
        "method": "slurm",
        "transport": "zmq",
        "loginnode": "<hostname_of_login_node>",
        "proxyjump": "",
        "lmod_modules": [],
        "sbatch_flags": {
          "cpus-per-task": "4",
          "gres": "gpu:1",
          "mem": "32G",
          "partition": "gpu",
          "time": "01:00:00"
        },
        "username": "<username>"
      },
      "provisioner_name": "cybershuttle"
    }
  }
}
```