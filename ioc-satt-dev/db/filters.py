from caproto import ChannelType
from caproto.server import PVGroup, pvproperty

from .. import calculator


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

    def load_data(self, formula):
        """
        Load the HDF5 dataset containing physical constants
        and photon energy : atomic scattering factor table.
        """
        self.log.info("Loading absorption table for %s...", formula)
        self.table = calculator.get_absorption_table(formula=formula)
        self.eV_min = self.table[0, 0]
        self.eV_max = self.table[-1, 0]
        self.eV_inc = (self.eV_max - self.eV_min) / len(self.table[:, 0])
        self.table_kwargs = {
            'eV_min': self.eV_min,
            'eV_max': self.eV_max,
            'eV_inc': self.eV_inc,
            'table': self.table
        }
        self.log.info("Absorption table successfully loaded.")

    material = pvproperty(value='Si',
                          name='MATERIAL',
                          record='stringin',
                          doc='Filter material',
                          dtype=ChannelType.STRING)

    @material.putter
    async def material(self, instance, value):
        self.load_data(formula=value)

    thickness = pvproperty(value=1E-6,
                           name='THICKNESS',
                           record='ao',
                           upper_ctrl_limit=1.0,
                           lower_ctrl_limit=0.0,
                           doc='Filter thickness',
                           units='m')

    is_stuck = pvproperty(value='False',
                          name='IS_STUCK',
                          record='bo',
                          enum_strings=['False', 'True'],
                          doc='Filter is stuck in place',
                          dtype=ChannelType.ENUM)

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
