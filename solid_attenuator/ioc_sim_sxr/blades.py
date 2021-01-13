import caproto as ca
from caproto.server import PVGroup, SubGroup, pvproperty

from ..ioc_sim_at2l0.db.fake_blades import (FakeBeckhoffAxisPLC, FakeMotor,
                                            FakeTwinCATStateConfigAll,
                                            pvproperty_with_rbv)


class FakeTwinCATStatePositioner(PVGroup):
    _delay = 0.2

    state_enum_strings = [
        'UNKNOWN', 'OUT',
        'Filter 1', 'Filter 2', 'Filter 3', 'Filter 4',
        'Filter 5', 'Filter 6', 'Filter 7', 'Filter 8'
    ]

    state_get = pvproperty(
        value=0,
        name='GET_RBV',
        record='bo',
        enum_strings=state_enum_strings,
        doc='State information enum',
        dtype=ca.ChannelType.ENUM,
    )

    state_set = pvproperty(
        value=0,
        name='SET',
        enum_strings=state_enum_strings,
        dtype=ca.ChannelType.ENUM,
    )

    error = pvproperty(value=0.0, name='ERR_RBV')
    error_id = pvproperty(value=0, name='ERRID_RBV')
    error_message = pvproperty(dtype=str, name='ERRMSG_RBV')
    busy = pvproperty(value=0, name='BUSY_RBV')
    done = pvproperty(value=0, name='DONE_RBV')
    reset_cmd = pvproperty_with_rbv(dtype=int, name='RESET')
    config = SubGroup(FakeTwinCATStateConfigAll, prefix='')

    @state_set.startup
    async def state_set(self, instance, async_lib):
        self.async_lib = async_lib
        # Start as "out" and not unknown
        await self.state_get.write(1)

    @state_set.putter
    async def state_set(self, instance, value):
        await self.busy.write(1)
        await self.state_get.write(0)
        await self.async_lib.library.sleep(self._delay)
        await self.state_get.write(value)
        await self.busy.write(0)
        await self.done.write(1)


class FakeBeckhoffAxis(PVGroup):
    plc = SubGroup(FakeBeckhoffAxisPLC, prefix=':PLC:')
    state = SubGroup(FakeTwinCATStatePositioner, prefix=':STATE:')
    motor = SubGroup(FakeMotor, velocity=2, prefix='')


class FakeBladeGroup(PVGroup):
    """
    PV group for fake motion axes.

    Blades 1 - 4, with the option to insert one of 8 filters (or remain out).
    """
    axis01 = SubGroup(FakeBeckhoffAxis, prefix='MMS:01')
    axis02 = SubGroup(FakeBeckhoffAxis, prefix='MMS:02')
    axis03 = SubGroup(FakeBeckhoffAxis, prefix='MMS:03')
    axis04 = SubGroup(FakeBeckhoffAxis, prefix='MMS:04')
