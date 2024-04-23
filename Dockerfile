FROM mambaorg/micromamba

COPY --chown=$MAMBA_USER:$MAMBA_USER environment_docker.yml /tmp/env.yaml

RUN micromamba install -y -n base -f /tmp/env.yaml && micromamba clean --all --yes

EXPOSE 8888

CMD ["jupyter", "lab", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--allow-root"]