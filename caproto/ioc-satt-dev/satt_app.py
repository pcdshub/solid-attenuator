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
                 filter_group,
                 groups,
                 abs_data,
                 config_data,
                 eV,
                 pmps_run,
                 **kwargs):
        super().__init__(prefix, **kwargs)
        self.filter_group = filter_group
        self.groups = groups
        self.config_data = config_data
        self.startup()
        self.eV = epics.get_pv(eV, auto_monitor=True)
        
    def startup(self):
        self.config_table = self.load_configs(self.config_data)

    def load_configs(self, config_data):
        print("Loading configurations...")
        self.config_table = np.asarray(config_data['configurations'])
        print("Configurations successfully loaded.")
        return self.config_table

    def t_calc(self):
        t = 1.
        for group in self.filter_group:
            tfilter = self.groups[f'{group}'].pvdb[f'{self.prefix}:FILTER:{group}:T'].value
            t *= tfilter
        return t

    def calc_closest_eV(self, eV, table, eV_min, eV_max, eV_inc):
        i = int(np.rint((eV - eV_min)/eV_inc))
        if i < 0:
            i = 0 # Use lowest tabulated value.
        if i > table.shape[0]:
            i = -1 # Use greatest tabulated value.
        closest_eV = table[i,0]
        return closest_eV, i

    def transmission_value_error(value):
        if value < 0 or value > 1:
            raise ValueError('Transmission must be '
                         +'between 0 and 1.')

def create_ioc(prefix, filter_group, eV_pv, pmps_run_pv,
               config_data, absorption_data, **ioc_options):
    groups = {}
    ioc = IOCMain(prefix=prefix,
                  filter_group=filter_group,
                  groups=groups,
                  abs_data=absorption_data,
                  config_data=config_data,
                  eV=eV_pv,
                  pmps_run=pmps_run_pv,
                  **ioc_options)

    for group_prefix in filter_group:
        ioc.groups[group_prefix] = FilterGroup(
            f'{prefix}:FILTER:{group_prefix}:',
            abs_data=absorption_data,
            ioc=ioc)

    ioc.groups['SYS'] = SystemGroup(f'{prefix}:SYS:', ioc=ioc)

    for group in ioc.groups.values():
        ioc.pvdb.update(**group.pvdb)

    return ioc
