from caproto.server import PVGroup, SubGroup, get_pv_pair_wrapper, pvproperty
from caproto.server.records import MotorFields


def broadcast_precision_to_fields(record):
    precision = record.precision
    for field, prop in record.field_inst.pvdb.items():
        # HACK: this shouldn't be done normally
        if 'precision' in prop._data:
            prop._data['precision'] = precision


class FakeMotor(PVGroup):
    motor = pvproperty(value=0.0, name='', record='motor',
                       precision=3)

    def __init__(self, *args,
                 velocity=0.1,
                 precision=3,
                 acceleration=1.0,
                 resolution=1e-6,
                 tick_rate_hz=10.,
                 **kwargs):
        super().__init__(*args, **kwargs)
        self.tick_rate_hz = tick_rate_hz
        self.defaults = {
            'velocity': velocity,
            'precision': precision,
            'acceleration': acceleration,
            'resolution': resolution,
        }

    @motor.startup
    async def motor(self, instance, async_lib):
        self.async_lib = async_lib

        await self.motor.write_metadata(precision=self.defaults['precision'])
        broadcast_precision_to_fields(self.motor)

        fields = self.motor.field_inst  # type: MotorFields
        await fields.velocity.write(self.defaults['velocity'])
        await fields.seconds_to_velocity.write(self.defaults['acceleration'])
        await fields.motor_step_size.write(self.defaults['resolution'])

        while True:
            dwell = 1. / self.tick_rate_hz
            target_pos = self.motor.value
            diff = (target_pos - fields.user_readback_value.value)
            # compute the total movement time based an velocity
            total_time = abs(diff / fields.velocity.value)
            # compute how many steps, should come up short as there will
            # be a final write of the return value outside of this call
            num_steps = int(total_time // dwell)

            if abs(diff) < 1e-9:
                await async_lib.library.sleep(dwell)
                continue

            await fields.done_moving_to_value.write(1)
            await fields.done_moving_to_value.write(0)
            await fields.motor_is_moving.write(1)

            readback = fields.user_readback_value.value
            step_size = diff / num_steps if num_steps > 0 else 0.0
            resolution = max((fields.motor_step_size.value, 1e-10))
            for _ in range(num_steps):
                if fields.stop.value != 0:
                    await fields.stop.write(0)
                    await self.motor.write(readback)
                    break
                if fields.stop_pause_move_go.value == 'Stop':
                    await self.motor.write(readback)
                    break

                readback += step_size
                raw_readback = readback / resolution
                await fields.user_readback_value.write(readback)
                await fields.dial_readback_value.write(readback)
                await fields.raw_readback_value.write(raw_readback)
                await async_lib.library.sleep(dwell)
            else:
                # Only executed if we didn't break
                await fields.user_readback_value.write(target_pos)

            await fields.motor_is_moving.write(0)
            await fields.done_moving_to_value.write(1)


class FakeBeckhoffAxisPLC(PVGroup):
    status = pvproperty(value='No error', name='sErrorMessage_RBV')
    err_code = pvproperty(value=0, name='nErrorId_RBV')
    cmd_err_reset = pvproperty(value=0, name='bReset')
    cmd_err_reset_rbv = pvproperty(value=0, name='bReset_RBV')


pvproperty_with_rbv = get_pv_pair_wrapper(setpoint_suffix='',
                                          readback_suffix='_RBV')


class FakeTwinCATStateConfigOne(PVGroup):
    state_name = pvproperty(dtype=str, name='NAME_RBV')
    setpoint = pvproperty_with_rbv(dtype=float, name='SETPOINT')
    delta = pvproperty_with_rbv(dtype=float, name='DELTA')
    velo = pvproperty_with_rbv(dtype=float, name='VELO')
    accl = pvproperty_with_rbv(dtype=float, name='ACCL')
    dccl = pvproperty_with_rbv(dtype=float, name='DCCL')
    move_ok = pvproperty(value=0, name='MOVE_OK_RBV')
    locked = pvproperty(value=0, name='LOCKED_RBV')
    valid = pvproperty(value=0, name='VALID_RBV')


class FakeTwinCATStateConfigAll(PVGroup):
    state01 = SubGroup(FakeTwinCATStateConfigOne, prefix='01:')
    state02 = SubGroup(FakeTwinCATStateConfigOne, prefix='02:')
    state03 = SubGroup(FakeTwinCATStateConfigOne, prefix='03:')
    state04 = SubGroup(FakeTwinCATStateConfigOne, prefix='04:')
    state05 = SubGroup(FakeTwinCATStateConfigOne, prefix='05:')
    state06 = SubGroup(FakeTwinCATStateConfigOne, prefix='06:')
    state07 = SubGroup(FakeTwinCATStateConfigOne, prefix='07:')
    state08 = SubGroup(FakeTwinCATStateConfigOne, prefix='08:')
    state09 = SubGroup(FakeTwinCATStateConfigOne, prefix='09:')
    state10 = SubGroup(FakeTwinCATStateConfigOne, prefix='10:')
    state11 = SubGroup(FakeTwinCATStateConfigOne, prefix='11:')
    state12 = SubGroup(FakeTwinCATStateConfigOne, prefix='12:')
    state13 = SubGroup(FakeTwinCATStateConfigOne, prefix='13:')
    state14 = SubGroup(FakeTwinCATStateConfigOne, prefix='14:')
    state15 = SubGroup(FakeTwinCATStateConfigOne, prefix='15:')


class FakeTwinCATStatePositioner(PVGroup):
    _delay = 0.2

    state_get = pvproperty(value=0, name='GET_RBV')
    state_set = pvproperty(value=0, name='SET')
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

    @state_set.putter
    async def state_set(self, instance, value):
        await self.busy.write(1)
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
    """
    locals().update(
        **{f'axis{axis:02d}': SubGroup(FakeBeckhoffAxis,
                                       prefix=f'MMS:{axis:02d}')
           for axis in range(1, 20)
           }
    )
