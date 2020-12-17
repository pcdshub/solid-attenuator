import dataclasses

import numpy as np
import pytest

from ..ioc_lfe_at2l0_calc import calculator

import matplotlib  # isort: skip  # noqa

matplotlib.use('Agg')

import matplotlib.pyplot as plt  # isort: skip  # noqa


@dataclasses.dataclass
class Filter:
    material: str
    thickness: float
    transmission: float


@pytest.fixture(params=range(2_000, 3_0000, 2_000))
def photon_energy(request):
    return float(request.param)


absorption_tables = {}
_subplots = {}


def get_transmission(material: str,
                     thickness: float,
                     photon_energy: float) -> np.ndarray:
    """Get the transmission for a given material at a specific energy."""
    try:
        table = absorption_tables[material]
    except KeyError:
        table = calculator.get_absorption_table(material)
        absorption_tables[material] = table
    return calculator.get_transmission(
        photon_energy, table=table, thickness=thickness * 1e-6
    )


@pytest.mark.parametrize(
    'diamond_thicknesses, si_thicknesses',
    [
        pytest.param(
            [1280, 640, 320, 160, 80, 40, 20, 10],
            [10240, 5120, 2560, 1280, 640, 320, 160, 80, 40, 20],
            id='all_working'
        ),
        pytest.param(
            [640, 320, 160, 80, 40, 20, 10],
            [10240, 5120, 2560, 1280, 640, 320, 160, 80, 40, 20],
            id='missing_C_1280'
        ),
        pytest.param(
            [640, 320, 160, 80, 40],
            [10240, 5120, 2560, 1280, 640, 320, 160, 80, 40, 20],
            id='missing_C_10_20'
        ),
    ]
)
def test_material_prioritization(request, diamond_thicknesses, si_thicknesses,
                                 photon_energy):
    diamond_filters = [
        Filter('C', thickness, get_transmission('C', thickness, photon_energy))
        for thickness in diamond_thicknesses
    ]
    silicon_filters = [
        Filter('Si', thickness, get_transmission('Si', thickness,
                                                 photon_energy))
        for thickness in si_thicknesses
    ]
    filters = diamond_filters + silicon_filters

    t_all_diamond = np.product([flt.transmission for flt in diamond_filters])

    t_des_checks = (
        list(np.linspace(0.0, t_all_diamond, 1500)) +
        list(np.linspace(t_all_diamond, 1.0, 1500))
    )

    materials = [flt.material for flt in filters]
    transmissions = [flt.transmission for flt in filters]

    compared = []
    actual = []
    for t_des in t_des_checks:
        conf = calculator.get_best_config_with_material_priority(
            materials=materials,
            transmissions=transmissions,
            material_order=['C', 'Si'],
            t_des=t_des,
        )

        inserted_materials = [
            flt.material for state, flt in zip(conf.filter_states, filters)
            if state
        ]
        if 'Si' in inserted_materials:
            assert inserted_materials.count('C') == len(diamond_filters)

        actual.append(conf.transmission)
        if t_des > 0.0:
            compared.append(abs(t_des - conf.transmission) / t_des)
        else:
            compared.append(0.0)

    print()
    print('(t_des - t_act) / t_des:')
    print('    Standard deviation:', np.std(compared))
    print('    Average:', np.average(compared))

    # I'm sure there's a better way to do this:
    param_id = request.node.name.rsplit('-', 1)[1].strip(']')
    # -> param_id = 'all_working'

    try:
        subplot = _subplots[param_id]
    except KeyError:
        fig = plt.figure(figsize=(10, 6), dpi=120)
        _subplots[param_id] = subplot = fig.subplots(1, 2)

        subplot[0].set_title(f'{param_id} - Transmission Actual vs Desired')
        subplot[1].set_title('Error vs Desired')
        fig.tight_layout()

    line, = subplot[0].plot(t_des_checks, actual,
                            alpha=0.5,
                            lw=1,
                            label=f'{photon_energy} eV')
    subplot[0].plot([t_all_diamond], [t_all_diamond],
                    marker='x',
                    markersize=3,
                    markerfacecolor=line.get_color(),
                    color=line.get_color(),
                    )
    subplot[0].annotate(
        f'{photon_energy:.0f} eV',
        (t_all_diamond, t_all_diamond),
        (t_all_diamond - 0.2, t_all_diamond),
        color=line.get_color(),
    )
    subplot[0].legend(loc='best')

    subplot[1].plot(t_des_checks,
                    np.asarray(actual) - np.asarray(t_des_checks),
                    label=f'{photon_energy} eV',
                    alpha=0.5, lw=1, color=line.get_color())
    subplot[0].figure.savefig(f'{param_id}.pdf')
