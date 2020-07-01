from caproto.server import pvproperty, PVGroup
from caproto import ChannelType
from caproto.threading import pyepics_compat as epics
import numpy as np

class FilterGroup(PVGroup):
    """
    PV group for filter metadata.
    """
    async def load_data(self, instance, value):
        """
        Load the HDF5 dataset containing physical constants
        and photon energy : atomic scattering factor table.
        """
        print("Loading absorption table for {}...".format(value))
        material_str = str(value)
        if material_str not in ['Si','C']:
            raise ValueError('{} is not an available '
                             +'material'.format(material_str))
        self.table = np.asarray(self.abs_data['{}_table'.format(material_str)])
        self.constants = np.asarray(
            self.abs_data['{}_constants'.format(material_str)])
        self.eV_min = self.table[0,0]
        self.eV_max = self.table[-1,0]
        self.eV_inc = (self.table[-1,0] - self.table[0,0])/len(self.table[:,0])
        print("Absorption table successfully loaded.")
        return value

    async def get_closest_eV(self, instance):
        eV = self.eV.get()
        closest_eV, i = self.calc_closest_eV(eV)
        await instance.write(closest_eV)
        return closest_eV

    async def get_closest_eV_index(self, instance):
        eV = self.eV.get()
        closest_eV, i = self.calc_closest_eV(eV)
        await instance.write(closest_eV)
        return closest_eV

    material = pvproperty(value='Si',
                          put=load_data,
                          name='MATERIAL',
                          mock_record='stringin',
                          doc='Filter material',
                          dtype=ChannelType.STRING)

    thickness = pvproperty(value=1E-6,
                           name='THICKNESS',
                           mock_record='ao',
                           upper_alarm_limit=1.0,
                           lower_alarm_limit=0.0,
                           read_only=True,
                           doc='Filter thickness',
                           units='m')

    is_stuck = pvproperty(value='False',
                          name='IS_STUCK',
                          mock_record='bo',
                          enum_strings=['False', 'True'],
                          doc='Filter is stuck in place',
                          dtype=ChannelType.ENUM)

    closest_eV = pvproperty(name='CLOSE_EV',
                            get=get_closest_eV,
                            read_only=True)

    closest_eV_index = pvproperty(name='CLOSE_EV_INDEX',
                                  get=get_closest_eV_index,
                                  read_only=True)

    @pvproperty(name='EV_RBV',
                read_only=True,
                units='eV')
    async def eV_RBV(self, instance):
        eV = self.eV.get()
        closest_eV, i = self.calc_closest_eV(eV)
        await self.closest_eV_index.write(i)
        await self.closest_eV.write(closest_eV)
        return eV

    @pvproperty(name='T',
                value=0.5,
                upper_alarm_limit=1.0,
                lower_alarm_limit=0.0,
                read_only=True)
    async def transmission(self, instance):
        closest_eV_index = self.calc_closest_eV(self.eV.get())[1]
        return np.exp(-self.table[closest_eV_index,2]*self.thickness.value)

    def __init__(self, prefix, *, abs_data, eV, ioc, **kwargs):
        super().__init__(prefix, **kwargs)
        self.abs_data = abs_data
        self.ioc = ioc
        self.eV = eV
    
    def calc_closest_eV(self, eV):
        i = int(np.rint((eV - self.eV_min)/self.eV_inc))
        if i < 0:
            i = 0 # Use lowest tabulated value.
        if i > self.table.shape[0]:
            i = -1 # Use greatest tabulated value.
        closest_eV = self.table[i,0]
        return closest_eV, i

    @thickness.putter
    async def thickness(self, instance, value):
        if value < 0:
          raise ValueError('Thickness must be '
                           +'a positive number')

    @material.startup
    async def material(self, instance, value):
        await instance.write("Si")
    
    @closest_eV.startup
    async def closest_eV(self, instance, value):
        closest_eV, i = self.calc_closest_eV(self.eV.get())
        await instance.write(closest_eV)

    @closest_eV_index.startup
    async def closest_eV_index(self, instance, value):
        closest_eV, i = self.calc_closest_eV(self.eV.get())
        await instance.write(i)
