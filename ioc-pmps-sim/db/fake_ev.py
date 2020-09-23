from caproto.server import PVGroup, pvproperty


class FakeEVGroup(PVGroup):
    """
    PV group for fake photon energy readback
    """
    fake_eV = pvproperty(value=9500,
                         name='EV',
                         record='ao',
                         upper_alarm_limit=25000,
                         lower_alarm_limit=1000,
                         lower_ctrl_limit=0,
                         doc='Fake photon energy PV for attenuator testing',
                         units='eV'
                         )
