from caproto import ChannelType
from caproto.server import PVGroup, pvproperty
from caproto.server.autosave import autosaved

from .. import calculator


class FilterGroup(PVGroup):
    """
    PV group for filter metadata.
    """
    def __init__(self, prefix, *, index, **kwargs):
        super().__init__(prefix, **kwargs)
        self.index = index
        self._last_photon_energy = 0.0
        # Default to silicon, for now
        self.load_data('Si')

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
        pvproperty(
            value='Si',
            name='Material',
            record='stringin',
            doc='Filter material',
            dtype=ChannelType.STRING
        )
    )

    @material.putter
    async def material(self, instance, value):
        self.load_data(formula=value)

    thickness = autosaved(
        pvproperty(
            value=1E-6,
            name='Thickness',
            record='ao',
            upper_ctrl_limit=1.0,
            lower_ctrl_limit=0.0,
            doc='Filter thickness',
            units='m',
            precision=7,
        )
    )

    is_stuck = autosaved(
        pvproperty(
            value='False',
            name='IsStuck',
            record='bo',
            enum_strings=['False', 'True'],
            doc='Filter is stuck in place',
            dtype=ChannelType.ENUM
        )
    )

    closest_energy = pvproperty(
        value=0.0,
        name='ClosestEnergy_RBV',
        read_only=True,
        precision=1,
    )

    closest_index = pvproperty(
        name='ClosestIndex_RBV',
        read_only=True,
    )

    transmission = pvproperty(
        name='Transmission_RBV',
        value=0.5,
        upper_ctrl_limit=1.0,
        lower_ctrl_limit=0.0,
        read_only=True,
        precision=3,
    )

    transmission_3omega = pvproperty(
        name='Transmission3Omega_RBV',
        value=0.5,
        upper_alarm_limit=1.0,
        lower_alarm_limit=0.0,
        read_only=True,
        precision=3,
    )

    async def set_photon_energy(self, energy_ev):
        self._last_photon_energy = energy_ev
        closest_energy, i = calculator.find_closest_energy(
            energy_ev, self.table)

        await self.closest_index.write(i)
        await self.closest_energy.write(closest_energy)

        await self.transmission.write(
            self.get_transmission(energy_ev, self.thickness.value)
        )
        await self.transmission_3omega.write(
            self.get_transmission(3.*energy_ev, self.thickness.value)
        )

    def get_transmission(self, eV, thickness):
        return calculator.get_transmission(
            photon_energy=eV,
            table=self.table,
            thickness=thickness)

    @thickness.putter
    async def thickness(self, instance, value):
        energy = self._last_photon_energy
        await self.transmission.write(
            self.get_transmission(energy, value)
        )
