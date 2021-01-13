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
from caproto.server import SubGroup, expand_macros
from caproto.server.autosave import RotatingFileManager

from . import calculator, util
from .filters import EightFilterGroup
from .ioc import IOCBase
from .system import SystemGroupBase
from .util import State


class SystemGroup(SystemGroupBase):
    """
    PV group for attenuator system-spanning information.

    This system group implementation applies to SXR solid attenuators, such as
    AT1K4.
    """

    @util.block_on_reentry()
    async def run_calculation(self, energy: float, desired_transmission: float,
                              calc_mode: str
                              ) -> calculator.Config:
        # Update all of the filters first, to determine their transmission
        # at this energy
        for filter in self.filters.values():
            await filter.set_photon_energy(energy)

        # TODO: handling for stuck filters? active is below...

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
        return config


def create_ioc(prefix, filter_group, macros, **ioc_options):
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
    subgroups['sys'] = SubGroup(SystemGroup, prefix=':SYS:')

    low_index = min(filter_index_to_attribute)
    high_index = max(filter_index_to_attribute)
    motor_prefix = expand_macros(macros["motor_prefix"], macros)
    motor_prefixes = {
        idx: f'{motor_prefix}{idx:02d}:STATE'
        for idx in range(low_index, high_index + 1)
    }

    IOCMain = IOCBase.create_ioc_class(filter_index_to_attribute, subgroups,
                                       motor_prefixes)
    ioc = IOCMain(prefix=prefix, macros=macros, **ioc_options)

    autosave_path = expand_macros(macros['autosave_path'], macros)
    ioc.autosave_helper.filename = autosave_path
    ioc.autosave_helper.file_manager = RotatingFileManager(autosave_path)
    return ioc
