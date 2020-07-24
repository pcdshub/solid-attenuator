from caproto import ChannelType
from caproto.server import PVGroup, pvproperty

from .util import monitor_pvs


class SystemGroup(PVGroup):
    """
    PV group for attenuator system-spanning information.
    """
    t_calc = pvproperty(value=0.1,
                        name='T_CALC',
                        record='ao',
                        upper_alarm_limit=1.0,
                        lower_alarm_limit=0.0,
                        read_only=True,
                        doc='Calculated transmission')

    t_high = pvproperty(value=0.1,
                        name='T_HIGH',
                        record='ao',
                        upper_alarm_limit=1.0,
                        lower_alarm_limit=0.0,
                        read_only=True,
                        doc='Desired transmission best achievable (high)')

    t_low = pvproperty(value=0.1,
                       name='T_LOW',
                       record='ao',
                       upper_alarm_limit=1.0,
                       lower_alarm_limit=0.0,
                       read_only=True,
                       doc='Desired transmission best achievable (low)')

    running = pvproperty(value='False',
                         name='RUNNING',
                         record='bo',
                         enum_strings=['False', 'True'],
                         read_only=True,
                         doc='The system is running',
                         dtype=ChannelType.ENUM)

    mirror_in = pvproperty(value='False',
                           name='MIRROR_IN',
                           record='bo',
                           enum_strings=['False', 'True'],
                           read_only=True,
                           doc='The inspection mirror is in',
                           dtype=ChannelType.ENUM)

    mode = pvproperty(value='Floor',
                      name='MODE',
                      record='bo',
                      enum_strings=['Floor', 'Ceiling'],
                      read_only=False,
                      doc=('Mode for selecting floor or ceiling transmission'
                           'estimation'),
                      dtype=ChannelType.ENUM)

    set_config = pvproperty(name='SET_CONFIG',
                            value=0,
                            max_length=18,
                            read_only=True)

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

    @property
    def current_photon_energy(self):
        return self.eV_RBV.value

    eV_RBV = pvproperty(name='EV_RBV',
                        value=1000.0,
                        read_only=True,
                        units='eV')

    @eV_RBV.startup
    async def eV_RBV(self, instance, async_lib):
        """Update beam energy and calculated values."""
        pvname = self.ioc.monitor_pvnames['ev']
        async for event, pv, data in monitor_pvs(pvname, async_lib=async_lib):
            if event == 'connection':
                self.log.info('%s %s', pv, data)
                continue

            eV = data.data[0]
            self.log.debug('Photon energy changed: %s', eV)

            if instance.value != eV:
                print("Photon energy changed to {} eV.".format(eV))
                await instance.write(eV)
                for f in range(len(self.ioc.filter_group)):
                    filter = self.ioc.filter(f+1)
                    closest_eV, i = self.ioc.calc_closest_eV(
                        eV, **filter.table_kwargs)
                    await filter.closest_eV_index.write(i)
                    await filter.closest_eV.write(closest_eV)
                    await filter.transmission.write(
                        filter.get_transmission(eV, filter.thickness.value))
                    await filter.transmission_3omega.write(
                        filter.get_transmission(3.*eV, filter.thickness.value))
                print(f"Closest tabulated photon energy: {closest_eV} eV")
                await self.t_calc.write(self.ioc.t_calc())

        return eV

    t_desired = pvproperty(
        name='T_DES',
        value=0.5,
        read_only=True,
        lower_ctrl_limit=0.0,
        upper_ctrl_limit=1.0,
    )

    @t_desired.startup
    async def t_desired(self, instance, async_lib):
        """Update PMPS desired transmission value."""
        pvname = self.ioc.monitor_pvnames['pmps_tdes']
        async for event, pv, data in monitor_pvs(pvname, async_lib=async_lib):
            if event == 'connection':
                self.log.info('%s %s', pv, data)
                continue

            pmps_tdes = data.data[0]
            self.log.debug('Desired transmission changed: %s', pmps_tdes)

            if instance.value != pmps_tdes:
                print("Desired transmission set to {}".format(
                    pmps_tdes))
                try:
                    await instance.write(pmps_tdes)
                except Exception:
                    self.log.exception('Failed to update desired transmission')

        return pmps_tdes

    run = pvproperty(value='False',
                     name='RUN',
                     record='bo',
                     enum_strings=['False', 'True'],
                     doc='Change transmission',
                     read_only=True,
                     dtype=ChannelType.ENUM)

    @run.startup
    async def run(self, instance, async_lib):
        """
        Update PMPS run command value.  When true the `:SET_CONFIG` PV will
        update to the optimal configuration for the current desired
        transmission `:T_DES`.
        """

        pvname = self.ioc.monitor_pvnames['pmps_run']
        async for event, pv, data in monitor_pvs(pvname, async_lib=async_lib):
            if event == 'connection':
                self.log.info('%s %s', pv, data)
                continue

            pmps_run = data.data[0]
            self.log.debug('PMPS run request: %s', pmps_run)

            if pmps_run == 1 and instance.value == "False":
                self.log.warning(
                    "PMPS run command received. "
                    "Desired transmission: %s (%s eV)",
                    self.t_desired.value,
                    self.current_photon_energy,
                )
                await instance.write(1)
                try:
                    await self.set_config.write(self.ioc.get_config()[0])
                    self.ioc.print_config()
                except Exception:
                    self.log.exception('Get config failed?')
            if pmps_run == 1 and instance.value == "True":
                pass
            if pmps_run == 0 and instance.value == "True":
                await instance.write(0)

        return pmps_run

    def __init__(self, prefix, *, ioc, **kwargs):
        super().__init__(prefix, **kwargs)
        self.ioc = ioc
        self.config_table = self.ioc.config_table
        self.dt = 0.01

    @t_low.putter
    async def t_low(self, instance, value):
        self.ioc.transmission_value_error(value)

    @t_high.putter
    async def t_high(self, instance, value):
        self.ioc.transmission_value_error(value)
