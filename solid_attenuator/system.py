import threading
import time

from caproto import AlarmStatus, ChannelType
from caproto.asyncio.server import AsyncioAsyncLayer
from caproto.server import PVGroup, pvproperty
from caproto.server.autosave import autosaved

from . import util
from .util import monitor_pvs


class SystemGroupBase(PVGroup):
    """
    PV group for attenuator system-spanning information.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # TODO: this could be done by wrapping SystemGroup
        for obj in (self.best_config, self.active_config, self.filter_moving):
            util.hack_max_length_of_channeldata(obj,
                                                [0] * self.parent.num_filters)

        # TODO: caproto does not make this easy. We explicitly will be using
        # asyncio here.
        self.async_lib = AsyncioAsyncLayer()
        self._context = {}
        self._pv_put_queue = None
        self._put_thread = None

    calculated_transmission = pvproperty(
        value=0.1,
        name='T_CALC',
        record='ao',
        upper_alarm_limit=1.0,
        lower_alarm_limit=0.0,
        read_only=True,
        doc='Calculated transmission (all blades)',
        precision=3,
    )

    calculated_transmission_3omega = pvproperty(
        name='T_3OMEGA',
        value=0.5,
        upper_alarm_limit=1.0,
        lower_alarm_limit=0.0,
        read_only=True,
        doc='Calculated 3omega transmission (all blades)',
        precision=3,
    )

    best_config_error = pvproperty(
        value=0.1,
        name='BestConfigError_RBV',
        record='ao',
        upper_alarm_limit=1.0,
        lower_alarm_limit=-1.0,
        read_only=True,
        doc='Calculated transmission error',
        precision=3,
    )

    moving = pvproperty(
        name='Moving_RBV',
        value='False',
        record='bo',
        enum_strings=['False', 'True'],
        read_only=True,
        doc='Moving to a new configuration.',
        dtype=ChannelType.ENUM
    )

    mirror_in = pvproperty(
        value='False',
        name='MIRROR_IN',
        record='bo',
        enum_strings=['False', 'True'],
        read_only=True,
        doc='The inspection mirror is in',
        dtype=ChannelType.ENUM
    )

    calc_mode = pvproperty(
        value='Floor',
        name='CalcMode',
        record='bo',
        enum_strings=['Floor', 'Ceiling'],
        read_only=False,
        doc='Mode for selecting floor or ceiling transmission estimation',
        dtype=ChannelType.ENUM
    )

    energy_source = pvproperty(
        value='Actual',
        name='EnergySource',
        record='bo',
        enum_strings=['Actual', 'Custom'],
        read_only=False,
        doc='Choose the source of photon energy',
        dtype=ChannelType.ENUM,
    )

    best_config = pvproperty(
        name='BestConfiguration_RBV',
        value=0,
        max_length=1,
        read_only=True,
        doc='Best configuration as an array (1 if inserted)',
    )

    best_config_bitmask = pvproperty(
        name='BestConfigurationBitmask_RBV',
        value=0,
        read_only=True,
        doc='Best configuration as an integer',
    )

    active_config = pvproperty(
        name='ActiveConfiguration_RBV',
        value=0,
        max_length=1,
        read_only=True,
        alarm_group='motors',
        doc='Active configuration array',
    )

    active_config_bitmask = pvproperty(
        name='ActiveConfigurationBitmask_RBV',
        value=0,
        read_only=True,
        alarm_group='motors',
        doc='Active configuration represented as an integer',
    )

    filter_moving = pvproperty(
        name='FiltersMoving_RBV',
        value=0,
        max_length=1,
        read_only=True,
        alarm_group='motors',
        doc='Filter motion status as an array (1 if moving)',
    )

    filter_moving_bitmask = pvproperty(
        name='FiltersMovingBitmask_RBV',
        value=0,
        read_only=True,
        alarm_group='motors',
        doc='Filter motion status as an integer',
    )

    energy_actual = pvproperty(
        name='ActualPhotonEnergy_RBV',
        value=0.0,
        read_only=True,
        units='eV',
        alarm_group='valid_photon_energy',
        precision=1,
    )

    transmission_actual = pvproperty(
        name='ActualTransmission_RBV',
        value=0.0,
        read_only=True,
        alarm_group='motors',
        precision=3,
    )

    transmission_3omega_actual = pvproperty(
        name='Actual3OmegaTransmission_RBV',
        value=0.0,
        read_only=True,
        alarm_group='motors',
        precision=3,
    )

    energy_custom = pvproperty(
        name='CustomPhotonEnergy',
        value=0.0,
        read_only=False,
        units='eV',
        lower_ctrl_limit=100.0,
        upper_ctrl_limit=30000.0,
        precision=1,
    )

    last_energy = pvproperty(
        name='LastPhotonEnergy_RBV',
        value=0.0,
        read_only=True,
        units='eV',
        doc='Energy that was used for the calculation.',
        precision=1,
    )

    last_transmission = pvproperty(
        name='LastTransmission_RBV',
        value=0.0,
        lower_ctrl_limit=0.0,
        upper_ctrl_limit=1.0,
        doc='Last desired transmission value',
        precision=3,
        read_only=True,
    )

    last_mode = pvproperty(
        value='Floor',
        name='LastCalcMode_RBV',
        record='bo',
        enum_strings=['Floor', 'Ceiling'],
        read_only=True,
        doc='Last calculation mode',
        dtype=ChannelType.ENUM,
    )

    apply_config = pvproperty(
        name='ApplyConfiguration',
        value='False',
        record='bo',
        enum_strings=['False', 'True'],
        doc='Apply the calculated configuration.',
        dtype=ChannelType.ENUM,
        alarm_group='motors',
    )

    cancel_apply = pvproperty(
        name='Cancel',
        value='False',
        record='bo',
        enum_strings=['False', 'True'],
        doc='Stop trying to apply the configuration.',
        dtype=ChannelType.ENUM,
    )

    desired_transmission = autosaved(
        pvproperty(
            name='DesiredTransmission',
            value=0.5,
            lower_ctrl_limit=0.0,
            upper_ctrl_limit=1.0,
            doc='Desired transmission value',
            precision=3,
        )
    )

    run = pvproperty(
        value='False',
        name='Run',
        record='bo',
        enum_strings=['False', 'True'],
        doc='Run calculation',
        dtype=ChannelType.ENUM
    )

    @active_config.startup
    async def active_config(self, instance, async_lib):
        motor_pvnames = self.parent.monitor_pvnames['motors']
        monitor_list = sum((pvlist for pvlist in motor_pvnames.values()),
                           [])
        all_status = {pv: False for pv in monitor_list}

        async def update_connection_status(pv, status):
            all_status[pv] = (status == 'connected')
            await util.alarm_if(instance, not all(all_status.values()),
                                AlarmStatus.LINK)

        async for event, context, data in monitor_pvs(*monitor_list,
                                                      async_lib=async_lib):
            if event == 'connection':
                await update_connection_status(context.name, data)
                continue

            pvname = context.pv.name
            if pvname not in motor_pvnames['get']:
                continue

            idx = self.parent.monitor_pvnames['motors']['get'].index(pvname)
            await self.motor_has_moved(self.parent.first_filter + idx,
                                       data.data[0])

    @energy_actual.startup
    async def energy_actual(self, instance, async_lib):
        """Update beam energy and calculated values."""
        async def update_connection_status(status):
            await util.alarm_if(
                instance, status != 'connected', AlarmStatus.LINK
            )

        await update_connection_status('disconnected')
        pvname = self.parent.monitor_pvnames['ev']
        async for event, context, data in monitor_pvs(pvname,
                                                      async_lib=async_lib):
            if event == 'connection':
                self.log.info('%s %s', context, data)
                await update_connection_status(data)
                continue

            eV = data.data[0]
            self.log.debug('Photon energy changed: %s', eV)

            if instance.value != eV:
                delta = instance.value - eV
                if abs(delta) > 1000:
                    self.log.info("Photon energy changed to %s eV.", eV)
                await instance.write(eV)

        return eV

    @apply_config.putter
    async def apply_config(self, instance, value):
        if value == 'False':
            return

        await self.move_blades()

    # apply_config.PROC -> apply_config = 1
    util.process_writes_value(apply_config, value=1)

    @apply_config.startup
    async def apply_config(self, instance, async_lib):
        def put_thread():
            while True:
                pv, value = self._pv_put_queue.get()
                try:
                    pv.write([value], wait=False)
                except Exception:
                    self.log.exception('Failed to put value: %s=%s', pv, value)

        ctx = util.get_default_thread_context()

        self._set_pvs = ctx.get_pvs(
            *self.parent.monitor_pvnames['motors']['set'], timeout=None)

        self._pv_put_queue = self.async_lib.ThreadsafeQueue()
        self._put_thread = threading.Thread(target=put_thread, daemon=True)
        self._put_thread.start()

    async def move_blades(self, *, timeout_threshold=30.0):
        """Move to the calculated configuration."""
        t0 = time.monotonic()

        def check_done():
            elapsed = time.monotonic() - t0
            done = (tuple(self.active_config.value) ==
                    tuple(self.best_config.value))
            moving = any(status for status in self.filter_moving.value)
            return any(
                (done and not moving,
                 self.cancel_apply.value == 'True',
                 elapsed > timeout_threshold,
                 )
            )

        await self.moving.write(1)

        state = {}
        while not check_done():
            if not await self.move_blade_step(state):
                break

            await self.async_lib.library.sleep(0.1)

        await self.moving.write(0)

    @run.putter
    async def run(self, instance, value):
        if value == 'False':
            return

        try:
            await self.run_calculation()
        except Exception:
            self.log.exception('update_config failed?')

    # RUN.PROC -> run = 1
    util.process_writes_value(run, value=1)
