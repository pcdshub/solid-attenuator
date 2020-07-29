from caproto import ChannelType
from caproto.server import PVGroup, pvproperty

from .. import calculator
from . import util
from .util import monitor_pvs


class SystemGroup(PVGroup):
    """
    PV group for attenuator system-spanning information.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # TODO: this could be done by wrapping SystemGroup
        util.hack_max_length_of_channeldata(
            self.set_config, [0] * self.parent.num_filters)

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
                        upper_ctrl_limit=1.0,
                        lower_ctrl_limit=0.0,
                        read_only=True,
                        doc='Desired transmission best achievable (high)')

    t_low = pvproperty(value=0.1,
                       name='T_LOW',
                       record='ao',
                       upper_ctrl_limit=1.0,
                       lower_ctrl_limit=0.0,
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
                            max_length=1,
                            read_only=True)

    @pvproperty(name='T_CALC',
                value=0.5,
                upper_alarm_limit=1.0,
                lower_alarm_limit=0.0,
                read_only=True)
    async def t_calc(self, instance):
        t = self.parent.t_calc()
        return t

    @pvproperty(name='T_3OMEGA',
                value=0.5,
                upper_alarm_limit=1.0,
                lower_alarm_limit=0.0,
                read_only=True)
    async def t_calc_3omega(self, instance):
        t = self.parent.t_calc_3omega()
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
        pvname = self.parent.monitor_pvnames['ev']
        async for event, pv, data in monitor_pvs(pvname, async_lib=async_lib):
            if event == 'connection':
                self.log.info('%s %s', pv, data)
                continue

            eV = data.data[0]
            self.log.debug('Photon energy changed: %s', eV)

            if instance.value != eV:
                self.log.info("Photon energy changed to %s eV.", eV)
                await instance.write(eV)
                for filter in self.parent.filters.values():
                    closest_eV, i = calculator.find_closest_energy(
                        eV, filter.table)
                    await filter.closest_eV_index.write(i)
                    await filter.closest_eV.write(closest_eV)
                    await filter.transmission.write(
                        filter.get_transmission(eV, filter.thickness.value))
                    await filter.transmission_3omega.write(
                        filter.get_transmission(3.*eV, filter.thickness.value))
                self.log.info("Closest tabulated photon energy %s eV",
                              closest_eV)
                await self.t_calc.write(self.parent.t_calc())

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
        pvname = self.parent.monitor_pvnames['pmps_tdes']
        async for event, pv, data in monitor_pvs(pvname, async_lib=async_lib):
            if event == 'connection':
                self.log.info('%s %s', pv, data)
                continue

            pmps_tdes = data.data[0]
            self.log.debug('Desired transmission changed: %s', pmps_tdes)

            if instance.value != pmps_tdes:
                try:
                    await instance.write(pmps_tdes)
                except Exception:
                    self.log.exception('Failed to update desired transmission')

        return pmps_tdes

    run = pvproperty(value='False',
                     name='RUN',
                     record='bo',
                     enum_strings=['False', 'True'],
                     doc='Run calculation',
                     dtype=ChannelType.ENUM)

    async def run_calculation(self):
        config = calculator.get_best_config(
            all_transmissions=self.parent.all_transmissions,
            t_des=self.t_desired.value,
            mode=self.mode.value
        )
        await self.set_config.write(config.filter_states)
        self.log.info(
            '%s transmission desired %.2g estimated %.2g '
            '(delta %.3g) configuration: %s',
            self.mode.value,
            self.t_desired.value,
            config.transmission,
            config.transmission - self.t_desired.value,
            config.filter_states,
        )

    @run.putter
    async def run(self, instance, value):
        if value == 'False':
            return

        try:
            await self.run_calculation()
        except Exception:
            self.log.exception('update_config failed?')

    # RUN.PROC -> run = 1
    util.process_writes_value(run, value=1)
