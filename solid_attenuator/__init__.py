from . import calculator, filters, ioc, sxr, system, util
from ._version import get_versions

__version__ = get_versions()['version']
del get_versions

__all__ = [
    'calculator',
    'filters',
    'ioc',
    'sxr',
    'system',
    'util',
]
