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

### Part A - Running the Cybershuttle Gateway Server

First, run the cybershuttle gateway on remotehost

```bash
# activate environment
micromamba activate cybershuttle
# start gateway on remotehost
python -m cybershuttle_gateway --port=<gateway_server_port>
```

#### Configuring the Notebook Gateway (Admin UI)

Open `http://<gateway_server_host>:<gateway_server_port>` on a web browser. Next, click the "Add Cluster" button. This will open up a form. Provide the cluster specs in the form fields, and submit.
This will create a new cluster entry on the gateway.
Once created, the jupyterlab extension will start displaying this cluster as an option.

### Part B - Running Jupyter Lab + Cybershuttle Extension

If you installed using micromamba, both the cybershuttle extension and jupyter lab will be already installed.
```bash
# activate environment
micromamba activate cybershuttle
# start jupyter lab on localhost
python -m jupyter lab
```

You can also build and run a container from the provided Dockerfile.

```bash
docker buildx build -t cybershuttle-notebook:local .
docker run -p 8888:8888 -t cybershuttle-notebook:local

```
