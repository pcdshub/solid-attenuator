"""
Shared IOC source.
"""
from typing import Dict, List, Type

from caproto.server import PVGroup, SubGroup
from caproto.server.autosave import AutosaveHelper
from caproto.server.stats import StatusHelper


class IOCBase(PVGroup):
    """
    Base for attenuator IOCs.  This is extended dynamically with SubGroups in
    `at2l0.create_ioc` or `sxr.create_ioc`.
    """
    filters: Dict[int, PVGroup]
    prefix: str

    # Set by subclass in `create_ioc_class`:
    motors: Dict[str, List[str]]
    monitor_pvnames: Dict[str, str]
    first_filter: int
    num_filters: int

    def __init__(self, prefix, *, eV, pmps_run, pmps_tdes, **kwargs):
        self.num_filters = len(self.filter_index_to_attribute)
        self.first_filter = min(self.filter_index_to_attribute)
        super().__init__(prefix, **kwargs)
        self.prefix = prefix
        self.filters = {
            idx: getattr(self, attr)
            for idx, attr in self.filter_index_to_attribute.items()
        }
        self.monitor_pvnames = dict(
            ev=eV,
            pmps_run=pmps_run,
            pmps_tdes=pmps_tdes,
            motors=self.motors,
        )

    autosave_helper = SubGroup(AutosaveHelper)
    stats_helper = SubGroup(StatusHelper, prefix=':STATS:')

    @classmethod
    def create_ioc_class(
            cls,
            filters: Dict[int, str],
            subgroups: Dict[str, SubGroup],
            motor_prefixes: Dict[int, str],
            ) -> Type[PVGroup]:
        """
        Helper that creates a new, complete IOC PVGroup class from the base.

        Parameters
        ----------
        filters : dict
            Dictionary of filter index to attribute name.  Mirrored in
            ``filter_index_to_attribute`` on the returned class.

        subgroups : dict
            Dictionary of subgroups to add, which should include one per
            filter and also a system subgroup.

        motor_prefixes : dict
            Dictionary of motor index to PV prefix.  Used to generate the list
            of get, set, and error PVs for each motor.
        """
        assert 'sys' in subgroups, 'Missing system subgroup'

        class IOCMain(IOCBase):
            filter_index_to_attribute = dict(filters)
            motors = {
                'get': [f'{pv}:GET_RBV' for pv in motor_prefixes.values()],
                'set': [f'{pv}:SET' for pv in motor_prefixes.values()],
                'error': [f'{pv}:ERR_RBV' for pv in motor_prefixes.values()],
            }
            locals().update(**subgroups)

        return IOCMain
