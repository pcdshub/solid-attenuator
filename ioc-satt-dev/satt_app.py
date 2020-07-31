import numpy as np
from caproto.server import PVGroup, SubGroup
from caproto.server.autosave import AutosaveHelper, RotatingFileManager

from .db import FilterGroup, SystemGroup


class IOCBase(PVGroup):
    """
    """

    num_filters = None

    def __init__(self, prefix, *, eV, pmps_run, pmps_tdes,
                 filter_index_to_attribute,
                 motors,
                 **kwargs):
        super().__init__(prefix, **kwargs)
        self.prefix = prefix
        self.filters = {idx: getattr(self, attr)
                        for idx, attr in filter_index_to_attribute.items()}
        self.monitor_pvnames = dict(
            ev=eV,
            pmps_run=pmps_run,
            pmps_tdes=pmps_tdes,
            motors=motors,
        )

    autosave_helper = SubGroup(AutosaveHelper)
    sys = SubGroup(SystemGroup, prefix=':SYS:')

    @property
    def working_filters(self):
        """
        Returns a dictionary of all filters that are in working order

        That is to say, filters that are not stuck.
        """
        return {
            idx: filt for idx, filt in self.filters.items()
            if filt.is_stuck.value != "True"
        }

    def calculate_transmission(self):
        """
        Total transmission through all filter blades.

        Stuck blades are assumed to be 'OUT' and thus the total transmission
        will be overestimated (in the case any blades are actually stuck 'IN').
        """
        t = 1.
        for filt in self.working_filters.values():
            t *= filt.transmission.value
        return t

    def calculate_transmission_3omega(self):
        """
        Total 3rd harmonic transmission through all filter blades.

        Stuck blades are assumed to be 'OUT' and thus the total transmission
        will be overestimated (in the case any blades are actually stuck 'IN').
        """
        t = 1.
        for filt in self.working_filters.values():
            t *= filt.transmission_3omega.value
        return t

    @property
    def all_transmissions(self):
        """
        Return an array of the transmission values for each filter at the
        current photon energy.

        Stuck filters get a transmission of NaN, which omits them from
        calculations/considerations.
        """
        T_arr = np.zeros(len(self.filters)) * np.nan
        for idx, filt in self.working_filters.items():
            T_arr[idx - 1] = filt.transmission.value
        return T_arr


def create_ioc(prefix,
               *,
               eV_pv,
               motor_prefix,
               pmps_run_pv,
               pmps_tdes_pv,
               filter_group,
               autosave_path,
               **ioc_options):
    """IOC Setup."""

    filter_index_to_attribute = {
        index: f'filter_{suffix}'
        for index, suffix in filter_group.items()
    }

    subgroups = {
        filter_index_to_attribute[index]: SubGroup(
            FilterGroup, prefix=f':FILTER:{suffix}:', index=index)
        for index, suffix in filter_group.items()
    }

    motor_prefixes = {
        idx: f'{motor_prefix}{idx:02d}:STATE'
        for idx in range(1, len(filter_group) + 1)
    }

    motors = {
        'get': [f'{motor}:GET_RBV' for idx, motor in motor_prefixes.items()],
        'set': [f'{motor}:GET_RBV' for idx, motor in motor_prefixes.items()],
        'error': [f'{motor}:ERR_RBV' for idx, motor in motor_prefixes.items()],
    }

    class IOCMain(IOCBase):
        num_filters = len(filter_index_to_attribute)
        locals().update(**subgroups)

    ioc = IOCMain(prefix=prefix,
                  eV=eV_pv,
                  filter_index_to_attribute=filter_index_to_attribute,
                  motors=motors,
                  pmps_run=pmps_run_pv,
                  pmps_tdes=pmps_tdes_pv,
                  **ioc_options)

    ioc.autosave_helper.filename = autosave_path
    ioc.autosave_helper.file_manager = RotatingFileManager(autosave_path)
    return ioc
