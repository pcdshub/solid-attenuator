import enum
import threading
import time

import numpy as np
from caproto import AlarmSeverity, AlarmStatus, ChannelType
from caproto.asyncio.server import AsyncioAsyncLayer
from caproto.server import PVGroup, pvproperty
from caproto.server.autosave import autosaved

from .. import calculator
from . import util
from .util import monitor_pvs


class State(enum.IntEnum):
    Out = 0
    In = 1

    def __repr__(self):
        return self.name


STATE_FROM_MOTOR = {
    0: State.Out,  # unknown -> out
    1: State.Out,  # out
    2: State.In,  # in
}

STATE_TO_MOTOR = {
    State.Out: 1,
    State.In: 2,
}


class SystemGroup(PVGroup):
    """
    PV group for attenuator system-spanning information.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # TODO: this could be done by wrapping SystemGroup
        for obj in (self.best_config, self.active_config):
            util.hack_max_length_of_channeldata(obj,
                                                [0] * self.parent.num_filters)

        # TODO: caproto does not make this easy. We explicitly will be using
        # asyncio here.
        self.async_lib = AsyncioAsyncLayer()
        self._context = {}
        self._pv_put_queue = None
        self._put_thread = None

    calculated_transmission = pvproperty(
        value=0.1,
        name='T_CALC',
        record='ao',
        upper_alarm_limit=1.0,
        lower_alarm_limit=0.0,
        read_only=True,
        doc='Calculated transmission (all blades)',
        precision=3,
    )

    calculated_transmission_3omega = pvproperty(
        name='T_3OMEGA',
        value=0.5,
        upper_alarm_limit=1.0,
        lower_alarm_limit=0.0,
        read_only=True,
        doc='Calculated 3omega transmission (all blades)',
        precision=3,
    )

    best_config_error = pvproperty(
        value=0.1,
        name='BestConfigError_RBV',
        record='ao',
        upper_alarm_limit=1.0,
        lower_alarm_limit=-1.0,
        read_only=True,
        doc='Calculated transmission error',
        precision=3,
    )

    moving = pvproperty(
        name='Moving_RBV',
        value='False',
        record='bo',
        enum_strings=['False', 'True'],
        read_only=True,
        doc='Moving to a new configuration.',
        dtype=ChannelType.ENUM
    )

    mirror_in = pvproperty(
        value='False',
        name='MIRROR_IN',
        record='bo',
        enum_strings=['False', 'True'],
        read_only=True,
        doc='The inspection mirror is in',
        dtype=ChannelType.ENUM
    )

    calc_mode = pvproperty(
        value='Floor',
        name='CalcMode',
        record='bo',
        enum_strings=['Floor', 'Ceiling'],
        read_only=False,
        doc='Mode for selecting floor or ceiling transmission estimation',
        dtype=ChannelType.ENUM
    )

    energy_source = pvproperty(
        value='Actual',
        name='EnergySource',
        record='bo',
        enum_strings=['Actual', 'Custom'],
        read_only=False,
        doc='Choose the source of photon energy',
        dtype=ChannelType.ENUM,
    )

    best_config = pvproperty(
        name='BestConfiguration_RBV',
        value=0,
        max_length=1,
        read_only=True
    )

    active_config = pvproperty(
        name='ActiveConfiguration_RBV',
        value=0,
        max_length=1,
        read_only=True,
        alarm_group='motors',
    )

    energy_actual = pvproperty(
        name='ActualPhotonEnergy_RBV',
        value=0.0,
        read_only=True,
        units='eV',
        alarm_group='valid_photon_energy',
        precision=1,
    )

    transmission_actual = pvproperty(
        name='ActualTransmission_RBV',
        value=0.0,
        read_only=True,
        alarm_group='motors',
        precision=3,
    )

    transmission_3omega_actual = pvproperty(
        name='Actual3OmegaTransmission_RBV',
        value=0.0,
        read_only=True,
        alarm_group='motors',
        precision=3,
    )

    energy_custom = pvproperty(
        name='CustomPhotonEnergy',
        value=0.0,
        read_only=False,
        units='eV',
        lower_ctrl_limit=100.0,
        upper_ctrl_limit=30000.0,
        precision=1,
    )

    energy_calc = pvproperty(
        name='LastPhotonEnergy_RBV',
        value=0.0,
        read_only=True,
        units='eV',
        doc='Energy that was used for the calculation.',
        precision=1,
    )

    apply_config = pvproperty(
        name='ApplyConfiguration',
        value='False',
        record='bo',
        enum_strings=['False', 'True'],
        doc='Apply the calculated configuration.',
        dtype=ChannelType.ENUM,
        alarm_group='motors',
    )

    cancel_apply = pvproperty(
        name='Cancel',
        value='False',
        record='bo',
        enum_strings=['False', 'True'],
        doc='Stop trying to apply the configuration.',
        dtype=ChannelType.ENUM,
    )

    desired_transmission = autosaved(
        pvproperty(
            name='DesiredTransmission',
            value=0.5,
            lower_ctrl_limit=0.0,
            upper_ctrl_limit=1.0,
            doc='Desired transmission value',
            precision=3,
        )
    )

    run = pvproperty(
        value='False',
        name='Run',
        record='bo',
        enum_strings=['False', 'True'],
        doc='Run calculation',
        dtype=ChannelType.ENUM
    )

    @active_config.startup
    async def active_config(self, instance, async_lib):
        motor_pvnames = self.parent.monitor_pvnames['motors']
        monitor_list = sum((pvlist for pvlist in motor_pvnames.values()),
                           [])
        all_status = {pv: False for pv in monitor_list}

        async def update_connection_status(pv, status):
            all_status[pv] = (status == 'connected')
            if all(all_status.values()):
                status, severity = AlarmStatus.NO_ALARM, AlarmSeverity.NO_ALARM
            else:
                status, severity = AlarmStatus.LINK, AlarmSeverity.MAJOR_ALARM

            if instance.alarm.status != status:
                await instance.alarm.write(status=status, severity=severity)

        async for event, context, data in monitor_pvs(*monitor_list,
                                                      async_lib=async_lib):
            if event == 'connection':
                await update_connection_status(context.name, data)
                continue

            value = data.data[0]
            pvname = context.pv.name
            if pvname in motor_pvnames['get']:
                idx = motor_pvnames['get'].index(pvname)
                new_config = list(self.active_config.value)
                new_config[idx] = STATE_FROM_MOTOR.get(value, value)
                if tuple(new_config) != tuple(self.active_config.value):
                    self.log.info('Active config changed: %s', new_config)
                    await self.active_config.write(new_config)
                    await self._update_active_transmission()

    async def _update_active_transmission(self):
        config = tuple(self.active_config.value)
        offset = self.parent.first_filter
        working_filters = self.parent.working_filters

        transm = np.zeros_like(config) * np.nan
        transm3 = np.zeros_like(config) * np.nan
        for idx, filt in working_filters.items():
            zero_index = idx - offset
            if config[zero_index] == State.In:
                transm[zero_index] = filt.transmission.value
                transm3[zero_index] = filt.transmission_3omega.value

        await self.transmission_actual.write(np.nanprod(transm))
        await self.transmission_3omega_actual.write(np.nanprod(transm3))

    @energy_actual.startup
    async def energy_actual(self, instance, async_lib):
        """Update beam energy and calculated values."""
        async def update_connection_status(status):
            if status == 'connected':
                status, severity = AlarmStatus.NO_ALARM, AlarmSeverity.NO_ALARM
            else:
                status, severity = AlarmStatus.LINK, AlarmSeverity.MAJOR_ALARM
            await instance.alarm.write(status=status, severity=severity)

        await update_connection_status('disconnected')
        pvname = self.parent.monitor_pvnames['ev']
        async for event, context, data in monitor_pvs(pvname,
                                                      async_lib=async_lib):
            if event == 'connection':
                self.log.info('%s %s', context, data)
                await update_connection_status(data)
                continue

            eV = data.data[0]
            self.log.debug('Photon energy changed: %s', eV)

            if instance.value != eV:
                delta = instance.value - eV
                if abs(delta) > 1000:
                    self.log.info("Photon energy changed to %s eV.", eV)
                await instance.write(eV)

        return eV

    @util.block_on_reentry()
    async def run_calculation(self):
        energy = {
            'Actual': self.energy_actual.value,
            'Custom': self.energy_custom.value,
        }[self.energy_source.value]

        await self.energy_calc.write(energy)

        # Update all of the filters first, to determine their transmission
        # at this energy
        for filter in self.parent.filters.values():
            await filter.set_photon_energy(energy)

        await self.calculated_transmission.write(
            self.parent.calculate_transmission()
        )
        await self.calculated_transmission_3omega.write(
            self.parent.calculate_transmission_3omega()
        )

        # Using the above-calculated transmissions, find the best configuration
        config = calculator.get_best_config(
            all_transmissions=self.parent.all_transmissions,
            t_des=self.desired_transmission.value,
            mode=self.calc_mode.value
        )
        await self.best_config.write(config.filter_states)
        await self.best_config_error.write(
            config.transmission - self.desired_transmission.value
        )
        self.log.info(
            'Energy %s eV %s transmission desired %.2g estimated %.2g '
            '(delta %.3g) configuration: %s',
            energy,
            self.calc_mode.value,
            self.desired_transmission.value,
            config.transmission,
            self.best_config_error.value,
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

    @apply_config.startup
    async def apply_config(self, instance, async_lib):
        def put_thread():
            while True:
                pv, value = self._pv_put_queue.get()
                try:
                    pv.write([value], wait=False)
                except Exception:
                    self.log.exception('Failed to put value: %s=%s', pv, value)

        ctx = util.get_default_thread_context()

        self._set_pvs = ctx.get_pvs(
            *self.parent.monitor_pvnames['motors']['set'], timeout=None)

        self._pv_put_queue = self.async_lib.ThreadsafeQueue()
        self._put_thread = threading.Thread(target=put_thread, daemon=True)
        self._put_thread.start()

    @apply_config.putter
    async def apply_config(self, instance, value):
        if value == 'False':
            return

        timeout_threshold = 30.0
        t0 = time.monotonic()

        def check_done():
            elapsed = time.monotonic() - t0
            done = (tuple(self.active_config.value) ==
                    tuple(self.best_config.value))
            return any(
                (done,
                 self.cancel_apply.value == 'True',
                 elapsed > timeout_threshold)
            )

        await self.moving.write(1)

        requested = {}

        while not check_done():
            items = list(zip(self._set_pvs, self.active_config.value,
                             self.best_config.value))
            move_out = [pv for pv, active, best in items
                        if active == State.In and best == State.Out]
            move_in = [pv for pv, active, best in items
                       if active == State.Out and best == State.In]
            if move_in:
                # Move blades IN first, to be safe
                for pv in move_in:
                    if requested.get(pv, None) == State.In:
                        break
                    requested[pv] = State.In
                    self.log.debug('Moving in %s', pv)
                    await self._pv_put_queue.async_put(
                        (pv, STATE_TO_MOTOR[State.In]),
                    )
            elif move_out:
                for pv in move_out:
                    if requested.get(pv, None) == State.Out:
                        break
                    requested[pv] = State.Out
                    self.log.debug('Moving out %s', pv)
                    await self._pv_put_queue.async_put(
                        (pv, STATE_TO_MOTOR[State.Out]),
                    )
            else:
                break

            await self.async_lib.library.sleep(0.1)

        await self.moving.write(0)

    # apply_config.PROC -> apply_config = 1
    util.process_writes_value(apply_config, value=1)
