from caproto.server import PVGroup, SubGroup

from .db import FakeBladeGroup, FakeEVGroup, FakePMPSGroup


class IOCMain(PVGroup):
    """
    """

    beam = SubGroup(FakeEVGroup, prefix='LCLS:HXR:BEAM:')
    pmps = SubGroup(FakePMPSGroup, prefix='PMPS:HXR:AT2L0:')
    attenuator = SubGroup(FakeBladeGroup, prefix='PMPS:HXR:AT2L0:')


def create_ioc(prefix, eV_pv, pmps_run_pv, **ioc_options):
    return IOCMain(prefix=prefix, **ioc_options)
