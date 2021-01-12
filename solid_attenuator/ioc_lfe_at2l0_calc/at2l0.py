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
        for filter in self.filters.values():
            await filter.set_photon_energy(energy)

        await self.calculated_transmission.write(
            self.calculate_transmission()
        )
        await self.calculated_transmission_3omega.write(
            self.calculate_transmission_3omega()
        )

        # Using the above-calculated transmissions, find the best configuration
        config = calculator.get_best_config_with_material_priority(
            materials=self.all_filter_materials,
            transmissions=list(self.all_transmissions),
            material_order=self.material_order,
            t_des=desired_transmission,
            mode=calc_mode,
        )
        await self.best_config.write(
            [State.from_filter_index(idx) for idx in config.filter_states]
        )
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
