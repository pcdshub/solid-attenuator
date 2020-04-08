from caproto.server import pvproperty, PVGroup
from caproto import ChannelType

class SystemGroup(PVGroup):
    """
    PV group for attenuator system-spanning information.
    """
    t_calc = pvproperty(value=0.1,
                        name='T_CALC',
                        mock_record='ao',
                        upper_alarm_limit=1.0,
                        lower_alarm_limit=0.0,
                        read_only=True,
                        doc='Calculated transmission')

    t_high = pvproperty(value=0.1,
                        name='T_HIGH',
                        mock_record='ao',
                        upper_alarm_limit=1.0,
                        lower_alarm_limit=0.0,
                        read_only=True,
                        doc='Desired transmission '
                        +'best achievable (high)')

    t_low = pvproperty(value=0.1,
                       name='T_LOW',
                       mock_record='ao',
                       upper_alarm_limit=1.0,
                       lower_alarm_limit=0.0,
                       read_only=True,
                       doc='Desired transmission '
                       +'best achievable (low)')

    t_desired = pvproperty(value=0.1,
                           name='T_DESIRED',
                           mock_record='ao',
                           upper_alarm_limit=1.0,
                           lower_alarm_limit=0.0,
                           read_only=True,
                           doc='Desired transmission')

    t_3omega_calc = pvproperty(value=0.1,
                               name='T_3OMEGA_CALC',
                               mock_record='ao',
                               upper_alarm_limit=1.0,
                               lower_alarm_limit=0.0,
                               read_only=True,
                               doc='Actual 3rd harmonic '
                               +'transmission')

    run = pvproperty(value='False',
                     name='RUN',
                     mock_record='bo',
                     enum_strings=['False', 'True'],
                     doc='Change transmission',
                     read_only=True,
                     dtype=ChannelType.ENUM)

    running = pvproperty(value='False',
                         name='RUNNING',
                         mock_record='bo',
                         enum_strings=['False', 'True'],
                         read_only=True,
                         doc='The system is running',
                         dtype=ChannelType.ENUM)

    mirror_in = pvproperty(value='False',
                           name='MIRROR_IN',
                           mock_record='bo',
                           enum_strings=['False', 'True'],
                           read_only=True,
                           doc='The inspection mirror is in',
                           dtype=ChannelType.ENUM)

    test = pvproperty(value=None,
                      mock_record='bo',
                      enum_strings=['False', 'True'],
                      read_only=True,
                      dtype=ChannelType.ENUM,
                      name='TEST')

    testput = pvproperty(value='False',
                         mock_record='bo',
                         enum_strings=['False', 'True'],
 #                        read_only=True,
                         dtype=ChannelType.ENUM,
                         name='TESTPUT')

    def __init__(self, prefix, *, ioc, test_val=False, **kwargs):
        super().__init__(prefix, **kwargs)
        self.ioc = ioc
        self.test_val = test_val

    @t_calc.putter
    async def t_calc(self, instance, value):
        transmission_value_error(value)

    @t_desired.putter
    async def t_desired(self, instance, value):
        transmission_value_error(value)

    @t_low.putter
    async def t_low(self, instance, value):
        transmission_value_error(value)

    @t_high.putter
    async def t_high(self, instance, value):
        transmission_value_error(value)

    @t_3omega_calc.putter
    async def t_3omega_calc(self, instance, value):
        transmission_value_error(value)

    @test.startup
    async def test(self, instance, value):
        await instance.write(self.test_val)
    
    @testput.putter
    async def testput(self, instance, value):
        await self.test.write(value)

def transmission_value_error(value):
    if value < 0 or value > 1:
        raise ValueError('Transmission must be '
                         +'between 0 and 1.')
