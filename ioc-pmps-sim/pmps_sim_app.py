from caproto import ChannelType
from caproto.server import PVGroup, ioc_arg_parser, pvproperty, run
from caproto.threading import pyepics_compat as epics
from db.fake_ev import FakeEVGroup
from db.fake_pmps import FakePMPSGroup


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
    groups['LCLS:HXR:BEAM'] = FakeEVGroup(
        f'LCLS:HXR:BEAM:',ioc=ioc)
    groups['PMPS:HXR:AT2L0'] = FakePMPSGroup(
        f'PMPS:HXR:AT2L0:',ioc=ioc)

    for group in groups.values():
        ioc.pvdb.update(**group.pvdb)
    return ioc
