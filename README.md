# RISC-V Architectural Certification Tests

The RISC-V Architectural Certification Tests (ACTs) are a set of assembly language tests designed to certify that a design faithfully implements the RISC-V specification. These are not verification tests and additional verification should be run on all processors. For additional details on the certification process, see [LINK COMING SOON]().

## Getting Started

This section serves as a quick guide to set up the ACT environment and ensure you can run tests successfully on the RISC-V Sail golden reference model.

### Prerequisites

#### 1. Python/uv

The test generator and framework are written in Python. The recommended way of installing and running Python is using the uv project manager, which will handle Python versions, virtual environments, and dependencies transparently.

Install uv:

```bash
$ curl -LsSf https://astral.sh/uv/install.sh | sh
```

For more details on uv and alternate installation methods, see the [uv installation guide](https://docs.astral.sh/uv/getting-started/installation/).

#### 2. RISC-V Compiler

The ACT framework is compatible with GCC or LLVM. This guide uses GCC, but if you prefer LLVM you just need to set the path the compiler appropriately when [creating your config file](#configfile).

> **Note**: The git clone and installation will take significant time. Please be patient. If you face issues with any of the following steps, please refer to [riscv-gnu-toolchain](https://github.com/riscv-collab/riscv-gnu-toolchain) for further help in installation.

### Ubuntu

```bash
$ sudo apt-get install autoconf automake autotools-dev curl python3 libmpc-dev \
      libmpfr-dev libgmp-dev gawk build-essential bison flex texinfo gperf libtool \
      patchutils bc zlib1g-dev libexpat-dev
$ git clone https://github.com/riscv/riscv-gnu-toolchain
$ cd riscv-gnu-toolchain
$ ./configure --prefix=/path/to/install --with-arch=rv32gc --with-abi=ilp32d # for 32-bit toolchain
$ [sudo] make # sudo is required depending on the path chosen in the previous setup
```

Make sure to add the path `/path/to/install` to your `$PATH` in the `.bashrc/cshrc`.

# Installing RISC-V Reference Models: Spike and SAIL

This section will guide you through the installation of two important RISC-V reference models: Spike and SAIL. These models are often used as reference models in the RISCOF framework.

### 1. Spike (riscv-isa-sim)

Spike is the official RISC-V ISA simulator, also known as the RISC-V ISA simulator (riscv-isa-sim). It is commonly used as a reference model in RISCOF for compliance testing.

### Installation Steps for Spike

```bash
$ sudo apt-get install device-tree-compiler
$ git clone https://github.com/riscv-software-src/riscv-isa-sim.git
$ cd riscv-isa-sim
$ mkdir build
$ cd build
$ ../configure --prefix=/path/to/install
$ make
$ [sudo] make install
```

Note: Use sudo if the installation path requires administrative privileges.

### 2. SAIL (SAIL C-emulator)

First install the [Sail Compiler](https://github.com/rems-project/sail/). It is recommended to use the pre-compiled [binary release](https://github.com/rems-project/sail/releases). This can be performed as follows:

```bash
$ sudo apt-get install libgmp-dev pkg-config zlib1g-dev curl
$ curl --location https://github.com/rems-project/sail/releases/latest/download/sail.tar.gz | [sudo] tar xvz --directory=/path/to/install --strip-components=1
```

Note: Make sure to add the path `/path/to/install` to your `$PATH`.

Then build the RISC-V Sail Model:

```bash
$ git clone https://github.com/riscv/sail-riscv.git
$ cd sail-riscv
$ ./build_simulators.sh
```

This will create a C simulator in `build/c_emulator/sail_riscv_sim`. You will need to add this path to your `$PATH` or create an alias to execute it from the command line.

## Necessary Env Files

To run tests via RISCOF, you will need to provide the following items:

- **config.ini**: This file is a basic configuration file following the INI syntax. This file will capture information like the name of the DUT/reference plugins, path to the plugins, path to the riscv-config based YAMLs, etc. This file is located at `riscof-plugins/rv32/config.ini` for RV32 and at `riscof-plugins/rv64/config.ini` for `RV64`

- **riscv-test-suite/**: The directory contains the architectural test suites.

- **riscv-config/**: The repository containing the configuration files for various RISC-V implementations. You can clone the required repository using the following commands:

```
$ git clone https://github.com/riscv/riscv-config.git
```

## Running the Tests

Once everything is set up, you can run the tests using the following command:

```
$ riscof run --config config.ini --suite riscv-test-suite/ --env riscv-test-suite/env
```

If you only want to use spike as the reference model to test, you can use the following command to using the sample environment:

```
$ cd riscof-plugins/rv32 #If you want to run the rv64 test, change this to rv64
$ riscof run --config config.ini --suite ../../riscv-test-suite/ --env ../../riscv-test-suite/env
```

## Running the coverage command

You can run the coverage using the following command:

```
$ riscof coverage --config=config.ini --cgf-file covergroups/dataset.cgf --cgf-file covergroups/m/rv32im.cgf --suite /riscv-test-suite/rv32i_m/M --env /riscv-test-suite/env
```

## Licensing

In general:

- code is licensed under one of the following:
  - the BSD 3-clause license (SPDX license identifier `BSD-3-Clause`);
  - the Apache License (SPDX license identifier `Apache-2.0`); while
- documentation is licensed under the Creative Commons Attribution 4.0 International license (SPDX license identifier `CC-BY-4.0`).

The files [`COPYING.BSD`](./COPYING.BSD), [`COPYING.APACHE`](./COPYING.APACHE) and [`COPYING.CC`](./COPYING.CC) in the top level directory contain the complete text of these licenses.
