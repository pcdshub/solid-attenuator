from caproto.server import pvproperty, PVGroup, ioc_arg_parser, run
from caproto.threading import pyepics_compat as epics
from caproto import ChannelType

from db.filters import FilterGroup
from db.system import SystemGroup
from db.fake_ev import FakeEVGroup
from db.fake_pmps import FakePMPSGroup

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
        print("hey!")
        self.groups=groups
        self.eV=eV
        self.pmps_run=pmps_run
        self.startup()

    def startup(self):
        self.eV.add_callback(self.eV_callback)
        self.pmps_run.add_callback(self.pmps_run_callback)
        print("startup!")
        print(self.eV)
        print(self.pmps_run)

    def eV_callback(value, **kwargs):
        print("eV changed to {}".format(value))

    def pmps_run_callback(value, **kwargs):
        print("PMPS run changed to {}".format(value))


def create_ioc(prefix, filter_group, eV_pv, pmps_run_pv,
               config_data, absorption_data, **ioc_options):
    groups = {}
    ioc = IOCMain(prefix=prefix,
                  groups=groups,
                  abs_data=absorption_data,
                  config_data=config_data,
                  eV=epics.get_pv(eV_pv, auto_monitor=True),
                  pmps_run=epics.get_pv(pmps_run_pv, auto_monitor=True),
                  **ioc_options)

    for group_prefix in filter_group:
        groups[group_prefix] = FilterGroup(
            f'{prefix}:FILTER:{group_prefix}:',
            ioc=ioc)

    groups['SYS'] = SystemGroup(f'{prefix}:SYS:', ioc=ioc)

    # Fake PV groups for development and testing:
    groups['LCLS:HXR:BEAM'] = FakeEVGroup(
        f'LCLS:HXR:BEAM:',ioc=ioc)
    groups['PMPS:HXR:AT2L0'] = FakePMPSGroup(
        f'PMPS:HXR:AT2L0:',ioc=ioc)
    
    for group in groups.values():
        ioc.pvdb.update(**group.pvdb)
    return ioc
