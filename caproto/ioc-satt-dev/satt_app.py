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
                 pmps_tdes,
                 **kwargs):
        super().__init__(prefix, **kwargs)
        self.filter_group = filter_group
        self.groups = groups
        self.config_data = config_data
        self.startup()
        self.eV = epics.get_pv(eV, auto_monitor=True)
        self.pmps_run = epics.get_pv(pmps_run, auto_monitor=True)
        self.pmps_tdes = epics.get_pv(pmps_tdes, auto_monitor=True)

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
            tN = self.groups[f'{group}'].pvdb[
                f'{self.prefix}:FILTER:{group}:T'
            ].value
            t *= tN
        return t

    def t_calc_3omega(self):
        t = 1.
        for group in self.filter_group:
            tN = self.groups[f'{group}'].pvdb[
                f'{self.prefix}:FILTER:{group}:T_3OMEGA'
            ].value
            t *= tN
        return t

    def all_transmissions(self):
        N = len(self.filter_group)
        T_arr = np.ones(N)
        # TODO: check if filter is stuck...
        # If so, replace with NaN.
        for i in range(N):
            group = str(i+1).zfill(2)
            T_arr[i] = self.filter(i+1).pvdb[
                f'{self.prefix}:FILTER:{group}:T'
            ].value
        return T_arr

    def filter(self, i):
        group = str(i).zfill(2)
        return self.groups[f'{group}']

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


def create_ioc(prefix, *, eV_pv, pmps_run_pv, pmps_tdes_pv, filter_group, absorption_data, config_data, **ioc_options):
    groups = {}
    ioc = IOCMain(prefix=prefix,
                  filter_group=filter_group,
                  groups=groups,
                  abs_data=absorption_data,
                  config_data=config_data,
                  eV=eV_pv,
                  pmps_run=pmps_run_pv,
                  pmps_tdes=pmps_tdes_pv,
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
