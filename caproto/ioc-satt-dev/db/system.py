from caproto.server import pvproperty, PVGroup
from caproto import ChannelType
import asyncio 

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

    @pvproperty(name='T_CALC',
                value=0.5,
                upper_alarm_limit=1.0,
                lower_alarm_limit=0.0,
                read_only=True)
    async def t_calc(self, instance):
        t = self.ioc.t_calc()
        return t

    @pvproperty(name='T_3OMEGA',
                value=0.5,
                upper_alarm_limit=1.0,
                lower_alarm_limit=0.0,
                read_only=True)
    async def t_calc_3omega(self, instance):
        t = self.ioc.t_calc_3omega()
        return t

    eV_RBV = pvproperty(name='EV_RBV',
                value=1000.0,
                read_only=True,
                units='eV')
    @eV_RBV.startup
    async def eV_RBV(self, instance, async_lib):
        while True:
            eV = self.eV.get()
            for group in self.ioc.filter_group:
                filter = self.ioc.groups[f'{group}']
                closest_eV, i = self.ioc.calc_closest_eV(eV, **filter.table_kwargs)
                await filter.pvdb[f'{self.ioc.prefix}:FILTER:{group}:CLOSE_EV_INDEX'].write(i)
                await filter.pvdb[f'{self.ioc.prefix}:FILTER:{group}:CLOSE_EV'].write(closest_eV)
                await filter.pvdb[f'{self.ioc.prefix}:FILTER:{group}:T'].write(
                    filter.get_transmission(eV, filter.thickness.value))
                await filter.pvdb[f'{self.ioc.prefix}:FILTER:{group}:T_3OMEGA'].write(
                    filter.get_transmission(3.*eV, filter.thickness.value))
                await instance.write(eV)
                await async_lib.library.sleep(self.dt)
        return eV

    t_desired = pvproperty(name='T_DES',
                value=0.5,
                read_only=True)
    @t_desired.startup
    async def t_desired(self, instance, async_lib):
        while True:
            pmps_tdes = self.pmps_tdes.get()
            await instance.write(pmps_tdes)
            await async_lib.library.sleep(self.dt)
        return pmps_tdes

    def __init__(self, prefix, *, ioc, **kwargs):
        super().__init__(prefix, **kwargs)
        self.ioc = ioc
        self.eV = self.ioc.eV
        self.pmps_run = self.ioc.pmps_run
        self.pmps_tdes = self.ioc.pmps_tdes
        self.config_table = self.ioc.config_table
        self.dt = 0.01
        
    @t_low.putter
    async def t_low(self, instance, value):
        self.ioc.transmission_value_error(value)

    @t_high.putter
    async def t_high(self, instance, value):
        self.ioc.transmission_value_error(value)
