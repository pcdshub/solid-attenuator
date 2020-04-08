from caproto.server import pvproperty, PVGroup, ioc_arg_parser, run
from caproto import ChannelType
from caproto.threading import pyepics_compat as epics
from h5py import File as h5file

from app import *

from db.filters import FilterGroup
from db.system import SystemGroup
from db.fake_ev import FakeEVGroup
from db.fake_pmps import FakePMPSGroup

pref = "AT2L0:SIM"
eV_name = "LCLS:HXR:BEAM:EV"
pmps_run_name = "PMPS:HXR:AT2L0:RUN"
num_blades = 18
absorption_data = h5file('../../absorption_data.h5')
config_data = h5file('../../configs.h5')
filter_group = [str(N+1).zfill(2) for N in range(num_blades)]


def create_ioc(prefix, filter_group, **ioc_options):
    groups = {}
    ioc = IOCMain(prefix=prefix,
                  groups=groups,
                  abs_data=absroption_data,
                  config_data=config_data,
                  eV=epics.get_pv(eV_name),
                  pmps_run=epics.get_pv(pmps_run_name),
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


if __name__ == '__main__':
    ioc_options, run_options = ioc_arg_parser(
        default_prefix=pref,
        desc=IOCMain.__doc__)
    ioc = create_ioc(
        filter_group=filter_group,
        **ioc_options)
    run(ioc.pvdb, **run_options)
