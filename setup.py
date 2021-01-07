import sys
from os import path

from setuptools import find_packages, setup

import versioneer

min_version = (3, 6)

if sys.version_info < min_version:
    error = """
solid-attenuator does not support Python {0}.{1}.
Python {2}.{3} and above is required. Check your Python version like so:

python3 --version

This may be due to an out-of-date pip. Make sure you have pip >= 9.0.1.
Upgrade pip like so:

pip install --upgrade pip
""".format(*sys.version_info[:2], *min_version)
    sys.exit(error)


here = path.abspath(path.dirname(__file__))

with open(path.join(here, 'README.rst'), encoding='utf-8') as readme_file:
    readme = readme_file.read()

with open(path.join(here, 'requirements.txt')) as requirements_file:
    # Parse requirements.txt, ignoring any commented-out lines.
    requirements = [line for line in requirements_file.read().splitlines()
                    if not line.startswith('#')]


git_requirements = [r for r in requirements if r.startswith('git+')]
if git_requirements:
    print('User must install the following packages manually:')
    print()
    print("\n".join(f'* {r}' for r in git_requirements))
    print()


setup(
    name='solid_attenuator',
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    license='BSD',
    author='SLAC National Accelerator Laboratory',
    packages=find_packages(exclude=['docs', 'tests']),
    description=' LCLS Hard X-Ray Solid Attenuator System',
    long_description=readme,
    url='https://github.com/pcdshub/solid-attenuator',
    entry_points={
        'console_scripts': [
            'ioc-lfe-at2l0-calc=solid_attenuator.ioc_lfe_at2l0_calc.__main__:main',  # noqa
            'ioc-sim-at2l0=solid_attenuator.ioc_sim_at2l0.__main__:main',
            'ioc-sim-sxr-satt=solid_attenuator.ioc_sim_sxr.__main__:main',
            ],
        },
    include_package_data=True,
    package_data={
        'solid_attenuator': [
            # When adding files here, remember to update MANIFEST.in as well!
            'ioc_lfe_at2l0_calc/CXRO/*.nff'
            'ioc_lfe_at2l0_calc/iocBoot/*.cmd',
            'ioc_sim_at2l0/iocBoot/*.cmd',
            ]
        },
    install_requires=requirements,
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
    ],
)
