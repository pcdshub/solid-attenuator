import sys

import h5py
import numpy as np
from scipy.interpolate import interp1d

"""
Program for populating photoabsorption datasets for
X-FEL solid attenuator transmission calculations using
public data availabe from LBNL CXRO.

REFERENCES:
----------------
B.L. Henke, E.M. Gullikson, and J.C. Davis,
X-ray interactions: photoabsorption, scattering, transmission,
and reflection at E=50-30000 eV, Z=1-92,
Atomic Data and Nuclear Data Tables 54 no.2, 181-342 (July 1993).

B.D. Cullity, Elements of X-Ray Diffraction (Second Edition),
11-20, (1978).
"""

# TODO: Read these from a config file.
Si_data = {
    'formula'      : 'Si',
    'atomic_number': 14,         # Z
    'atomic_weight': 28.08,      # grams
    'density'      : 2.329E6,    # grams/m^3
}
C_data = {
    'formula'      : 'C',
    'atomic_number': 6,          # Z
    'atomic_weight': 12.01,      # grams
    'density'      : 3.51E6,     # grams/m^3
}

# physical constants
r0 = 2.81794E-15    # [m]      classical electron radius
h = 4.135667E-15    # [eV s]    plancks constant
c = 2.997945E8      # [m s^-1] Speed of light
NA = 6.02240E23     # []       Avagadros number

data_dicts = [Si_data, C_data]

def nff_to_npy(element):
    """
    Opens the .nff file containing scattering factors / energies for
    an atomic element and writes the data to a numpy array.

    Parameters:
    ---------------
    element : ``str``
       Formula of the element to open e.g. "Si", "si", "C", "Au"

    """
    element = element.lower()
    raw_data = open('CXRO/{}.nff'.format(element), 'r')
    data_lines = raw_data.readlines()
    npy_data = np.zeros([len(data_lines)-2,3])
    for i in range(1,len(data_lines)-1):
        nums = data_lines[i].split('\t')
        npy_data[i-1]= float(nums[0]), float(nums[1]), float(nums[2])
    return npy_data


def eV_linear(eV_range, res=10, dec=2):
    """
    Return a linear range of photon energies.

    Parameters:
    ---------------
    eV_range : ``tuple``
       Upper and lower bounds of photon energy range.

    res : ``float``
       Magnitude of resolution.  Default of 10 yields 0.1 eV resolution.

    dec : ``int``
       Decimal places.
    """
    return np.around(np.linspace(eV_range[0],
                                 eV_range[1],
                                 (eV_range[1]-eV_range[0])*res+1), dec)


def fill_data_linear(element, eV_range, res=10):
    """
    Interpolates data to add more samples.

    Parameters:
    ---------------
    element : ``str``
       Formula of the element to open e.g. "Si", "si", "C", "Au"

    eV_range : ``tuple``
       Upper and lower bounds of photon energy range.

    res : ``float``
       Magnitude of resolution.  Default of 10 yields 0.1 eV resolution.
    """
    raw_data = nff_to_npy(element)
    new_range = eV_linear(eV_range=eV_range, res=10)
    fill_func = interp1d(raw_data[:,0], raw_data[:,2])
    return fill_func(new_range)


def abs_data(material, eV_range):
    """
    Data table for photoabsorption calculations.
    """
    fs = fill_data_linear(material.get('formula'), eV_range=eV_range)
    table = np.zeros([fs.shape[0], 3])
    A = material.get('atomic_weight')
    p = material.get('density')
    eV_space = eV_linear(eV_range=eV_range) # eV
    table[:,0] = eV_space[:]
    table[:,1] = fs # scattering factor f_2
    table[:,2] = (2*r0*h*c*fs/eV_space)*p*(NA/A) # absorption constant \mu
    return table


def gen_table(data_dicts, eV_range=(1000,25000), res=10, dec=2,
              output_filename='absorption_data.h5'):
    h5 = h5py.File(output_filename, 'w')
    for data in data_dicts:
        element = data.get('formula')
        table = abs_data(data, eV_range)
        data_table = h5.create_dataset('{}_table'.format(element),
                                        table.shape,
                                        dtype='f')
        data_consts = h5.create_dataset('{}_constants'.format(element),
                                    (3,),
                                    dtype=float)
        data_table[:] = table[:]
        data_consts[0] = data.get('atomic_number')
        data_consts[1] = data.get('atomic_weight')
        data_consts[2] = data.get('density')
    h5.close()


if __name__ == '__main__':
    try:
        output_filename = sys.argv[1]
    except IndexError:
        print(f'Usage: {sys.argv[0]} (output_filename.h5)')
        sys.exit(1)

    gen_table(data_dicts, output_filename=output_filename)
