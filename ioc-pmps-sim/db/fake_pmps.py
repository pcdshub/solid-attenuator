from caproto import ChannelType
from caproto.server import PVGroup, pvproperty


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
