import logging

from caproto import ChannelType
from caproto.server import PVGroup, pvproperty

from .. import calculator
from .autosave import autosaved


class FilterGroup(PVGroup):
    """
    PV group for filter metadata.
    """
    def __init__(self, prefix, *, ioc, index, **kwargs):
        super().__init__(prefix, **kwargs)
        self.ioc = ioc
        self.index = index
        # Default to silicon, for now
        self.load_data('Si')
        self.log = logging.getLogger(f'{self.ioc.log.name}.Filter{index}')

    def load_data(self, formula):
        """
        Load the HDF5 dataset containing physical constants
        and photon energy : atomic scattering factor table.
        """
        try:
            self.table = calculator.get_absorption_table(formula=formula)
        except Exception:
            self.table = None
            self.log.exception("Failed to load absorption table for %s",
                               formula)
        else:
            self.log.info("Loaded absorption table for %s", formula)

    material = autosaved(
        pvproperty(value='Si',
                   name='MATERIAL',
                   record='stringin',
                   doc='Filter material',
                   dtype=ChannelType.STRING
                   )
    )

    @material.putter
    async def material(self, instance, value):
        self.load_data(formula=value)

    thickness = autosaved(
        pvproperty(value=1E-6,
                   name='THICKNESS',
                   record='ao',
                   upper_ctrl_limit=1.0,
                   lower_ctrl_limit=0.0,
                   doc='Filter thickness',
                   units='m')
    )

    is_stuck = autosaved(
        pvproperty(value='False',
                   name='IS_STUCK',
                   record='bo',
                   enum_strings=['False', 'True'],
                   doc='Filter is stuck in place',
                   dtype=ChannelType.ENUM)
    )

    closest_eV = pvproperty(name='CLOSE_EV',
                            read_only=True)

    closest_eV_index = pvproperty(name='CLOSE_EV_INDEX',
                                  read_only=True)

    @pvproperty(name='T',
                value=0.5,
                upper_ctrl_limit=1.0,
                lower_ctrl_limit=0.0,
                read_only=True)
    async def transmission(self, instance):
        return self.get_transmission(
            self.current_photon_energy,
            self.thickness.value)

    @pvproperty(name='T_3OMEGA',
                value=0.5,
                upper_alarm_limit=1.0,
                lower_alarm_limit=0.0,
                read_only=True)
    async def transmission_3omega(self, instance):
        return self.get_transmission(
            3 * self.current_photon_energy,
            self.thickness.value)

    @property
    def current_photon_energy(self):
        """Current photon energy in eV."""
        return self.ioc.sys.current_photon_energy

    def get_transmission(self, eV, thickness):
        return calculator.get_transmission(
            photon_energy=eV,
            table=self.table,
            thickness=thickness)

    @thickness.putter
    async def thickness(self, instance, value):
        await self.transmission.write(
            self.get_transmission(self.current_photon_energy, value)
        )
