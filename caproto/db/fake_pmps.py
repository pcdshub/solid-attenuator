from caproto.server import pvproperty, PVGroup
from caproto import ChannelType

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
        if value == True:
            await async_lib.library.sleep(1)
            await instance.write(value='False')
