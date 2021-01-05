import enum
from typing import Dict

import numpy as np
from caproto import AlarmSeverity, AlarmStatus

from ... import calculator, util
from ...system import SystemGroupBase


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


def int_array_to_bit_string(int_array: list) -> int:
    """
    Integer array such as [1, 0, 0, 0] to integer (8).

    Returns 0 if non-binary values found in the list.
    """
    try:
        return int(''.join(str(int(c)) for c in int_array), 2)
    except ValueError:
        return 0


class SystemGroup(SystemGroupBase):
    """
    PV group for attenuator system-spanning information.

    This system group implementation is specific to AT2L0.
    """

    async def motor_has_moved(self, idx, value):
        """
        Callback indicating a motor has moved.

        Update the current configuration, if necessary.

        Parameters
        ----------
        idx : int
            Motor index.

        value : int
            Raw state value from control system.
        """
        new_config = list(self.active_config.value)
        new_config[idx] = STATE_FROM_MOTOR.get(value, value)
        if tuple(new_config) != tuple(self.active_config.value):
            self.log.info('Active config changed: %s', new_config)
            await self.active_config.write(new_config)
            await self.active_config_bitmask.write(
                int_array_to_bit_string(new_config)
            )
            await self._update_active_transmission()

        moving = list(self.filter_moving.value)
        # TODO: better handling of moving status
        moving[idx] = 1 if value == 0 else 0
        if tuple(moving) != tuple(self.filter_moving.value):
            await self.filter_moving.write(moving)
            await self.filter_moving_bitmask.write(
                int_array_to_bit_string(moving))

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

    @util.block_on_reentry()
    async def run_calculation(self):
        energy = {
            'Actual': self.energy_actual.value,
            'Custom': self.energy_custom.value,
        }[self.energy_source.value]

        desired_transmission = self.desired_transmission.value
        calc_mode = self.calc_mode.value

        # This is a bit backwards - we reach up to the parent (IOCBase) for
        # transmission calculations and such.
        primary = self.parent

        material_check = primary.check_materials()
        if material_check:
            status, severity = AlarmStatus.NO_ALARM, AlarmSeverity.NO_ALARM
        else:
            status, severity = AlarmStatus.CALC, AlarmSeverity.MAJOR_ALARM

        await self.desired_transmission.alarm.write(status=status,
                                                    severity=severity)
        if not material_check:
            # Don't proceed with calculations if the material check fails.
            return

        await self.last_energy.write(energy)
        await self.last_mode.write(calc_mode)
        await self.last_transmission.write(desired_transmission)

        # Update all of the filters first, to determine their transmission
        # at this energy
        for filter in primary.filters.values():
            await filter.set_photon_energy(energy)

        await self.calculated_transmission.write(
            primary.calculate_transmission()
        )
        await self.calculated_transmission_3omega.write(
            primary.calculate_transmission_3omega()
        )

        # Using the above-calculated transmissions, find the best configuration

        config = calculator.get_best_config_with_material_priority(
            materials=primary.all_filter_materials,
            transmissions=list(primary.all_transmissions),
            material_order=primary.material_order,
            t_des=desired_transmission,
            mode=calc_mode,
        )
        await self.best_config.write(config.filter_states)
        await self.best_config_bitmask.write(
            int_array_to_bit_string(config.filter_states))
        await self.best_config_error.write(
            config.transmission - self.desired_transmission.value
        )
        self.log.info(
            'Energy %s eV with desired transmission %.2g estimated %.2g '
            '(delta %.3g) configuration: %s',
            energy,
            desired_transmission,
            config.transmission,
            self.best_config_error.value,
            config.filter_states,
        )

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
        items = list(zip(self._set_pvs, self.active_config.value,
                         self.best_config.value))
        move_out = [pv for pv, active, best in items
                    if active == State.In and best == State.Out]
        move_in = [pv for pv, active, best in items
                   if active == State.Out and best == State.In]
        if move_in:
            # Move blades IN first, to be safe
            for pv in move_in:
                if state.get(pv, None) == State.In:
                    break
                state[pv] = State.In
                self.log.debug('Moving in %s', pv)
                await self._pv_put_queue.async_put(
                    (pv, STATE_TO_MOTOR[State.In]),
                )
        elif move_out:
            for pv in move_out:
                if state.get(pv, None) == State.Out:
                    break
                state[pv] = State.Out
                self.log.debug('Moving out %s', pv)
                await self._pv_put_queue.async_put(
                    (pv, STATE_TO_MOTOR[State.Out]),
                )

        return bool(move_in or move_out)
