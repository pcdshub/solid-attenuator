from caproto.server import PVGroup, SubGroup

from .db import FakeBladeGroup, FakeEVGroup, FakePMPSGroup


class IOCMain(PVGroup):
    """
    """

    beam = SubGroup(FakeEVGroup, prefix='PMPS:LFE:PE:UND:')
    pmps = SubGroup(FakePMPSGroup, prefix='PMPS:AT2L0:')
    attenuator = SubGroup(FakeBladeGroup, prefix='AT2L0:XTES:')


def create_ioc(prefix, eV_pv, pmps_run_pv, **ioc_options):
    return IOCMain(prefix=prefix, **ioc_options)
