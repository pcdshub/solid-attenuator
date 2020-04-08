from caproto.server import pvproperty, PVGroup, ioc_arg_parser, run
from caproto import ChannelType

class IOCMain(PVGroup):
    """
    """
    def __init__(self,
                 prefix,
                 *,
                 groups,
                 abs_data,
                 config_data,
                 eV,
                 pmps_run,
                 **kwargs):
        super().__init__(prefix, **kwargs)
        self.groups=groups
        self.eV=eV
        self.pmps_run=pmps_run
        self.startup()

    def startup(self):
        self.eV.add_callback(self.eV_callback)
        self.pmps_run.add_callback(self.pmps_run_callback)

    def eV_callback(value, **kwargs):
        print("eV changed to {}".format(value))

    def pmps_run_callback(value, **kwargs):
        print("PMPS run changed to {}".format(value))


