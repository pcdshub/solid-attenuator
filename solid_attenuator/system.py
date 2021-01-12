import threading
import time
from typing import Dict, List

import numpy as np
from caproto import AlarmSeverity, AlarmStatus, ChannelType
from caproto.asyncio.server import AsyncioAsyncLayer
from caproto.server import PVGroup, pvproperty
from caproto.server.autosave import autosaved

from . import util
from .util import State, monitor_pvs


class SystemGroupBase(PVGroup):
    """
    PV group for attenuator system-spanning information.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # TODO: this could be done by wrapping SystemGroup
        for obj in (self.best_config, self.active_config, self.filter_moving):
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
        read_only=True,
        doc='Best configuration as an array (1 if inserted)',
    )

    best_config_bitmask = pvproperty(
        name='BestConfigurationBitmask_RBV',
        value=0,
        read_only=True,
        doc='Best configuration as an integer',
    )

    active_config = pvproperty(
        name='ActiveConfiguration_RBV',
        value=0,
        max_length=1,
        read_only=True,
        alarm_group='motors',
        doc='Active configuration array',
    )

    active_config_bitmask = pvproperty(
        name='ActiveConfigurationBitmask_RBV',
        value=0,
        read_only=True,
        alarm_group='motors',
        doc='Active configuration represented as an integer',
    )

    filter_moving = pvproperty(
        name='FiltersMoving_RBV',
        value=0,
        max_length=1,
        read_only=True,
        alarm_group='motors',
        doc='Filter motion status as an array (1 if moving)',
    )

    filter_moving_bitmask = pvproperty(
        name='FiltersMovingBitmask_RBV',
        value=0,
        read_only=True,
        alarm_group='motors',
        doc='Filter motion status as an integer',
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

    last_energy = pvproperty(
        name='LastPhotonEnergy_RBV',
        value=0.0,
        read_only=True,
        units='eV',
        doc='Energy that was used for the calculation.',
        precision=1,
    )

    last_transmission = pvproperty(
        name='LastTransmission_RBV',
        value=0.0,
        lower_ctrl_limit=0.0,
        upper_ctrl_limit=1.0,
        doc='Last desired transmission value',
        precision=3,
        read_only=True,
    )

    last_mode = pvproperty(
        value='Floor',
        name='LastCalcMode_RBV',
        record='bo',
        enum_strings=['Floor', 'Ceiling'],
        read_only=True,
        doc='Last calculation mode',
        dtype=ChannelType.ENUM,
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
            await util.alarm_if(instance, not all(all_status.values()),
                                AlarmStatus.LINK)

        async for event, context, data in monitor_pvs(*monitor_list,
                                                      async_lib=async_lib):
            if event == 'connection':
                await update_connection_status(context.name, data)
                continue

            pvname = context.pv.name
            if pvname not in motor_pvnames['get']:
                continue

            idx = self.parent.monitor_pvnames['motors']['get'].index(pvname)
            await self.motor_has_moved(self.parent.first_filter + idx,
                                       data.data[0])

    @energy_actual.startup
    async def energy_actual(self, instance, async_lib):
        """Update beam energy and calculated values."""
        async def update_connection_status(status):
            await util.alarm_if(
                instance, status != 'connected', AlarmStatus.LINK
            )

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

    @apply_config.putter
    async def apply_config(self, instance, value):
        if value == 'False':
            return

        await self.move_blades()

    # apply_config.PROC -> apply_config = 1
    util.process_writes_value(apply_config, value=1)

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

    async def move_blades(self, *, timeout_threshold=30.0):
        """Move to the calculated configuration."""
        t0 = time.monotonic()

        def check_done():
            elapsed = time.monotonic() - t0
            done = (tuple(self.active_config.value) ==
                    tuple(self.best_config.value))
            moving = any(status for status in self.filter_moving.value)
            return any(
                (done and not moving,
                 self.cancel_apply.value == 'True',
                 elapsed > timeout_threshold,
                 )
            )

        await self.moving.write(1)

        state = {}
        while not check_done():
            if not await self.move_blade_step(state):
                break

            await self.async_lib.library.sleep(0.1)

        await self.moving.write(0)

    @run.putter
    async def run(self, instance, value):
        if value == 'False':
            return

        try:
            energy = {
                'Actual': self.energy_actual.value,
                'Custom': self.energy_custom.value,
            }[self.energy_source.value]

            desired_transmission = self.desired_transmission.value
            calc_mode = self.calc_mode.value
            await self.run_calculation(
                energy,
                desired_transmission=self.desired_transmission.value,
                calc_mode=calc_mode,
            )
        except util.MisconfigurationError as ex:
            self.log.warning('Misconfiguration blocks calculation: %s', ex)
            await self.desired_transmission.alarm.write(
                status=AlarmStatus.CALC, severity=AlarmSeverity.MAJOR_ALARM,
            )
        except Exception:
            self.log.exception('Calculation failed unexpectedly')
            await self.desired_transmission.alarm.write(
                status=AlarmStatus.CALC, severity=AlarmSeverity.MAJOR_ALARM,
            )
        else:
            await self.last_energy.write(energy)
            await self.last_mode.write(calc_mode)
            await self.last_transmission.write(desired_transmission)

    # RUN.PROC -> run = 1
    util.process_writes_value(run, value=1)

    async def _update_active_transmission(self):
        """Re-calculate transmission_actual based on working filters."""
        config = tuple(self.active_config.value)
        offset = self.parent.first_filter

        transm = np.zeros_like(config) * np.nan
        transm3 = np.zeros_like(config) * np.nan
        for idx, filt in self.working_filters.items():
            zero_index = idx - offset
            if State(config[zero_index]).is_inserted:
                transm[zero_index] = filt.transmission.value
                transm3[zero_index] = filt.transmission_3omega.value

        await self.transmission_actual.write(np.nanprod(transm))
        await self.transmission_3omega_actual.write(np.nanprod(transm3))

    async def move_blade_step(self, state: Dict[int, State]):
        """
        Caller is requesting to move blades in or out.

        The caller is expected to handle timeout scenarios and provide a
        dictionary with which we can record this implementation's state.

        Parameters
        ----------
        state : dict
            State dictionary, which we use here to mark each time we request
            a motion.  This will be passed in on subsequent calls.

        Returns
        -------
        continue_ : bool
            Returns `True` if there are more blades to move.
        """
        items = [
            (pv, State(active), State(best)) for pv, active, best in
            zip(
                self._set_pvs, self.active_config.value, self.best_config.value
            )
        ]

        move_out = {
            pv: best
            for pv, active, best in items
            if not best.is_inserted and active != best
        }
        move_in = {
            pv: best
            for pv, active, best in items
            if best.is_inserted and active != best
        }

        if move_in:
            to_move = move_in
            # Move blades IN first, to be safe
        else:
            to_move = move_out

        for pv, target in to_move.items():
            if state.get(pv, None) != target:
                state[pv] = target
                self.log.debug('Moving %s to %s', pv, target)
                await self._pv_put_queue.async_put((pv, target))

        return bool(move_in or move_out)

    def calculate_transmission(self):
        """
        Total transmission through all filter blades.

        Stuck blades are assumed to be 'OUT' and thus the total transmission
        will be overestimated (in the case any blades are actually stuck 'IN').
        """
        t = 1.
        for filt in self.working_filters.values():
            t *= filt.transmission.value
        return t

    def calculate_transmission_3omega(self):
        """
        Total 3rd harmonic transmission through all filter blades.

        Stuck blades are assumed to be 'OUT' and thus the total transmission
        will be overestimated (in the case any blades are actually stuck 'IN').
        """
        t = 1.
        for filt in self.working_filters.values():
            t *= filt.transmission_3omega.value
        return t

    @property
    def all_transmissions(self):
        """
        List of the transmission values for working filters at the current
        energy.

        Stuck filters get a transmission of NaN, which omits them from
        calculations/considerations.
        """
        T_arr = np.zeros(len(self.filters)) * np.nan
        for idx, filt in self.working_filters.items():
            T_arr[idx - self.first_filter] = filt.transmission.value
        return T_arr

    @property
    def first_filter(self):
        """The first filter index in the system."""
        # Indirection for where it's actually stored - in the parent.
        return self.parent.first_filter

    @property
    def filters(self):
        """All filters in the system."""
        # Indirection for where they're actually stored - in the parent.
        return self.parent.filters

    @property
    def working_filters(self):
        """
        A dictionary of all filters that are in working order.

        That is to say, filters that are marked as active and not stuck.
        """
        return {
            idx: filt for idx, filt in self.filters.items()
            if filt.is_stuck.value == 'Not stuck' and
            filt.active.value == "True"
        }

    @property
    def all_filter_materials(self) -> List[str]:
        """All filter materials in a list."""
        return [flt.material.value for flt in self.filters.values()]

    async def motor_has_moved(self, blade_index, raw_state):
        """
        Callback indicating a motor has moved.

        Update the current configuration, if necessary.

        Parameters
        ----------
        blade_index : int
            Blade index (not zero-based).

        raw_state : int
            Raw state value from control system.
        """
        array_idx = blade_index - self.parent.first_filter
        state = State(int(raw_state))

        new_config = list(self.active_config.value)
        new_config[array_idx] = int(state)
        if tuple(new_config) != tuple(self.active_config.value):
            self.log.info('Active config changed: %s', new_config)
            await self.active_config.write(new_config)
            await self.active_config_bitmask.write(
                util.int_array_to_bit_string(
                    [State(blade).is_inserted for blade in new_config]
                )
            )
            await self._update_active_transmission()

        moving = list(self.filter_moving.value)
        moving[array_idx] = state.is_moving
        if tuple(moving) != tuple(self.filter_moving.value):
            await self.filter_moving.write(moving)
            await self.filter_moving_bitmask.write(
                util.int_array_to_bit_string(moving)
            )

        flt = self.parent.filters[blade_index]
        await flt.set_inserted_filter_state(state)
