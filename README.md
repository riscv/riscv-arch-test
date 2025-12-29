# RISC-V Architectural Certification Tests

The RISC-V Architectural Certification Tests (ACTs) are a set of assembly language tests designed to certify that a design faithfully implements the RISC-V specification. These are not verification tests and additional verification should be run on all processors. For additional details on the certification process, see [LINK COMING SOON]().

## Getting Started

This section serves as a quick guide to set up the ACT environment and ensure you can run tests successfully on the RISC-V Sail golden reference model.

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

The ACT framework is compatible with GCC or LLVM. This guide uses GCC, but if you prefer LLVM you just need to set the path for the compiler appropriately when [creating your config file](#configfile).

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

The ACTs use [`riscv-unified-db`](https://github.com/riscv-software-src/riscv-unified-db) for configuration validation and parsing. UDB requires a container to run. Currently, the ACTs are only compatable with the Podman container runtime. Work is ongoing to remove this dependency.

To install Podman:

```bash
# On Ubuntu/Debian
$ sudo apt-get install podman
# On Fedora/CentOS/RHEL
$ sudo dnf install podman
```

## Licensing

In general:

- code is licensed under one of the following:
  - the BSD 3-clause license (SPDX license identifier `BSD-3-Clause`);
  - the Apache License (SPDX license identifier `Apache-2.0`); while
- documentation is licensed under the Creative Commons Attribution 4.0 International license (SPDX license identifier `CC-BY-4.0`).

The files [`COPYING.BSD`](./COPYING.BSD), [`COPYING.APACHE`](./COPYING.APACHE) and [`COPYING.CC`](./COPYING.CC) in the top level directory contain the complete text of these licenses.
