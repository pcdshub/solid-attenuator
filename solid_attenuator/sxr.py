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
from typing import Dict

from caproto.server import PVGroup, SubGroup
from caproto.server.autosave import AutosaveHelper, RotatingFileManager
from caproto.server.stats import StatusHelper

from . import calculator, util
from .filters import EightFilterGroup
from .system import SystemGroupBase
from .util import State


class SystemGroup(SystemGroupBase):
    """
    PV group for attenuator system-spanning information.

    This system group implementation is specific to AT2L0.
    """

    @util.block_on_reentry()
    async def run_calculation(self):
        energy = {
            'Actual': self.energy_actual.value,
            'Custom': self.energy_custom.value,
        }[self.energy_source.value]

        desired_transmission = self.desired_transmission.value
        calc_mode = self.calc_mode.value

        # material_check = self.check_materials()
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
        for filter in self.filters.values():
            await filter.set_photon_energy(energy)

        await self.calculated_transmission.write(
            self.calculate_transmission()
        )
        await self.calculated_transmission_3omega.write(
            self.calculate_transmission_3omega()
        )

        # Using the above-calculated transmissions, find the best configuration
        # Get only the *active* filter transmissions:
        blade_transmissions = [
            [flt.transmission.value
             for flt in blade.active_filters.values()]
            for blade in self.filters.values()
        ]

        # Map per-blade array index -> filter index
        # Having removed non-active filters, these may not match 1-1 any more.
        blade_transmission_idx_to_filter_idx = [
            dict(enumerate(blade.active_filters))
            for blade in self.filters.values()
        ]

        config = calculator.get_ladder_config(
            blade_transmissions=blade_transmissions,
            t_des=desired_transmission,
            mode=calc_mode,
        )

        # Use the transmission array indices to get back a State:
        best_config = [
            State.from_filter_index(idx_map.get(transmission_idx))
            for transmission_idx, idx_map
            in zip(config.filter_states, blade_transmission_idx_to_filter_idx)
        ]

        await self.best_config.write(best_config)
        await self.best_config_bitmask.write(
            util.int_array_to_bit_string(
                [state.is_inserted for state in best_config]
            )
        )
        await self.best_config_error.write(
            config.transmission - self.desired_transmission.value
        )
        self.log.info(
            'Energy %s eV with desired transmission %.2g estimated %.2g '
            '(delta %.3g) mode: %s configuration: %s',
            energy,
            desired_transmission,
            config.transmission,
            self.best_config_error.value,
            calc_mode,
            config.filter_states,
        )


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
