#!/usr/bin/env bash

PREFIX="AT2L0:SIM"
TOP=../
ATT_CONFIG_PATH=${TOP}

unset LD_LIBRARY_PATH
unset PYTHONPATH

##########################################
# use Raj's env for development
export PCDS_CONDA_VER='3.2.0'
source /reg/g/pcds/pyps/conda/pcds_conda

PYDEV=/reg/neh/home/rajan-01/pydev
export PATH="${PYDEV}/bin:${PATH}"
export PYTHONPATH="${PYDEV}:${PYTHONPATH}"
##########################################

cd "$(dirname "$0")"
python --version
python ${TOP}main.py --prefix ${PREFIX} --list-pvs
