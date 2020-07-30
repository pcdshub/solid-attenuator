import sys

from caproto.server import ioc_arg_parser, run

from .db import util
from .satt_app import create_ioc

################################################
NUM_BLADES = 18
if '--production' in sys.argv:
    prefix = "AT2L0:CALC"
    eV_name = "PMPS:LFE:PE:UND:CurrentPhotonEnergy_RBV"
    pmps_run_name = "PMPS:HXR:AT2L0:RUN"  # TODO
    pmps_tdes_name = "PMPS:HXR:AT2L0:T_DES"  # TODO
    log_level = 'INFO'
    sys.argv.remove('--production')
else:
    prefix = "AT2L0:SIM"
    eV_name = "LCLS:HXR:BEAM:EV"
    pmps_run_name = "PMPS:HXR:AT2L0:RUN"
    pmps_tdes_name = "PMPS:HXR:AT2L0:T_DES"
    log_level = 'DEBUG'

################################################

ioc_args = {
    "filter_group": {N: str(N).zfill(2)
                     for N in range(1, NUM_BLADES + 1)},
    "eV_pv": eV_name,
    "pmps_run_pv": pmps_run_name,
    "pmps_tdes_pv": pmps_tdes_name
}


if __name__ == '__main__':
    ioc_options, run_options = ioc_arg_parser(
        default_prefix=prefix,
        desc='Solid attenuator IOC')

    ioc = create_ioc(**ioc_args, **ioc_options)
    util.config_logging(ioc.log, level=log_level)
    run(ioc.pvdb, **run_options)
