from caproto.server import pvproperty, PVGroup, ioc_arg_parser, run
from caproto import ChannelType

from db.filters import FilterGroup
from db.system import SystemGroup
from db.fake_ev import FakeEVGroup

pref = "AT2L0:SIM"
num_blades = 18
filter_group = [str(N+1).zfill(2) for N in range(num_blades)]

class IOCMain(PVGroup):
    """
    """
    def __init__(self, prefix, *, groups, **kwargs):
        super().__init__(prefix, **kwargs)
        self.groups = groups


def create_ioc(prefix, filter_group, **ioc_options):
    groups = {}
    ioc = IOCMain(prefix=prefix, groups=groups, **ioc_options)

    for group_prefix in filter_group:
        groups[group_prefix] = FilterGroup(f'{prefix}:FILTER:{group_prefix}:', ioc=ioc)

    groups['SYS'] = SystemGroup(f'{prefix}:SYS:', ioc=ioc)

    # Fake photon energy PV for development:
    groups['LCLS:HXR:BEAM'] = FakeEVGroup(f'LCLS:HXR:BEAM:',ioc=ioc)

    for group in groups.values():
        ioc.pvdb.update(**group.pvdb)
    return ioc


if __name__ == '__main__':
    ioc_options, run_options = ioc_arg_parser(
        default_prefix=pref,
        desc=IOCMain.__doc__
    )
    ioc = create_ioc(
        filter_group=filter_group,
        **ioc_options)
    run(ioc.pvdb, **run_options)
