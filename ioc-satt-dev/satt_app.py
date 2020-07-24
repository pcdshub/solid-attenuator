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
        self.monitor_pvnames = dict(
            ev=eV,
            pmps_run=pmps_run,
            pmps_tdes=pmps_tdes,
        )

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
        for f in range(1,len(self.filter_group)+1):
            is_stuck = self.filter(f).is_stuck.value
            if is_stuck != "True":
                tN = self.filter(f).transmission.value
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
        for f in range(1,len(self.filter_group)+1):
            is_stuck = self.filter(f).is_stuck.value
            if is_stuck != "True":
                tN = self.filter(f).transmission_3omega.value
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
        for f in range(N):
            is_stuck = self.filter(f+1).is_stuck.value
            if is_stuck == "True":
                T_arr[f] = np.nan
            else:
                T_arr[f] = self.filter(f+1).transmission.value
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
        filter configurations.
        """
        if not T_des:
            T_des = self.sys.t_desired.value

        # Basis vector of all filter transmission values.
        # Note: Stuck filters have transmission of `NaN`.
        T_basis = self.all_transmissions()

        # Table of transmissions for all configurations
        # is obtained by multiplying basis by
        # configurations in/out state matrix.
        T_table = np.nanprod(T_basis*self.config_table,
                             axis=1)

        # Create a table of configurations and their associated
        # beam transmission values, sorted by transmission value.
        T_config_table = np.asarray(sorted(np.transpose([T_table[:],
                                    range(len(self.config_table))]),
                                           key=lambda x: x[0]))

        # Find the index of the filter configuration which
        # minimizes the differences between the desired
        # and closest achievable transmissions.
        i = np.argmin(np.abs(T_config_table[:,0]-T_des))

        # Obtain the optimal filter configuration and its transmission.
        closest = self.config_table[int(T_config_table[i,1])]
        T_closest = np.nanprod(T_basis*closest)

        # Determine the optimal configurations for "best highest"
        # and "best lowest" achievable transmissions.
        if T_closest == T_des:
            # The optimal configuration achieves the desired
            # transmission exactly.
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
        Return the optimal floor (lower than desired transmission)
        or ceiling (higher than desired transmission) configuration
        based on the current mode setting.
        """
        if not T_des:
            T_des = self.sys.t_desired.value
        mode = self.sys.mode.value
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


def create_ioc(prefix,
               *,
               eV_pv,
               pmps_run_pv,
               pmps_tdes_pv,
               filter_group,
               absorption_data,
               config_data,
               **ioc_options):
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
    ioc.sys = ioc.groups['SYS']

    for group in ioc.groups.values():
        ioc.pvdb.update(**group.pvdb)

    return ioc
