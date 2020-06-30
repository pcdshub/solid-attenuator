from caproto.server import pvproperty, PVGroup
from caproto import ChannelType
from caproto.threading import pyepics_compat as epics
import numpy as np

class FilterGroup(PVGroup):
    """
    PV group for filter metadata.
    """
    thickness = pvproperty(value=0.1,
                           name='THICKNESS',
                           mock_record='ao',
                           upper_alarm_limit=1.0,
                           lower_alarm_limit=0.0,
                           read_only=True,
                           doc='Filter thickness',
                           units='m')

    material = pvproperty(value='Si',
                          name='MATERIAL',
                          mock_record='stringin',
                          doc='Filter material',
                          dtype=ChannelType.STRING)

    is_stuck = pvproperty(value='False',
                          name='IS_STUCK',
                          mock_record='bo',
                          enum_strings=['False', 'True'],
                          doc='Filter is stuck in place',
                          dtype=ChannelType.ENUM)

    closest_eV = pvproperty(name='CLOSE_EV',
                            doc='Closest eV value',
                            mock_record='ao',
                            read_only=True,
                            units='eV')

    @pvproperty(name='EV_RBV',
                read_only=True,
                units='eV')
    async def eV_RBV(self, instance):
        return self.eV.get()

    # cmd_st = pvproperty(value='True',
    #                     name='CMD_STATE',
    #                     mock_record='bo',
    #                     enum_strings=['False', 'True'],
    #                     doc='Commanded filter state')


    def __init__(self, prefix, *, abs_data, eV, ioc, **kwargs):
        super().__init__(prefix, **kwargs)
        self.abs_data = abs_data
        self.ioc = ioc
        self.eV = eV

    def load_data(self, material):
        """
        Load the HDF5 dataset containing physical constants
        and photon energy : atomic scattering factor table.
        """
        print("Loading absorption table for {}...".format(material))
        self.table = np.asarray(self.abs_data['{}_table'.format(material)])
        self.constants = np.asarray(self.abs_data['{}_constants'.format(material)])
        self.eV_min = self.table[0,0]
        self.eV_max = self.table[-1,0]
        self.eV_inc = (self.table[-1,0] - self.table[0,0])/len(self.table[:,0])
        print("Absorption table successfully loaded.")
        return self.constants, self.table, self.eV_min, self.eV_inc, self.eV_max

    async def eV_callback(self, value, **kwargs):
        await self.eV_RBV.write(value)

    @thickness.putter
    async def thickness(self, instance, value):
        if value < 0:
          raise ValueError('Thickness must be '
                           +'a positive number')
    
    @material.putter
    async def material(self, instance, value):
        if str(value).lower() not in ['si','c']:
            raise ValueError('{} is not an available '
                             +'material'.format(value))
        self.load_data(value)

    @material.startup
    async def material(self, instance, value):
        await instance.write("Si")
