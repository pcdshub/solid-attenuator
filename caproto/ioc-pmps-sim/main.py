from caproto.server import ioc_arg_parser, run
from caproto.threading import pyepics_compat as epics
from h5py import File as h5file
from app import *

################################################
eV_name = "LCLS:HXR:BEAM:EV"
pmps_run_name = "PMPS:HXR:AT2L0:RUN"
prefix = "PMPS:HXR:AT2L0"
################################################

if __name__ == '__main__':
    ioc_options, run_options = ioc_arg_parser(
        default_prefix=prefix,
        desc=IOCMain.__doc__)
    ioc = create_ioc(
        eV_pv=eV_name,
        pmps_run_pv=pmps_run_name,
        **ioc_options)
    run(ioc.pvdb, **run_options)
