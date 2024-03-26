#!/bin/bash
#SBATCH -J cybershuttle_kernel
{SBATCH_OPTS}

tmpfile=$(mktemp)
cat <<EOF >$tmpfile
{CONNECTION_INFO}
EOF

{ENV_VARS}
{LMOD_MODULES}
{EXEC_COMMAND}
