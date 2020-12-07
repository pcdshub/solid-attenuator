#!/usr/bin/env bash

PREFIX=
TOP="$(dirname "$0")"/../../
ATT_CONFIG_PATH=${TOP}
export EPICS_CA_AUTO_ADDR_LIST=NO
export EPICS_CA_ADDR_LIST=172.21.91.255

# export IOC_DATA_AT2L0=/reg/d/iocData/ioc-lfe-at2l0-calc
export IOC_DATA_AT2L0=/reg/g/pcds/epics-dev/klauer/hxr-attenuator/ioc-lfe-at2l0-calc/iocBoot/iocData/
export LOG_FILE_PATH=${IOC_DATA_AT2L0}/ioc.log

unset LD_LIBRARY_PATH
unset PYTHONPATH

##########################################
# currently unused:
# export PCDS_CONDA_VER='3.2.0'
source /reg/g/pcds/pyps/conda/pcds_conda

CONDA_ENV=/reg/g/pcds/epics-dev/klauer/hxr-attenuator-conda-env
##########################################

run_ioc() {
    conda activate $CONDA_ENV
    echo ""
    echo "* Running the IOC..."
    set -ex
    cd ${TOP}
    python --version
    python `which ioc-lfe-at2l0-calc` --production --list-pvs
}

(run_ioc 2>&1) | tee --append $LOG_FILE_PATH
