import os
import sys

from caproto.server import expand_macros, ioc_arg_parser, run

from .. import util
from ..sxr import create_ioc

FIRST_FILTER = 1
NUM_BLADES = 4


if '--production' in sys.argv:
    subsystem = 'CALC'
    eV_name = "PMPS:KFE:PE:UND:CurrentPhotonEnergy_RBV"
    pmps_run_name = "PMPS:SXR:{system}:RUN"  # TODO
    pmps_tdes_name = "PMPS:SXR:{system}:T_DES"  # TODO
    motor_prefix = "{system}:L2SI:MMS:"  # TODO
    log_level = 'INFO'
    # autosave_path = '/reg/d/iocData/ioc-lfe-at1k4-calc/iocInfo/autosave.json'
    # TODO: wrong env var here; this method is not great:
    ioc_data = os.environ.get('IOC_DATA_{system}', '/reg/d/iocData/ioc-lfe-at1k4-calc/')  # noqa
    # autosave_path = os.path.join(ioc_data, 'autosave.json')
    autosave_path = 'autosave_development.json'
    sys.argv.remove('--production')
else:
    subsystem = 'SIM'
    eV_name = "LCLS:SXR:BEAM:EV"
    pmps_run_name = "PMPS:SXR:{system}:RUN"
    pmps_tdes_name = "PMPS:SXR:{system}:T_DES"
    motor_prefix = "{system}:SIM:MMS:"
    autosave_path = 'autosave_development.json'
    log_level = 'DEBUG'


def main():
    ioc_options, run_options = ioc_arg_parser(
        default_prefix="{system}:{subsystem}",
        desc='Solid attenuator IOC',
        macros={
            'system': 'AT1K4',
            'subsystem': subsystem,
        },
    )

    macros = ioc_options['macros']
    ioc = create_ioc(
        **ioc_options,
        filter_group={
            N: f'{N:02d}'
            for N in range(FIRST_FILTER, NUM_BLADES + FIRST_FILTER)
        },
        eV_pv=expand_macros(eV_name, macros),
        pmps_run_pv=expand_macros(pmps_run_name, macros),
        pmps_tdes_pv=expand_macros(pmps_tdes_name, macros),
        motor_prefix=expand_macros(motor_prefix, macros),
        autosave_path=expand_macros(autosave_path, macros),
    )

    util.config_logging(ioc.log, level=log_level)
    run(ioc.pvdb, **run_options)


if __name__ == '__main__':
    main()
