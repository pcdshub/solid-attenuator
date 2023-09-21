from typing import Dict, Optional

from caproto import ChannelType
from caproto.server import PVGroup, SubGroup, pvproperty
from caproto.server.autosave import autosaved

from . import calculator
from .util import State

__all__ = ['InOutFilterGroup', 'EightFilterGroup']


class FilterGroup(PVGroup):
    """
    PVGroup for a single filter - with a specific material and thickness.

    Parameters
    ----------
    prefix : str
        PV prefix.

    index : int
        Index of the filter in the system.
    """

    def __init__(self, prefix, index, **kwargs):
        super().__init__(prefix, **kwargs)
        self._last_photon_energy = 0.0
        self.index = index
        # Default to silicon, for now
        self.load_data('Si')

    def __repr__(self):
        return (
            f'<{self.__class__.__name__} '
            f'({self.index}) '
            f'{self.material.value} '
            f'{self.thickness.value} um '
            f'T={self.transmission.value}'
            f'>'
        )

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
            dtype=ChannelType.STRING,
            alarm_group="material",
        )
    )

    thickness = autosaved(
        pvproperty(
            value=10.,
            name='Thickness',
            record='ao',
            lower_ctrl_limit=0.0,
            upper_ctrl_limit=900000.0,
            doc='Filter thickness',
            units='um',
            precision=1,
            alarm_group="material",
        )
    )

    closest_energy = pvproperty(
        value=0.0,
        name='ClosestEnergy_RBV',
        read_only=True,
        precision=1,
        alarm_group="material",
    )

    closest_index = pvproperty(
        name='ClosestIndex_RBV',
        read_only=True,
        alarm_group="energy_based",
    )

    transmission = pvproperty(
        name='Transmission_RBV',
        value=0.5,
        upper_ctrl_limit=1.0,
        lower_ctrl_limit=0.0,
        read_only=True,
        precision=3,
        alarm_group="energy_based",
    )

    transmission_3omega = pvproperty(
        name='Transmission3Omega_RBV',
        value=0.5,
        upper_alarm_limit=1.0,
        lower_alarm_limit=0.0,
        read_only=True,
        precision=3,
        alarm_group="energy_based",
    )

    # What does it mean to be inactive but stuck?
    # stuck,     inactive -> ignore entirely
    # not stuck, inactive -> ignore entirely
    # stuck,       active -> stuck, include in transmission
    # not stuck,   active -> use in calculations
    active = autosaved(
        pvproperty(
            value='True',
            name='Active',
            record='bo',
            enum_strings=['False', 'True'],
            doc='Filter should be used in calculations',
            dtype=ChannelType.ENUM,
            alarm_group="material",
        )
    )

    # TODO: intention is to say it's stuck in/out/etc depending on the state
    # better name would be "StuckAtState"
    # NOTE: this is a PV API change for AT2L0, but it's not currently necessary
    # as of the time of writing, fortunately.
    is_stuck = autosaved(
        pvproperty(
            value='Not stuck',
            name='IsStuck',
            record='mbbo',
            doc='Stuck at indicated state',
            enum_strings=['Not stuck', 'Out', 'In_01', 'In_02', 'In_03',
                          'In_04', 'In_05', 'In_06', 'In_07', 'In_08',
                          'In_09'],
            dtype=ChannelType.ENUM,
            alarm_group="stuck",
        )
    )

    def get_stuck_state(self) -> State:
        """If marked as stuck, get the stuck State."""
        return State(self.is_stuck.enum_strings.index(self.is_stuck.value))

    async def set_photon_energy(self, energy_ev):
        """
        Set the current photon energy to determine transmission.

        Parameters
        ----------
        energy_ev : float
            The photon energy [eV].
        """
        self._last_photon_energy = energy_ev
        closest_energy, i = calculator.find_closest_energy(
            energy_ev, self.table)

        await self.closest_index.write(i)
        await self.closest_energy.write(closest_energy)
        await self.transmission.write(self.get_transmission(energy_ev))
        await self.transmission_3omega.write(
            self.get_transmission(3.*energy_ev))

    def get_transmission(self, photon_energy_ev: float):
        """
        Get the transmission for the given photon energy based on the material
        and thickness configured.

        Parameters
        ----------
        energy_ev : float
            The photon energy [eV].

        Returns
        -------
        transmission : float
            Normalized transmission value.
        """
        return calculator.get_transmission(
            photon_energy=photon_energy_ev,
            table=self.table,
            thickness=self.thickness.value * 1e-6,  # um -> meters
        )

    @material.putter
    async def material(self, instance, value):
        """
        Update the material - load the table and update transmission values.
        """
        self.load_data(formula=value)
        if (self.table is not None and self.thickness.value > 0.0 and
                self._last_photon_energy > 0.0):
            await self.set_photon_energy(self._last_photon_energy)

    @thickness.putter
    async def thickness(self, instance, value):
        """
        Update the thickness
        """
        energy = self._last_photon_energy
        await self.thickness.write(value, verify_value=False)
        await self.transmission.write(self.get_transmission(energy))


class InOutFilterGroup(FilterGroup):
    """
    PVGroup for a single in-out filter blade.

    Parameters
    ----------
    prefix : str
        PV prefix.

    index : int
        Index of the filter in the system.
    """

    async def set_inserted_filter_state(self, state: State):
        ...


class EightFilterGroup(FilterGroup):
    """
    PVGroup for a single blade with 8 spots for filters.

    This inherits and overrides methods from :class:`FilterGroup`.  If a filter
    is selected, values such as transmission and material will reflect those of
    the selected filter.

    .. note::

        As this is the standard holder for AT1K4 and similar attenuators, a
        dynamic "NFilterGroup" is currently unnecessary.

    Parameters
    ----------
    prefix : str
        PV prefix.

    index : int
        Index of the blade in the system.
    """

    N_FILTERS = 8

    def __init__(self, prefix, *, index, **kwargs):
        self.table = None
        super().__init__(prefix, index=index, **kwargs)
        self._last_photon_energy = 0.0
        self.filters = {
            idx: getattr(self, f'filter{idx:02d}')
            for idx in range(1, self.N_FILTERS + 1)
        }

        # TODO: caproto pvproperty doesn't really work this way, sadly:
        # self.material.read_only = True
        # self.thickness.read_only = True

    filter01 = SubGroup(FilterGroup, prefix='FILTER:01:', index=1)
    filter02 = SubGroup(FilterGroup, prefix='FILTER:02:', index=2)
    filter03 = SubGroup(FilterGroup, prefix='FILTER:03:', index=3)
    filter04 = SubGroup(FilterGroup, prefix='FILTER:04:', index=4)
    filter05 = SubGroup(FilterGroup, prefix='FILTER:05:', index=5)
    filter06 = SubGroup(FilterGroup, prefix='FILTER:06:', index=6)
    filter07 = SubGroup(FilterGroup, prefix='FILTER:07:', index=7)
    filter08 = SubGroup(FilterGroup, prefix='FILTER:08:', index=8)

    inserted_filter_index = pvproperty(
        name='InsertedFilter_RBV',
        value=0,
        read_only=True,
    )

    def load_data(self, formula):
        # Stub load_data, as `self.table` is not used here, instead relying
        # on the inserted filter's information.
        ...

    @property
    def inserted_filter_state(self) -> State:
        """The current filter state, according to inserted_filter_index."""
        if self.is_stuck.value != 'Not stuck':
            return self.get_stuck_state()

        return State(self.inserted_filter_index.value)

    @property
    def inserted_filter(self) -> Optional[FilterGroup]:
        """The currently inserted filter."""
        return self.filters.get(self.inserted_filter_state.filter_index, None)

    def get_transmission(self, photon_energy_ev):
        """
        Get the transmission for the given photon energy based on the material
        and thickness configured.

        Parameters
        ----------
        energy_ev : float
            The photon energy [eV].

        Returns
        -------
        transmission : float
            Normalized transmission value.
        """
        flt = self.inserted_filter
        if flt is None:
            return 1.0
        return flt.get_transmission(photon_energy_ev)

    async def set_inserted_filter_state(self, state: State):
        await self.inserted_filter_index.write(int(state))
        await self._update()

    async def _update(self):
        """Proxy the inserted filter's information to transmission, etc."""
        flt = self.inserted_filter

        if flt is None:
            transmission = 1.0
            transmission_3omega = 1.0
            closest_index = 0
            closest_energy = 0.0
            thickness = 0.0
            material = 'None'
        else:
            transmission = flt.transmission.value
            transmission_3omega = flt.transmission_3omega.value
            closest_index = flt.closest_index.value
            closest_energy = flt.closest_energy.value
            thickness = flt.thickness.value
            material = flt.material.value

        await self.transmission.write(transmission, verify_value=False)
        await self.transmission_3omega.write(transmission_3omega,
                                             verify_value=False)
        await self.closest_index.write(closest_index, verify_value=False)
        await self.closest_energy.write(closest_energy, verify_value=False)
        await self.thickness.write(thickness, verify_value=False)
        await self.material.write(material, verify_value=False)

    async def set_photon_energy(self, energy_ev: float):
        """
        Set the current photon energy to determine transmission.

        Parameters
        ----------
        energy_ev : float
            The photon energy [eV].
        """
        self._last_photon_energy = energy_ev
        for flt in self.filters.values():
            await flt.set_photon_energy(energy_ev)
        await self._update()

    @property
    def active_filters(self) -> Dict[int, FilterGroup]:
        """A dictionary of all filters that are in active, working order."""
        return {
            idx: filt for idx, filt in self.filters.items()
            if filt.active.value == "True"
        }
