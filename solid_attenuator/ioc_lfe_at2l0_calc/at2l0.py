"""
This is the IOC source code for the unique AT2L0, with its 18 in-out filters.
"""
from typing import Dict, List

from caproto import AlarmStatus
from caproto.server import PVGroup, SubGroup
from caproto.server.autosave import AutosaveHelper, RotatingFileManager
from caproto.server.stats import StatusHelper

from .. import calculator, util
from ..filters import InOutFilterGroup
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
    async def run_calculation(self):
        energy = {
            'Actual': self.energy_actual.value,
            'Custom': self.energy_custom.value,
        }[self.energy_source.value]

        desired_transmission = self.desired_transmission.value
        calc_mode = self.calc_mode.value

        material_check = self.check_materials()
        await util.alarm_if(self.desired_transmission, not material_check,
                            AlarmStatus.CALC)
        if not material_check:
            # Don't proceed with calculations if the material check fails.
            return

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


class IOCBase(PVGroup):
    """
    Base for AT2L0 IOC.  This is extended dynamically with SubGroups in
    `create_ioc`.
    """
    filters: Dict[int, InOutFilterGroup]

    prefix: str
    monitor_pvnames: Dict[str, str]

    num_filters = None
    first_filter = 2

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
            InOutFilterGroup, prefix=f':FILTER:{suffix}:', index=index)
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
