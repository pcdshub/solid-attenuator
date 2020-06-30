from caproto.server import pvproperty, PVGroup, ioc_arg_parser, run
from caproto.threading import pyepics_compat as epics
from caproto import ChannelType
import numpy as np

from db.filters import FilterGroup
from db.system import SystemGroup


class IOCMain(PVGroup):
    """
    """
    def __init__(self,
                 prefix,
                 *,
                 groups,
                 abs_data,
                 config_data,
                 eV,
                 pmps_run,
                 **kwargs):
        super().__init__(prefix, **kwargs)
        self.groups=groups
        self.config_data = config_data
        self.startup()

    def startup(self):
        self.config_table = self.load_configs(self.config_data)

    def load_configs(self, config_data):
        print("Loading configurations...")
        self.config_table = np.asarray(config_data['configurations'])
        print("Configurations successfully loaded.")
        return self.config_table


def create_ioc(prefix, filter_group, eV_pv, pmps_run_pv,
               config_data, absorption_data, **ioc_options):
    groups = {}
    ioc = IOCMain(prefix=prefix,
                  groups=groups,
                  abs_data=absorption_data,
                  config_data=config_data,
                  eV=eV_pv,
                  pmps_run=pmps_run_pv,
                  **ioc_options)

    for group_prefix in filter_group:
        groups[group_prefix] = FilterGroup(
            f'{prefix}:FILTER:{group_prefix}:',
            abs_data=absorption_data,
            eV=epics.get_pv(eV_pv, auto_monitor=True),
            ioc=ioc)

    groups['SYS'] = SystemGroup(f'{prefix}:SYS:', ioc=ioc)

    for group in groups.values():
        ioc.pvdb.update(**group.pvdb)

    return ioc
