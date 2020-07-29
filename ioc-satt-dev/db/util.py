import sys
import typing

import caproto
import caproto._log as caproto_log
import caproto.threading

_default_thread_context = None


def get_default_thread_context():
    """Get a shared caproto threading client context."""
    global _default_thread_context
    if _default_thread_context is None:
        _default_thread_context = caproto.threading.client.Context()
    return _default_thread_context


def _monitor_pvs(*pv_names, context, queue, data_type='time'):
    """
    Monitor pv_names in the given threading context, putting events to `queue`.
    Parameters
    ----------
    *pv_names : str
        PV names to monitor.
    context : caproto.threading.client.Context
        The threading context to use.
    queue : ThreadsafeQueue
        Thread-safe queue for the current server async library.
    data_type : {'time', 'control', 'native'}
        The subscription type.
    Returns
    -------
    subscriptions : list
        List of subscription tuples, with each being:
        ``(sub, subscription_token, *callback_references)``
    """

    def add_to_queue(sub, event_add_response):
        queue.put(('subscription', sub, event_add_response))

    def connection_state_callback(pv, state):
        queue.put(('connection', pv, state))

    pvs = context.get_pvs(
        *pv_names, timeout=None,
        connection_state_callback=connection_state_callback
    )

    subscriptions = []
    for pv in pvs:
        sub = pv.subscribe(data_type=data_type)
        token = sub.add_callback(add_to_queue)
        subscriptions.append((sub, token, add_to_queue,
                              connection_state_callback))

    return subscriptions


async def monitor_pvs(*pv_names, async_lib, context=None, data_type='time'):
    """
    Monitor pv_names asynchronously, yielding events as they happen.
    Parameters
    ----------
    *pv_names : str
        PV names to monitor.
    async_lib : caproto.server.AsyncLibraryLayer
        The async library layer shim to get compatible classes from.
    context : caproto.threading.client.Context
        The threading context to use.
    data_type : {'time', 'control', 'native'}
        The subscription type.
    Yields
    -------
    event : {'subscription', 'connection'}
        The event type.
    context : str or Subscription
        For a 'connection' event, this is the PV name.  For a 'subscription'
        event, this is the `Subscription` instance.
    data : str or EventAddResponse
        For a 'subscription' event, the `EventAddResponse` holds the data and
        timestamp.  For a 'connection' event, this is one of ``{'connected',
        'disconnected'}``.
    """

    if context is None:
        context = get_default_thread_context()

    queue = async_lib.ThreadsafeQueue()
    subscriptions = _monitor_pvs(*pv_names, context=context, queue=queue,
                                 data_type=data_type)
    try:
        while True:
            event, context, data = await queue.async_get()
            yield event, context, data
    finally:
        for sub, token, *callbacks in subscriptions:
            sub.remove_callback(token)


def config_logging(logger, file=sys.stdout, datefmt='%H:%M:%S', color=True,
                   level='WARNING'):
    """
    Add a new handler to the logger.

    Parameters
    ----------
    logger : logging.Logger
        The logger to configure.

    file : object with ``write`` method or filename string
        Default is ``sys.stdout``.

    datefmt : string
        Date format. Default is ``'%H:%M:%S'``.

    color : boolean
        Use ANSI color codes. True by default.

    level : str or int
        Python logging level, given as string or corresponding integer.
        Default is 'WARNING'.

    Examples
    --------
    Log to a file.

    >>> config_logging(file='/tmp/what_is_happening.txt')

    Include the date along with the time. (The log messages will always include
    microseconds, which are configured separately, not as part of 'datefmt'.)

    >>> config_logging(datefmt="%Y-%m-%d %H:%M:%S")

    Turn off ANSI color codes.

    >>> config_logging(color=False)

    Increase verbosity: show level INFO or higher.

    >>> config_logging(level='INFO')
    """
    caproto_log._set_handler_with_logger(logger_name=logger.name,
                                         file=file, datefmt=datefmt,
                                         color=color, level=level)


def hack_max_length_of_channeldata(channeldata: caproto.ChannelData,
                                   new_value: list,
                                   max_length=None):
    """
    Force in a maximum length value. Should only be done at init time.

    Parameters
    ----------
    channeldata : caproto.ChannelData
        The ChannelData instance.

    new_value : list
        The new value to set.

    max_length : int, optional
        The new maximum length to use. Defaults to `len(new_value)`, and
        must be `>= len(new_value)`.
    """
    max_length = max_length or len(new_value)
    assert max_length >= len(new_value)
    channeldata._max_length = max_length
    channeldata._data['value'] = list(new_value)


def process_writes_value(pvprop: caproto.server.pvproperty, *,
                         value: typing.Any = None):
    """
    When `.PROC` is changed, write the value `value` to the pvproperty.

    Parameters
    ----------
    pvprop : caproto.server.pvproperty
        The property.

    value : any
        The value to write upon processing.  If `None`, defaults to re-writing
        the current value of `pvprop`.
    """

    async def wrapped(fields, instance, proc_value, *, value_to_write=value):
        pvprop_instance = fields.parent
        if value_to_write is None:
            value_to_write = pvprop_instance.value
        await pvprop_instance.write(value_to_write)

    pvprop.fields.process_record.putter(wrapped)
