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
        self.prefix = prefix
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
        """
        Load HDF5 table of filter state combinations.
        """
        print("Loading configurations...")
        self.config_table = np.asarray(config_data['configurations'])
        print("Configurations successfully loaded.")
        return self.config_table

    def t_calc(self):
        """
        Total transmission through all filter blades.
        Stuck blades are assumed to be 'OUT' and thus 
        the total transmission will be overestimated
        (in the case any blades are actually stuck 'IN').
        """
        t = 1.
        for group in self.filter_group:
            is_stuck = self.groups[f'{group}'].pvdb[
                f'{self.prefix}:FILTER:{group}:IS_STUCK'
            ].value
            if is_stuck != "True":
                tN = self.groups[f'{group}'].pvdb[
                    f'{self.prefix}:FILTER:{group}:T'
                ].value
                t *= tN
        return t

    def t_calc_3omega(self):
        """
        Total 3rd harmonic transmission through all filter
        blades. Stuck blades are assumed to be 'OUT' and thus 
        the total transmission will be overestimated
        (in the case any blades are actually stuck 'IN').
        """
        t = 1.
        for group in self.filter_group:
            is_stuck = self.groups[f'{group}'].pvdb[
                f'{self.prefix}:FILTER:{group}:IS_STUCK'
            ].value
            if is_stuck != "True":
                tN = self.groups[f'{group}'].pvdb[
                    f'{self.prefix}:FILTER:{group}:T_3OMEGA'
                ].value
                t *= tN
        return t

    def all_transmissions(self):
        """
        Return an array of the transmission values
        for each filter at the current photon energy.
        Stuck filters get a transmission of NaN, which
        omits them from calculations/considerations.
        """
        N = len(self.filter_group)
        T_arr = np.ones(N)
        for i in range(N):
            group = str(i+1).zfill(2)
            is_stuck = self.filter(i+1).pvdb[
                f'{self.prefix}:FILTER:{group}:IS_STUCK'
            ].value
            if is_stuck == "True":
                T_arr[i] = np.nan
            else:
                T_arr[i] = self.filter(i+1).pvdb[
                    f'{self.prefix}:FILTER:{group}:T'
                ].value
        print(T_arr)
        return T_arr

    def filter(self, i):
        """
        Return a filter PVGroup at index i.
        """
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

    def find_configs(self, T_des=None):
        """
        Find the optimal configurations for attaining
        desired transmission ``T_des`` at the 
        current photon energy.  

        Returns configurations which yield closest
        highest and lowest transmissions and their 
        transmission values.
        """
        if not T_des:
            T_des = self.groups['SYS'].pvdb[f'{self.prefix}:SYS:T_DES'].value

        T_basis = self.all_transmissions()
        T_table = np.nanprod(T_basis*self.config_table,
                             axis=1)
        T_config_table = np.asarray(sorted(np.transpose([T_table[:],
                                    range(len(self.config_table))]),
                                           key=lambda x: x[0]))
        i = np.argmin(np.abs(T_config_table[:,0]-T_des))
        closest = self.config_table[int(T_config_table[i,1])]
        T_closest = np.nanprod(T_basis*closest)

        if T_closest == T_des:
            config_bestHigh = config_bestLow = closest
            T_bestHigh = T_bestLow = T_closest

        if T_closest < T_des:
            config_bestHigh = self.config_table[int(T_config_table[i+1,1])]
            config_bestLow = closest
            T_bestHigh = np.nanprod(T_basis*config_bestHigh)
            T_bestLow = T_closest

        if T_closest > T_des:
            config_bestHigh = closest.astype(np.int)
            config_bestLow = self.config_table[int(T_config_table[i-1,1])]
            T_bestHigh = T_closest
            T_bestLow = np.nanprod(T_basis*config_bestLow)

        return np.nan_to_num(config_bestLow).astype(np.int), np.nan_to_num(config_bestHigh).astype(np.int), T_bestLow, T_bestHigh

    def get_config(self, T_des=None):
        """
        Return the optimal floor or ceiling configuration
        based on the current mode setting.
        """
        if not T_des:
            T_des = self.groups['SYS'].pvdb[f'{self.prefix}:SYS:T_DES'].value
        mode = self.groups['SYS'].pvdb[f'{self.prefix}:SYS:MODE'].value
        config_bestLow, config_bestHigh, T_bestLow, T_bestHigh = self.find_configs()
        if mode == "Floor":
            return config_bestLow, T_bestLow, T_des
        else:
            return config_bestHigh, T_bestHigh, T_des

    def print_config(self, w=80):
        """
        Format and print the optimal configuration.
        """
        config, T_best, T_des = self.get_config()
        print("="*w)
        print("Desired transmission value: {}".format(T_des))
        print("-"*w)
        print("Best possible transmission value: {}".format(T_best))
        print("-"*w)
        print(config.astype(np.int))
        print("="*w)
        
def create_ioc(prefix, *, eV_pv, pmps_run_pv, pmps_tdes_pv, filter_group, absorption_data, config_data, **ioc_options):
    """
    IOC Setup.
    """
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
