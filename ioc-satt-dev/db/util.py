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
        queue.put(('subscription', sub.pv, event_add_response))

    def connection_state_callback(pv, state):
        queue.put(('connection', pv, state))

    pvs = context.get_pvs(
        *pv_names, timeout=None,
        connection_state_callback=connection_state_callback
    )

    subscriptions = []
    for pv in pvs:
        sub = pv.subscribe(data_type='time')
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

    pv : str
        The PV name.

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
            info = await queue.async_get()
            yield info
    finally:
        for sub, token, *callbacks in subscriptions:
            sub.remove_callback(token)
