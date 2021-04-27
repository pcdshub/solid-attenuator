#!/usr/bin/env python3
"""
IOC entrypoint for AT1K4.

Also works for:

* AT2K2 (RIX, ioc-rix-at2k2-calc)

Ensure that:

* ``--autosave_path`` and other macros are appropriately customized to
  avoid shadowing PVs from other IOCs.
* For production IOCs, the ``--production`` flag is used such that the proper
  MPS PVs will be chosen, and logging debug flags will be set.
"""

import sys

from caproto.server import ioc_arg_parser, run

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
    # ioc_data = os.environ.get('IOC_DATA_SATT', '/reg/d/iocData/ioc-lfe-at1k4-calc/')  # noqa
    # autosave_path = os.path.join(ioc_data, 'autosave.json')
    autosave_path = "autosave_development.json"
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
            'ev_pv': eV_name,
            'pmps_run_pv': pmps_run_name,
            'pmps_tdes_pv': pmps_tdes_name,
            'motor_prefix': motor_prefix,
            'autosave_path': autosave_path,
        },
    )

    ioc = create_ioc(
        **ioc_options,
        filter_group={
            N: f'{N:02d}'
            for N in range(FIRST_FILTER, NUM_BLADES + FIRST_FILTER)
        },
    )

    util.config_logging(ioc.log, level=log_level)
    run(ioc.pvdb, **run_options)


if __name__ == '__main__':
    main()
