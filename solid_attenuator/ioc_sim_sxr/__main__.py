from caproto.server import ioc_arg_parser, run

from .sim_sxr import IOCMain


def main():
    ioc_options, run_options = ioc_arg_parser(
        default_prefix='',
        desc=IOCMain.__doc__,
        macros={
            'system': 'AT1K4',
            'pmps_run': 'PMPS:HXR:AT1K4:RUN',
            'ev_pv': 'LCLS:SXR:BEAM:EV',
        },
    )
    ioc = IOCMain(**ioc_options)
    run(ioc.pvdb, **run_options)


if __name__ == '__main__':
    main()
