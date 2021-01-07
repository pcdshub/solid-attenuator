from caproto import ChannelType
from caproto.server import PVGroup, SubGroup, pvproperty

from .blades import FakeBladeGroup


class FakeEVGroup(PVGroup):
    """
    PV group for fake photon energy readback
    """
    fake_eV = pvproperty(value=9500,
                         name='CurrentPhotonEnergy_RBV',
                         record='ao',
                         upper_alarm_limit=25000,
                         lower_alarm_limit=1000,
                         lower_ctrl_limit=0,
                         doc='Fake photon energy PV for attenuator testing',
                         units='eV'
                         )


class FakePMPSGroup(PVGroup):
    """
    Fake PV group for simulating incoming PMPS commands.
    """
    t_des = pvproperty(value=0.1,
                       name='T_DES',
                       record='ao',
                       upper_ctrl_limit=1.0,
                       lower_ctrl_limit=0.0,
                       doc='PMPS requested transmission')

    run = pvproperty(value='False',
                     name='RUN',
                     record='bo',
                     enum_strings=['False', 'True'],
                     doc='PMPS Change transmission command',
                     dtype=ChannelType.ENUM)


class IOCMain(PVGroup):
    """
    Main simulation group for SXR solid attenuators like AT1K4.
    """
    beam = SubGroup(FakeEVGroup, prefix='PMPS:LFE:PE:UND:')
    pmps = SubGroup(FakePMPSGroup, prefix='PMPS:{{system}}:')
    attenuator = SubGroup(FakeBladeGroup, prefix='{{system}}:L2SI:')
