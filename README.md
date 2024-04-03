# Cybershuttle Notebook Gateway

## Installing Dependencies

Install the required dependencies on both localhost and remotehost

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

### Running the System

First, run the cybershuttle gateway on remotehost

```bash
# activate environment
micromamba activate cybershuttle
# start gateway on remotehost
python -m cybershuttle_gateway --port=<gateway_server_port>
```

Second, run the sync daemon and jupyter lab on localhost

```bash
# activate environment
micromamba activate cybershuttle
# cd into project directory
cd cybershuttle-notebook-gateway/
# start sync daemon on localhost
python cybershuttle_nbplugin/kernel_sync_daemon.py --url=http://<gateway_server_host>:<gateway_server_port>  --kernel_dir=<jupyter_kernelspec_dir>
# start jupyter lab on localhost
python -m jupyter lab
```

**HINT**: Use ```jupyter --paths``` command to find <jupyter_kernelspec_dir>. Usually the path is ```$HOME/.local/share/jupyter/kernels```


### Creating New Kernels

Open ```http://<gateway_server_host>:<gateway_server_port>/admin``` on a web browser. Next, click the "Add Kernel" button. This will open up a form. Provide the kernel specs in the form fields, and submit.
This will create a new kernel entry on the gateway.
Now, when the kernel sync daemon requests available kernels, it will discover the new kernel.

### Example kernel.json for cybershuttle

```json
{
  "argv": ["ipython", "kernel", "-f", "{connection_file}"],
  "display_name": "cybershuttle",
  "env": {},
  "language": "python",
  "metadata": {
    "kernel_provisioner": {
      "config": {
        "gateway_url": "<gateway_server_url>",
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
