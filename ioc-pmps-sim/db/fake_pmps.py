from caproto import ChannelType
from caproto.server import PVGroup, pvproperty


class FakePMPSGroup(PVGroup):
    """
    Fake PV group for simulating
    incoming PMPS commands.
    """
    t_des = pvproperty(value=0.1,
                        name='T_DES',
                        mock_record='ao',
                        upper_alarm_limit=1.0,
                        lower_alarm_limit=0.0,
                        doc='PMPS requested transmission')

    run = pvproperty(value='False',
                     name='RUN',
                     mock_record='bo',
                     enum_strings=['False', 'True'],
                     doc='PMPS Change transmission command',
                     dtype=ChannelType.ENUM)

    def __init__(self, prefix, *, ioc, **kwargs):
        super().__init__(prefix, **kwargs)
        self.ioc = ioc

    @run.putter
    async def run(self, instance, value):
        if value == 1:
            exit
            await async_lib.library.sleep(1)
            await instance.write(value='False')

    @t_des.putter
    async def t_des(self, instance, value):
        if value < 0 or value > 1:
            raise ValueError('Invalid transmission request')
