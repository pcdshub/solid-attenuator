from caproto.server import ioc_arg_parser, run

from .db import util
from .satt_app import IOCMain, create_ioc

################################################
prefix = "AT2L0:SIM"
num_blades = 18
eV_name = "LCLS:HXR:BEAM:EV"
pmps_run_name = "PMPS:HXR:AT2L0:RUN"
pmps_tdes_name = "PMPS:HXR:AT2L0:T_DES"
################################################

ioc_args = {
    "filter_group": {N: str(N).zfill(2)
                     for N in range(1, num_blades + 1)},
    "eV_pv": eV_name,
    "pmps_run_pv": pmps_run_name,
    "pmps_tdes_pv": pmps_tdes_name
}


if __name__ == '__main__':
    ioc_options, run_options = ioc_arg_parser(
        default_prefix=prefix,
        desc=IOCMain.__doc__)

    ioc = create_ioc(**ioc_args, **ioc_options)
    util.config_logging(ioc.log, level='DEBUG')
    run(ioc.pvdb, **run_options)
