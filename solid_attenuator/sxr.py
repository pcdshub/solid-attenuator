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
        stuck = self.get_filters(stuck=True, inactive=False, normal=False)
        blades = self.get_filters(stuck=False, inactive=False, normal=True)

        for filter in stuck + blades:
            await filter.set_photon_energy(energy)

        # Using the above-calculated transmissions, find the best configuration
        # Get only the *active* filter transmissions:
        blade_transmissions = [
            [flt.transmission.value for flt in blade.active_filters.values()]
            for blade in blades
        ]

        # Map per-blade array index -> filter index
        # Having removed non-active filters, these may not match 1-1 any more.
        blade_transmission_idx_to_filter_idx = [
            dict(enumerate(blade.active_filters))
            for blade in blades
        ]

        # Account for stuck filters when calculating desired transmission:
        stuck_transmission = self.calculate_stuck_transmission()
        adjusted_tdes = desired_transmission / stuck_transmission

        config = calculator.get_ladder_config(
            blade_transmissions=blade_transmissions,
            t_des=adjusted_tdes,
            mode=calc_mode,
        )

        # Map each blade to the appropriate state:
        # 1. transmission_idx is the index chosen from blade_transmissions
        # 2. idx_map maps from blade_transmissions -> filter index
        # 3. State.from_filter_index() gives a State
        blade_to_state = {
            blade: State.from_filter_index(idx_map.get(transmission_idx))
            for blade, transmission_idx, idx_map
            in zip(blades, config.filter_states,
                   blade_transmission_idx_to_filter_idx)
        }
        blade_to_state.update(
            {blade: blade.get_stuck_state() for blade in stuck}
        )

        # Finally, all blades need to go in their defined order - that is given
        # by `self.filters`:
        config.filter_states = [
            blade_to_state[blade]
            for blade in self.filters.values()
        ]

        # Include the stuck transmission in the result:
        config.transmission *= stuck_transmission
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
