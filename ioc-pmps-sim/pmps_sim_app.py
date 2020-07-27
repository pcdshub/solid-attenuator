from caproto.server import PVGroup

from .db.fake_ev import FakeEVGroup
from .db.fake_pmps import FakePMPSGroup


class IOCMain(PVGroup):
    """
    """

    def __init__(self,
                 prefix,
                 *,
                 groups,
                 **kwargs):
        super().__init__(prefix, **kwargs)


def create_ioc(prefix, eV_pv, pmps_run_pv,
               **ioc_options):
    groups = {}
    ioc = IOCMain(prefix=prefix,
                  groups=groups,
                  **ioc_options)

    # Fake PV groups for development and testing:
    groups['LCLS:HXR:BEAM'] = FakeEVGroup('LCLS:HXR:BEAM:', ioc=ioc)
    groups['PMPS:HXR:AT2L0'] = FakePMPSGroup('PMPS:HXR:AT2L0:', ioc=ioc)

    for group in groups.values():
        ioc.pvdb.update(**group.pvdb)
    return ioc
