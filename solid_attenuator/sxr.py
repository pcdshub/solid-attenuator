"""
IOC source for SXR solid attenuators with 4 blades * up to 8 filters.

This is intended to be used for the following attenuators:

| Name        | Instrument | Area | Z [m] |
|-------------|------------|------|-------|
| AT1K4-SOLID | TMO        | FEE  | 748   |
| AT1K2-SOLID | NEH 2.2    | H2.2 | 784   |
| AT2K2-SOLID | NEH 2.2    | H2.2 | 788.8 |
| AT1K3-SOLID | TXI        | H1.1 | ~763  |
"""
import enum
from typing import Dict, List, Optional

import numpy as np
# from caproto import AlarmStatus
from caproto.server import PVGroup, SubGroup
from caproto.server.autosave import AutosaveHelper, RotatingFileManager
from caproto.server.stats import StatusHelper

from . import calculator, util
from .filters import EightFilterGroup
from .system import SystemGroupBase


class State(enum.IntEnum):
    """
    State which matches that of the motion IOC.
    """
    # 'Moving' is also: "unknown" or "between states"
    Moving = 0

    # 'Out' is fixed at 1:
    Out = 1

    # And any "in" states follow:
    In_01 = 2
    In_02 = 3
    In_03 = 4
    In_04 = 5
    In_05 = 6
    In_06 = 7
    In_07 = 8
    In_08 = 9
    In_09 = 10

    @property
    def filter_index(self) -> Optional[int]:
        """The one-based filter index, if inserted."""
        if not self.is_inserted:
            return None
        return self.value - 1

    @property
    def is_inserted(self) -> bool:
        """Is a filter inserted?"""
        return self not in {State.Moving, State.Out}

    @property
    def is_moving(self) -> bool:
        """Is the blade moving?"""
        return self == State.Moving

    def __repr__(self):
        return self.name


class SystemGroup(SystemGroupBase):
    """
    PV group for attenuator system-spanning information.

    This system group implementation is specific to AT2L0.
    """

    async def motor_has_moved(self, filter_idx, value):
        """
        Callback indicating a motor has moved.

        Update the current configuration, if necessary.

        Parameters
        ----------
        filter_idx : int
            Filter index (not zero-based).

        value : int
            Raw state value from control system.
        """
        array_idx = filter_idx - self.parent.first_filter
        state = State(int(value))

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

        await self.parent.filters[filter_idx].set_inserted_filter(state)

    async def _update_active_transmission(self):
        config = tuple(self.active_config.value)
        offset = self.parent.first_filter
        working_filters = self.parent.working_filters

        transm = np.zeros_like(config) * np.nan
        transm3 = np.zeros_like(config) * np.nan
        for idx, filt in working_filters.items():
            zero_index = idx - offset
            if State(config[zero_index]).is_inserted:
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

        # material_check = primary.check_materials()
        # await util.alarm_if(self.desired_transmission, not material_check,
        #                     AlarmStatus.CALC)
        # if not material_check:
        #     # Don't proceed with calculations if the material check fails.
        #     return

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
            util.int_array_to_bit_string(config.filter_states))
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
        items = [
            (pv, State(active), State(best))
            for pv, active, best in
            zip(self._set_pvs, self.active_config.value,
                self.best_config.value)
        ]

        move_out = {
            pv: best
            for pv, active, best in items
            if active.is_inserted and best == State.Out
        }
        move_in = {
            pv: best
            for pv, active, best in items
            if active == State.Out and best.is_inserted
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


class IOCBase(PVGroup):
    """
    Base for SXR attenuator IOCs.  This is extended dynamically with SubGroups
    in `create_ioc`.
    """
    filters: Dict[int, EightFilterGroup]
    prefix: str
    monitor_pvnames: Dict[str, str]

    num_filters = None
    first_filter = 1

    def __init__(self, prefix, *, eV, pmps_run, pmps_tdes,
                 filter_index_to_attribute,
                 motors,
                 **kwargs):
        super().__init__(prefix, **kwargs)
        self.prefix = prefix
        self.filters = {idx: getattr(self, attr)
                        for idx, attr in filter_index_to_attribute.items()}
        self.monitor_pvnames = dict(
            ev=eV,
            pmps_run=pmps_run,
            pmps_tdes=pmps_tdes,
            motors=motors,
        )

    autosave_helper = SubGroup(AutosaveHelper)
    stats_helper = SubGroup(StatusHelper, prefix=':STATS:')
    sys = SubGroup(SystemGroup, prefix=':SYS:')

    @property
    def working_filters(self):
        """
        A dictionary of all filters that are in working order.

        That is to say, filters that are marked as active and not stuck.
        """
        return {
            idx: filt for idx, filt in self.filters.items()
            if filt.is_stuck.value != "True" and filt.active.value == "True"
        }

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
    def all_filter_materials(self) -> List[str]:
        """All filter materials in a list."""
        return [flt.material.value for flt in self.filters.values()]


def create_ioc(prefix,
               *,
               eV_pv,
               motor_prefix,
               pmps_run_pv,
               pmps_tdes_pv,
               filter_group,
               autosave_path,
               **ioc_options):
    """IOC Setup."""

    filter_index_to_attribute = {
        index: f'filter_{suffix}'
        for index, suffix in filter_group.items()
    }

    subgroups = {
        filter_index_to_attribute[index]: SubGroup(
            EightFilterGroup, prefix=f':AXIS:{suffix}:', index=index)
        for index, suffix in filter_group.items()
    }

    low_index = min(filter_index_to_attribute)
    high_index = max(filter_index_to_attribute)
    motor_prefixes = {
        idx: f'{motor_prefix}{idx:02d}:STATE'
        for idx in range(low_index, high_index + 1)
    }

    motors = {
        'get': [f'{motor}:GET_RBV' for idx, motor in motor_prefixes.items()],
        'set': [f'{motor}:SET' for idx, motor in motor_prefixes.items()],
        'error': [f'{motor}:ERR_RBV' for idx, motor in motor_prefixes.items()],
    }

    class IOCMain(IOCBase):
        num_filters = len(filter_index_to_attribute)
        first_filter = min(filter_index_to_attribute)
        locals().update(**subgroups)

    ioc = IOCMain(prefix=prefix,
                  eV=eV_pv,
                  filter_index_to_attribute=filter_index_to_attribute,
                  motors=motors,
                  pmps_run=pmps_run_pv,
                  pmps_tdes=pmps_tdes_pv,
                  **ioc_options)

    ioc.autosave_helper.filename = autosave_path
    ioc.autosave_helper.file_manager = RotatingFileManager(autosave_path)
    return ioc
