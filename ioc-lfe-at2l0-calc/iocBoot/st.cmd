#!/usr/bin/env bash

PREFIX=
TOP="$(dirname "$0")"/../../
ATT_CONFIG_PATH=${TOP}
export EPICS_CA_AUTO_ADDR_LIST=NO
export EPICS_CA_ADDR_LIST=172.21.91.255
IOC_DATA_SATT=/reg/d/iocData/ioc-lfe-satt

unset LD_LIBRARY_PATH
unset PYTHONPATH

##########################################
# currently unused:
# export PCDS_CONDA_VER='3.2.0'
source /reg/g/pcds/pyps/conda/pcds_conda

CONDA_ENV=/reg/g/pcds/epics-dev/klauer/hxr-attenuator-conda-env
##########################################

cd ${TOP}

conda activate $CONDA_ENV
python --version
python -m ioc-lfe-at2l0-calc --production --list-pvs
