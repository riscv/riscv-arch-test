# RISC-V Architectural Certification Tests

The RISC-V Architectural Certification Tests (ACTs) are a set of assembly language tests designed to certify that a design faithfully implements the RISC-V specification. These are not verification tests and additional verification should be run on all processors. For additional details on the certification process, see [LINK COMING SOON]().

## Getting Started

This section serves as a guide to set up the ACT environment and generate ELFs for a DUT.

### Prerequisites

The ACTs require several tools to generate and run correctly. Ensure all of the following tools are installed before proceeding.

#### 1. Python/uv

The test generator and framework are written in Python. The recommended way of installing and running Python is using the uv project manager, which will handle Python versions, virtual environments, and dependencies transparently.

To install uv:

```bash
$ curl -LsSf https://astral.sh/uv/install.sh | sh
```

For more details on uv and alternate installation methods, see the [uv installation guide](https://docs.astral.sh/uv/getting-started/installation/).

#### 2. RISC-V Compiler

The ACT framework is compatible with GCC or LLVM. This guide uses GCC, but if you prefer LLVM you just need to set the path for the compiler appropriately when [creating your config file](#act-framework-configuration-file).

> **Note**: The toolchain installation will take significant time. Please be patient.

To install `riscv64-unknown-elf-gcc`:

```bash
# On Ubuntu/Debian:
$ sudo apt-get install autoconf automake autotools-dev curl python3 python3-pip \
  python3-tomli libmpc-dev libmpfr-dev libgmp-dev gawk build-essential bison \
  flex texinfo gperf libtool patchutils bc zlib1g-dev libexpat-dev ninja-build \
  git cmake libglib2.0-dev libslirp-dev libncurses-dev
# On Fedora/CentOS/RHEL:
$ sudo dnf install autoconf automake python3 libmpc-devel mpfr-devel gmp-devel \
  gawk  bison flex texinfo patchutils gcc gcc-c++ zlib-devel expat-devel \
  libslirp-devel ncurses-devel
# On all distros:
$ git clone https://github.com/riscv/riscv-gnu-toolchain
$ cd riscv-gnu-toolchain
$ ./configure --prefix=</path/to/install> --with-multilib-generator="rv32e-ilp32e--;rv32i-ilp32--;rv32im-ilp32--;rv32iac-ilp32--;rv32imac-ilp32--;rv32imafc-ilp32f--;rv32imafdc-ilp32d--;rv64i-lp64--;rv64ic-lp64--;rv64iac-lp64--;rv64imac-lp64--;rv64imafdc-lp64d--;rv64im-lp64--;"
$ [sudo] make # sudo is required depending on the path chosen in the previous setup
```

Make sure to add the path `/path/to/install` to your `$PATH` in the `.bashrc/cshrc`.

For more information or if you have issues installing, refer to the [riscv-gnu-toolchain README](https://github.com/riscv-collab/riscv-gnu-toolchain).

#### 3. RISC-V Sail Golden Reference Model

The ACTs use the RISC-V Sail model to generate expected results. It is currently compatible with version 0.9 of the model.

To install the sail model:

```bash
$ curl --location https://github.com/riscv/sail-riscv/releases/download/0.9/sail-riscv-$(uname)-$(arch).tar.gz | sudo tar xvz --directory=</path/to/install> --strip-components=1
```

For more details on the Sail model and alternate installation methods, see the [sail-riscv README](https://github.com/riscv/sail-riscv).

#### 4. Container Runtime

The ACTs use [`riscv-unified-db`](https://github.com/riscv-software-src/riscv-unified-db) for configuration validation and parsing. UDB requires a container to run. Currently, the ACTs are only compatible with the Podman container runtime. Work is ongoing to remove this dependency. <!-- TODO: Update this when other containers are supported -->

To install Podman:

```bash
# On Ubuntu/Debian
$ sudo apt-get install podman
# On Fedora/CentOS/RHEL
$ sudo dnf install podman
```

### Configuration

Several configuration files are needed to tell the ACT framework how to find your tools, what extensions and parameters are supported by your implementation, and how to perform implementation-specific functions. See [config/duts/cvw/cvw-rv64gc](config/duts/cvw/cvw-rv64gc) for a complete example configuration directory.

#### ACT Framework Configuration File

The ACT Framework configuration YAML file contains all of the top-level configuration options. It species the compiler and reference model along with the paths to your UDB config file, linker script, and header directory. See [test_config.yaml](config/duts/cvw/cvw-rv64gc/test_config.yaml) for an example.

#### UDB Config File

A [UDB](https://github.com/riscv-software-src/riscv-unified-db) configuration file is used to specify all of the implementation details for your DUT. This includes al of the supported extensions and the value of all relevant parameters. See [cvw-rv64gc.yaml](config/duts/cvw/cvw-rv64gc/cvw-rv64gc.yaml) for an example and [the riscv-unified-db repo](https://github.com/riscv-software-src/riscv-unified-db) for more details.

#### `model_test.h` Trickbox Macro Implementation

The ACT Framework uses a selection of assembly macros to run DUT-specific code to boot the DUT, print to a console, terminate the test, and trigger interrupts. These macros are defined and explained in detail in the [CTP](https://riscv-non-isa.github.io/riscv-arch-test/#_trick_box_macros). Complete examples are available for an example DUT ([config/duts/cvw/cvw-rv64gc/model_test.h](config/duts/cvw/cvw-rv64gc/model_test.h)) and for the RISC-V Sail reference model ([config/ref/sail-rv64gc/model_test.h](config/ref/sail-rv64gc/model_test.h)).

#### Linker Script

A linker script is needed to place the code and data regions in the appropriate place for the DUT's memory map. This can be customized as needed, but it must adhere to the following requirements:

- The `ENTRY` point must be `rvtest_entry_point`.
  - DUT-specific boot code can be run using the `RVMODEL_BOOT` macro, which `rvtest_entry_point` will run before anything else. It should not be directly called by the `ENTRY` point.
- There must be a `.text` section.
- There must be a `.data` section.
- There must be a `.bss` section.

For an example linker script that should work for most basic implementations (except for modifying the base address), see [config/duts/cvw/cvw-rv64gc/link.ld](config/duts/cvw/cvw-rv64gc/link.ld).

#### Other Config Files <!-- TODO: Remove this section when these files are autogenerated -->

The framework currently relies on three other config files. All three of these files will eventually be generated from the UDB config file, but that is still a work in progress, so they need to be handwritten for now. See [config/duts/cvw/cvw-rv64gc](config/duts/cvw/cvw-rv64gc) for examples of these files.

- `sail.json` Sail model configuration
- `rvtest_config.svh` and `rvtest_config.h` SystemVerilog and C header files that define the supported extensions and parameter values.

### Generating Self-Checking ELFs

Once all [dependencies](#prerequisites) are installed and the [configuration files](#configuration) for your DUT have been created, run the following command to generate self-checking ELFs.

> [!NOTE]
>
> Due to current limitations with the ACT framework, the directory with the config files for your DUT must be in the `riscv-arch-test` directory (the `config/duts` subdirectory is recommended). These command also **must** be run from the `riscv-arch-test` directory.

```bash
CONFIG_FILES=config/duts/<your_config_here>/test_config.yaml make --jobs $(nproc)
```

This will create all of the ELFs that apply to your DUT (based on the provided UDB configuration) in the `work/<config_name>/elfs` directory. These ELFs have the expected results compiled into them and use the provided macros and linker script.

### Running Certification Tests

All ELFs produced in the `work/<config_name>/elfs` directory must be run on your DUT for certification. Depending on your DUT, you may need to convert these ELFs into a format that your testbench accepts (hex files are common). It is recommended to use a script or Makefile to run all ELFs in the directory on your DUT. Some examples for this are coming soon.

Each test will print either `RVCP-SUMMARY: Test File "<test_name.S>": PASSED` or `RVCP-SUMMARY: Test File "<test_name.S>": FAILED`. For any test that fails, additional debug information will be printed out including the failing PC, instruction, register that mismatched, expected value, and actual value.

A common source of errors is configuration issues, so make sure that the UDB and Sail config files match what your DUT does.

## Licensing

In general:

- code is licensed under one of the following:
  - the BSD 3-clause license (SPDX license identifier `BSD-3-Clause`);
  - the Apache License (SPDX license identifier `Apache-2.0`); while
- documentation is licensed under the Creative Commons Attribution 4.0 International license (SPDX license identifier `CC-BY-4.0`).

The files [`COPYING.BSD`](./COPYING.BSD), [`COPYING.APACHE`](./COPYING.APACHE) and [`COPYING.CC`](./COPYING.CC) in the top level directory contain the complete text of these licenses.
