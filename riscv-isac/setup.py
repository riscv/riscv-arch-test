# See LICENSE.incore for details

"""The setup script."""

import os
from setuptools import setup, find_packages

# Base directory of package
here = os.path.abspath(os.path.dirname(__file__))


def read(*parts):
    with codecs.open(os.path.join(here, *parts), 'r') as fp:
        return fp.read()
def read_requires(name):
    with open(os.path.join(here, "riscv_isac", name),"r") as reqfile:
        return reqfile.read().splitlines()

#Long Description
with open("README.rst", "r") as fh:
    readme = fh.read()

setup_requirements = [ ]

setup(
    name='riscv_isac',
    version='0.18.0',
    description="RISC-V ISAC",
    long_description=readme + '\n\n',
    classifiers=[
          "Programming Language :: Python :: 3.6",
          "License :: OSI Approved :: BSD License",
          "Development Status :: 4 - Beta"
    ],
    url='https://github.com/riscv/riscv-isac',
    author="InCore Semiconductors Pvt. Ltd.",
    author_email='info@incoresemi.com',
    license="BSD-3-Clause",
    packages=find_packages(),
    package_dir={'riscv_isac': 'riscv_isac'},
    package_data={
        'riscv_isac': [
            'requirements.txt'
            ]
        },
    install_requires=read_requires("requirements.txt"),
    python_requires='>=3.6.0',
    entry_points={
        'console_scripts': [
            'riscv_isac=riscv_isac.main:cli',
        ],
    },
    include_package_data=True,
    keywords='riscv_isac',
    test_suite='tests',
    tests_require=read_requires("test_requirements.txt"),
    zip_safe=False,
)
