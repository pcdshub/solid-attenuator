# ====================================================================
#  This is old code intended for testing the attenuation algorithm.
#  Not for use in beamline operations.
# ====================================================================

import logging

import h5py
import numpy as np
from ophyd import EpicsSignal, EpicsSignalRO
from ophyd.device import Component as Cpt
from ophyd.device import Device
from ophyd.device import FormattedComponent as FCpt
from ophyd.status import wait as status_wait
from pcdsdevices.inout import TwinCATInOutPositioner

logger = logging.getLogger(__name__)


class HXRFilter(Device):
    """
    A single attenuation blade.

    Parameters:
    -----------
    prefix : ``str``
    filter_data : ``file``
    index : ``int``
    """
    _transmission = {}  # TODO: this would be good to be dynamically set.
    # It will be set by Satt using eV RBV callback

    blade = FCpt(TwinCATInOutPositioner,
                 '{prefix}:MMS:{self.index_str}', kind='normal')
    material = FCpt(EpicsSignalRO,
                    '{prefix}:FILTER:{self.index_str}:MATERIAL',
                    string=True, kind='normal')
    thickness = FCpt(EpicsSignalRO,
                     '{prefix}:FILTER:{self.index_str}:THICKNESS',
                     kind='normal')
    stuck = FCpt(EpicsSignal,
                 '{prefix}:FILTER:{self.index_str}:IS_STUCK',
                 kind='normal')
    tab_whitelist = ['inserted', 'removed', 'insert', 'remove', 'transmission']

    def __init__(self,
                 prefix,
                 h5file=None,
                 index=None,
                 name='hxr_filter',
                 **kwargs):
        self.index_str = f'{index}'.zfill(2)
        self.index = index
        super().__init__(prefix, name=name, **kwargs)
        self.constants, self._data, self._eV_min, self._eV_inc, self._eV_max = self.load_data(
            h5file)
        self.Z = self.atomic_number = int(self.constants[0])  # atomic number
        self.A = self.atomic_weight = self.constants[1]  # atomic weight [g]
        self.p = self.density = self.constants[2]  # density [g/cm^3]
        self.d = self.thickness.get()

    def load_data(self, h5file):
        """
        Loads HDF5 physics data into tables.
        """
        table = np.asarray(h5file['{}_table'.format(self.material.get())])
        constants = np.asarray(
            h5file['{}_constants'.format(self.material.get())])
        eV_min = table[0, 0]
        eV_max = table[-1, 0]
        eV_inc = (table[-1, 0] - table[0, 0])/len(table[:, 0])
        return constants, table, eV_min, eV_inc, eV_max

    def _closest_eV(self, eV):
        """
        Return the closest tabulated photon energy to ``eV``
        and its lookup table index.  If ``eV`` is outside
        the range of the table, the function will return
        either the lowest or highest value available.
        """
        i = int(np.rint((eV - self._eV_min)/self._eV_inc))
        if i < 0:
            i = 0  # Use lowest tabulated value.
        if i > self._data.shape[0]:
            i = -1  # Use greatest tabulated value.
        closest_eV = self._data[i, 0]
        return closest_eV, i

    def get_vals(self, eV):
        """
        Return closest photon energy to ``eV`` and its transmission.
        """
        close_eV, i = self._closest_eV(eV)
        T = np.exp(-self._data[i, 2]*self.d)
        return close_eV, T

    def transmission(self, eV):
        """
        Return beam transmission at photon energy closest ``eV``.
        """
        return self.get_vals(eV)[1]

    def inserted(self):
        """
        True if filter is inserted ('IN').
        """
        return self.blade.inserted

    def removed(self):
        """
        True if filter is removed ('OUT').
        """
        return self.blade.removed

    def is_stuck(self):
        """
        True if filter has been set as stuck.
        Unable to move.  Hopefully retracted.
        """
        return self.stuck.get()

    def set_stuck(self):
        """
        Flag the filter blade as stuck.
        """
        return self.stuck.put("True")


class HXRSatt(Device):
    """
    LCLS II Hard X-ray solid attenuator system.
    """
    cbid = None
    retries = 3
    tab_component_names = True
    tab_whitelist = []

    eV = FCpt(EpicsSignalRO, "LCLS:HXR:BEAM:EV", kind='hinted')

    locked = FCpt(EpicsSignalRO, '{prefix}:SYS:LOCKED',
                  kind='hinted')  # lock the system (all motion)
    unlock = FCpt(EpicsSignalRO, '{prefix}:SYS:UNLOCK',
                  kind='hinted')  # unlock the system
    set_mode = FCpt(EpicsSignal, '{prefix}:SYS:SET_MODE',
                    kind='hinted')  # select best lowest or highest
    T_actual = FCpt(EpicsSignal, '{prefix}:SYS:T_ACTUAL',
                    kind='hinted')  # current transmission
    T_high = FCpt(EpicsSignal, '{prefix}:SYS:T_HIGH',
                  kind='hinted')  # closest achievable high
    T_low = FCpt(EpicsSignal, '{prefix}:SYS:T_LOW',
                 kind='hinted')  # closest achievable low
    T_des = FCpt(EpicsSignal, '{prefix}:SYS:T_DESIRED',
                 kind='hinted')
    T_3omega = FCpt(EpicsSignal, '{prefix}:SYS:T_3OMEGA',
                    kind='hinted')
    run = FCpt(EpicsSignal, '{prefix}:SYS:RUN',
               kind='hinted')
    running = FCpt(EpicsSignal, '{prefix}:SYS:MOVING',
                   kind='hinted')
#    mirror_in = FCpt(EpicsSignalRO, '{prefix}:SYS:T_VALID',
#                    kind='hinted')
#    transmission_valid = FCpt(EpicsSignalRO, '{prefix}:SYS:T_VALID',
#                    kind='hinted')
#    pv_config = FCpt(EpicsSignalRO, '{prefix}:SYS:CONFIG',
#                    kind='hinted') # not implemented

    def __init__(self, prefix, eV_prefix="LCLS:HXR:BEAM:EV",
                 name='HXRSatt', **kwargs):
        super().__init__(prefix, name=name, **kwargs)

    def _startup(self):
        """
        Connect to PVs in order to generate
        information about filter configurations
        and photon energy.
        """
        self.N_filters = len(self.filters)
        self.config_arr = self._curr_config_arr()
        self.config_table = self._load_configs()
        self.curr_transmission()
        self.eV.subscribe(self._eV_callback)
        self.T_des.subscribe(self._T_des_callback)
        self.run.subscribe(self._run_callback)

    def blade(self, index):
        """
        Returns the filter device at `index`.
        """
        return self.filters.get(str(index))

    def insert(self, index):
        """
        Insert filter at `index` into the 'IN' position.
        """
        inserted = self.blade(index).blade.insert()
        self._curr_config_arr()
        return inserted

    def remove(self, index):
        """
        Retract  filter at `index` into the 'OUT' position.
        """
        removed = self.blade(index).blade.remove()
        self._curr_config_arr()
        return removed

    def config(self):
        """
        Return a dictionary of filter states indexed
        by filter number.
        """
        config_dict = {}
        for f in self.filters:
            blade = self.filters.get(f)
            if blade.inserted():
                config_dict.update({blade.index: 'IN'})
            if blade.removed():
                config_dict.update({blade.index: 'OUT'})
            if not blade.inserted() and not blade.removed():
                config_dict.update({blade.index: 'UKNOWN'})
            if blade.is_stuck():
                config_dict.update({blade.index: 'STUCK'})
        return config_dict

    def _load_configs(self):
        """
        Load the HDF5 table of possible configurations.
        """
        self.config_table = self.configs['configurations']
        return self.config_table

    # Need a callback on every blade to grab its state and update config...
    def _curr_config_arr(self):
        """
        Return the current configuration of filter states
        as an array.
        """
        config = np.ones(self.N_filters)
        for i in range(self.N_filters):
            if self.blade(i+1).inserted():
                config[i] = 1
            else:
                config[i] = np.nan
        self.config_arr = config
        return config

    def _all_transmissions(self, eV):
        """
        Calculates and returns transmission at
        photon energy ``eV`` for all non-stuck filters.
        """
        T_arr = np.ones(self.N_filters)
        for i in range(self.N_filters):
            if self.blade(i+1).is_stuck():
                T_arr = np.nan
            else:
                T_arr[i] = self.blade(i+1).transmission(eV)
        return T_arr

    def curr_transmission(self, eV=None):
        """
        Calculates and returns transmission at
        photon energy ``eV`` through current filter configuration.
        """
        print("updating transmission")
        if not eV:
            eV = self.eV.get()
        self.transmission = np.nanprod(
            self._all_transmissions(eV)*self._curr_config_arr())
        self.T_actual.put(self.transmission)
        self.get_3omega_transmission()
        return self.transmission

    def _eV_callback(self, value=None, **kwargs):
        """
        To be run every time the ``eV`` signal changes.
        """
        self.transmission = self.curr_transmission(self.eV.get())

    def _T_des_callback(self, value=None, **kwargs):
        """
        To be run every time the ``T_des`` signal changes.
        """
        config_bestLow, config_bestHigh, T_bestLow, T_bestHigh = self._find_configs(self.eV.get(),
                                                                                    T_des=self.T_des.get())
        self.T_high.put(T_bestHigh)
        self.T_low.put(T_bestLow)

    def _run_callback(self, old_value=None, value=None, **kwargs):
        """
        To be run every time the ``run`` sgianl changes.
        """
        if old_value == 0 and self.running.get() == 0 and value == 1:
            print("run value changed to 1, attenuating")
            self.attenuate()
            for i in range(self.retries):
                try:
                    print("returning run to 0")
                    self.run.put(0)
                except Exception:
                    print("could not set run to 0")
                    pass

    def _find_configs(self, eV, T_des=None):
        """
        Find the optimal configurations for attaining
        desired transmission ``T_des`` at photon
        energy ``eV``.

        Returns configurations which yield closest
        highest and lowest transmissions and their
        transmission values.
        """
        if not T_des:
            T_des = self.T_des.get()
        T_set = self._all_transmissions(eV)
        T_table = np.nanprod(T_set*self.config_table,
                             axis=1)
        T_config_table = np.asarray(sorted(np.transpose([T_table[:],
                                                         range(len(self.config_table))]),
                                           key=lambda x: x[0]))
        i = np.argmin(np.abs(T_config_table[:, 0]-T_des))
        closest = self.config_table[T_config_table[i, 1]]
        T_closest = np.nanprod(T_set*closest)
        if T_closest == T_des:
            config_bestHigh = config_bestLow = closest
            T_bestHigh = T_bestLow = T_closest
        if T_closest < T_des:
            config_bestHigh = self.config_table[T_config_table[i+1, 1]]
            config_bestLow = closest
            T_bestHigh = np.nanprod(T_set*config_bestHigh)
            T_bestLow = T_closest
        if T_closest > T_des:
            config_bestHigh = closest
            config_bestLow = self.config_table[T_config_table[i-1, 1]]
            T_bestHigh = T_closest
            T_bestLow = np.nanprod(T_set*config_bestLow)
        return config_bestLow, config_bestHigh, T_bestLow, T_bestHigh

    def get_3omega_transmission(self):
        """
        Calculates 3rd harmonic transmission through the current
        configuration and sets the ``T_3omega`` attribute.
        """
        return self.T_3omega.put(np.nanprod(
            self._all_transmissions(3*self.eV.get())*self._curr_config_arr()))

    def transmission_desired(self, T_des):
        """
        Set the desired transmission.
        """
        config_bestLow, config_bestHigh, T_bestLow, T_bestHigh = self._find_configs(
            self.eV.get())
        self.T_low.put(T_bestLow)
        self.T_high.put(T_bestHigh)
        return self.T_des.put(T_des)

    def attenuate(self, timeout=None):
        """
        Will execute the filter selection procedure and
        move the necessary filters into the beam in order
        to achieve the closest transmission to ``T_des``.
        """
        print("setting running to high")
        self.running.put(1)
        config_bestLow, config_bestHigh, T_bestLow, T_bestHigh = self._find_configs(
            self.eV.get())
        if self.set_mode.get() == 0:
            config = config_bestLow
            T = T_bestLow
        if self.set_mode.get() == 1:
            config = config_bestHigh
            T = T_bestHigh
        to_insert = list()
        to_remove = list()
        for i in range(len(self.config_arr)):
            blade = self.blade(i+1)
            if not blade.is_stuck() and blade.removed() and config[i] == 1:
                to_insert.append(i+1)
            if not blade.is_stuck() and blade.inserted() and np.isnan(config[i]):
                to_remove.append(i+1)
        insert_st = list()
        in_status = None
        remove_st = list()
        out_status = None
    #        logger.debug("Inserting blades {}".format(to_insert))
        print("inserting blades")
        for f in to_insert:
            insert_st.append(self.insert(f))
        for st in insert_st:
            print("waiting on insert status", st)
            status_wait(st, timeout=timeout)
        # if len(insert_st) >= 1:
        #     in_status = insert_st.pop(0)
        #     for st in insert_st:
        #         in_status = in_status & st
            logger.debug("Waiting for motion to finish...")
#            status_wait(in_status, timeout=timeout)
        if in_status:
            inserted = in_status
        else:
            inserted = True  # Not correct, this should be a status object.
        # TODO: if any inserted motion fails then do not remove any filters!
#        logger.debug("Removing blades {}".format(to_remove))
        print("removing blades")
        for f in to_remove:
            remove_st.append(self.remove(f))
        if len(remove_st) >= 1:
            out_status = remove_st.pop(0)
            for st in remove_st:
                out_status = out_status & st
            logger.debug("Waiting for motion to finish...")
            status_wait(out_status, timeout=timeout)
        if out_status:
            removed = out_status
        else:
            removed = True
        self._curr_config_arr()
        self.curr_transmission()
        print("resetting running to 0")
        self.running.put(0)
#        return inserted & removed


class AT2L0(HXRSatt):

    absorption_data = h5py.File('absorption_data.h5', 'r')
    configs = h5py.File('configs.h5', 'r')

    f01 = FCpt(HXRFilter, '{prefix}', h5file=absorption_data,
               index=1, kind='normal')
    f02 = FCpt(HXRFilter, '{prefix}', h5file=absorption_data,
               index=2, kind='normal')
    f03 = FCpt(HXRFilter, '{prefix}', h5file=absorption_data,
               index=3, kind='normal')
    f04 = FCpt(HXRFilter, '{prefix}', h5file=absorption_data,
               index=4, kind='normal')
    f05 = FCpt(HXRFilter, '{prefix}', h5file=absorption_data,
               index=5, kind='normal')
    f06 = FCpt(HXRFilter, '{prefix}', h5file=absorption_data,
               index=6, kind='normal')
    f07 = FCpt(HXRFilter, '{prefix}', h5file=absorption_data,
               index=7, kind='normal')
    f08 = FCpt(HXRFilter, '{prefix}', h5file=absorption_data,
               index=8, kind='normal')
    f09 = FCpt(HXRFilter, '{prefix}', h5file=absorption_data,
               index=9, kind='normal')
    f10 = FCpt(HXRFilter, '{prefix}', h5file=absorption_data,
               index=10, kind='normal')
    f11 = FCpt(HXRFilter, '{prefix}', h5file=absorption_data,
               index=11, kind='normal')
    f12 = FCpt(HXRFilter, '{prefix}', h5file=absorption_data,
               index=12, kind='normal')
    f13 = FCpt(HXRFilter, '{prefix}', h5file=absorption_data,
               index=13, kind='normal')
    f14 = FCpt(HXRFilter, '{prefix}', h5file=absorption_data,
               index=14, kind='normal')
    f15 = FCpt(HXRFilter, '{prefix}', h5file=absorption_data,
               index=15, kind='normal')
    f16 = FCpt(HXRFilter, '{prefix}', h5file=absorption_data,
               index=16, kind='normal')
    f17 = FCpt(HXRFilter, '{prefix}', h5file=absorption_data,
               index=17, kind='normal')
    f18 = FCpt(HXRFilter, '{prefix}', h5file=absorption_data,
               index=18, kind='normal')

    def __init__(self, prefix, name='at2l0', **kwargs):
        self.prefix = prefix
        super().__init__(prefix, name=name, **kwargs)
        self.filters = {
            str(self.f01.index): self.f01,
            str(self.f02.index): self.f02,
            str(self.f03.index): self.f03,
            str(self.f04.index): self.f04,
            str(self.f05.index): self.f05,
            str(self.f06.index): self.f06,
            str(self.f07.index): self.f07,
            str(self.f08.index): self.f08,
            str(self.f09.index): self.f09,
            str(self.f10.index): self.f10,
            str(self.f11.index): self.f11,
            str(self.f12.index): self.f12,
            str(self.f13.index): self.f13,
            str(self.f14.index): self.f14,
            str(self.f15.index): self.f15,
            str(self.f16.index): self.f16,
            str(self.f17.index): self.f17,
            str(self.f18.index): self.f18,
        }
        super()._startup()
