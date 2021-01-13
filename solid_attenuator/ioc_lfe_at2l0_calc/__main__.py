import os
import sys

from caproto.server import ioc_arg_parser, run

from .. import util
from .at2l0 import create_ioc

################################################
FIRST_FILTER = 2
NUM_BLADES = 18


if '--production' in sys.argv:
    prefix = "AT2L0:CALC"
    eV_name = "PMPS:LFE:PE:UND:CurrentPhotonEnergy_RBV"
    pmps_run_name = "PMPS:HXR:AT2L0:RUN"  # TODO
    pmps_tdes_name = "PMPS:HXR:AT2L0:T_DES"  # TODO
    motor_prefix = "AT2L0:XTES:MMS:"  # TODO
    log_level = 'INFO'
    # autosave_path = '/reg/d/iocData/ioc-lfe-at2l0-calc/iocInfo/autosave.json'
    ioc_data = os.environ.get('IOC_DATA_AT2L0', '/reg/d/iocData/ioc-lfe-at2l0-calc/')  # noqa
    autosave_path = os.path.join(ioc_data, 'autosave.json')
    sys.argv.remove('--production')
else:
    prefix = "AT2L0:SIM"
    eV_name = "LCLS:HXR:BEAM:EV"
    pmps_run_name = "PMPS:HXR:AT2L0:RUN"
    pmps_tdes_name = "PMPS:HXR:AT2L0:T_DES"
    motor_prefix = "AT2L0:SIM:MMS:"
    autosave_path = 'autosave_development.json'
    log_level = 'DEBUG'

################################################

ioc_args = {
    "filter_group": {
        N: f'{N:02d}'
        for N in range(FIRST_FILTER, NUM_BLADES + FIRST_FILTER)
    },
}


def main():
    ioc_options, run_options = ioc_arg_parser(
        default_prefix=prefix,
        desc='Solid attenuator IOC',
        macros={
            'ev_pv': eV_name,
            'pmps_run_pv': pmps_run_name,
            'pmps_tdes_pv': pmps_tdes_name,
            'motor_prefix': motor_prefix,
            'autosave_path': autosave_path,
        }
    )

    ioc = create_ioc(**ioc_args, **ioc_options)
    util.config_logging(ioc.log, level=log_level)
    run(ioc.pvdb, **run_options)


if __name__ == '__main__':
    main()
