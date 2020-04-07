from caproto.server import pvproperty, PVGroup
from caproto import ChannelType


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
                          read_only=True,
                          dtype=ChannelType.STRING)

    is_stuck = pvproperty(value='False',
                          name='IS_STUCK',
                          mock_record='bo',
                          enum_strings=['False', 'True'],
                          doc='Filter is stuck in place',
                          dtype=ChannelType.ENUM)

    cmd_st = pvproperty(value='True',
                        name='CMD_STATE',
                        mock_record='bo',
                        enum_strings=['False', 'True'],
                        doc='Commanded filter state')


    def __init__(self, prefix, *, ioc, **kwargs):
        super().__init__(prefix, **kwargs)
        self.ioc = ioc

    @thickness.putter
    async def thickness(self, instance, value):
        if value < 0:
          raise ValueError('Thickness must be '
                           +'a positive number')
    
    @material.putter
    async def material(self, instance, value):
        if value.lower() not in ['si','c']:
            raise ValueError('{} is not an available '
                             +'material'.format(value))
