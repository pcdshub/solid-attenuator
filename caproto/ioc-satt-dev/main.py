from caproto.server import ioc_arg_parser, run
from caproto.threading import pyepics_compat as epics
from h5py import File as h5file
from satt_app import *

################################################
prefix = "AT2L0:SIM"
num_blades = 18
eV_name = "LCLS:HXR:BEAM:EV"
pmps_run_name = "PMPS:HXR:AT2L0:RUN"
abs_data = h5file('../../../absorption_data.h5', 'r')
config_data = h5file('../../../configs.h5', 'r')
################################################

ioc_args = {
"absorption_data" : abs_data,
"config_data" : config_data,
"filter_group" : [str(N+1).zfill(2) for N in range(num_blades)]
}

if __name__ == '__main__':
    ioc_options, run_options = ioc_arg_parser(
        default_prefix=prefix,
        desc=IOCMain.__doc__)
    ioc = create_ioc(
        eV_pv=eV_name,
        pmps_run_pv=pmps_run_name,
        **ioc_args,
        **ioc_options)
    run(ioc.pvdb, **run_options)
