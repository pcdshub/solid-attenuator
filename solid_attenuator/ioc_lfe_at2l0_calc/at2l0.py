"""
This is the IOC source code for the unique AT2L0, with its 18 in-out filters.
"""
from typing import List

from caproto.server import SubGroup, expand_macros
from caproto.server.autosave import RotatingFileManager

from .. import calculator, util
from ..filters import InOutFilterGroup
from ..ioc import IOCBase
from ..system import SystemGroupBase
from ..util import State


class SystemGroup(SystemGroupBase):
    """
    PV group for attenuator system-spanning information.

    This system group implementation is specific to AT2L0.
    """
    @property
    def material_order(self) -> List[str]:
        """Material prioritization."""
        # Hard-coded for now.
        return ['C', 'Si']

    def check_materials(self) -> bool:
        """Ensure the materials specified are OK according to the order."""
        bad_materials = set(self.material_order).symmetric_difference(
            set(self.all_filter_materials)
        )
        if bad_materials:
            self.log.error(
                'Materials not set properly! May not calculate correctly. '
                'Potentially bad materials: %s', bad_materials
            )
        return not bool(bad_materials)

    @util.block_on_reentry()
    async def run_calculation(self, energy: float, desired_transmission: float,
                              calc_mode: str
                              ) -> calculator.Config:
        if not self.check_materials():
            raise util.MisconfigurationError(
                f"Materials specified outside of supported ones.  AT2L0 "
                f"requires that diamond filters be inserted prior to silicon "
                f"filters, but the following were found:"
                f"{self.all_filter_materials}"
            )

        # Update all of the filters first, to determine their transmission
        # at this energy
        stuck = self.get_filters(stuck=True, inactive=False, normal=False)
        filters = self.get_filters(stuck=False, inactive=False, normal=True)

        materials = list(flt.material.value for flt in filters)
        transmissions = list(flt.transmission.value for flt in filters)
        for filter in stuck + filters:
            await filter.set_photon_energy(energy)

        stuck_transmission = self.calculate_stuck_transmission()

        # Account for stuck filters when calculating desired transmission:
        adjusted_tdes = desired_transmission / stuck_transmission

        # Using the above-calculated transmissions, find the best configuration
        config = calculator.get_best_config_with_material_priority(
            materials=materials,
            transmissions=transmissions,
            material_order=self.material_order,
            t_des=adjusted_tdes,
            mode=calc_mode,
        )

        filter_to_state = {
            flt: State.from_filter_index(idx)
            for flt, idx in zip(filters, config.filter_states)
        }
        filter_to_state.update(
            {flt: flt.get_stuck_state() for flt in stuck}
        )

        # Reassemble filter states in order:
        config.filter_states = [
            # Inactive filters will be implicitly marked as "Out" here.
            filter_to_state.get(flt, State.Out)
            for flt in self.filters.values()
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
            InOutFilterGroup, prefix=f':FILTER:{suffix}:', index=index)
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
