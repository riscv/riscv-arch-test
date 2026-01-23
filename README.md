
# RISC-V Architecture Test SIG

This is a repository for the work of the RISC-V Foundation Architecture Test SIG. The repository owners are:

- Neel Gala (InCore Semiconductors)
- Marc Karasek (Inspire Semiconductors)

Quick Links:

  - Details of the RISC-V Foundation, the work of its task groups, and how to become a member can be found at [riscv.org](https://riscv.org/).
  - For more details and documentation on the current test environment see: [doc/README.adoc](doc/README.adoc)
  - For more details on the test format spec see: [spec/TestFormatSpec.adoc](spec/TestFormatSpec.adoc)
  - For contributions and reporting issues please refer to [CONTRIBUTION.md](CONTRIBUTION.md)
  - For more details on the usage of the current framework see : [RISCOF](https://riscof.readthedocs.io/)

**Note : The RISCOF framework requires a
[riscv-config](https://github.com/riscv-software-src/riscv-config) YAML to describe the
configurations implemented by the DUT**

## Old Framework

The older 2.x version of the framework (based on Makefiles) can be found in a separate branch :
[old-framework-2.x](https://github.com/riscv-non-isa/riscv-arch-test/tree/old-framework-2.x). This
branch is no longer officially supported and all changes must occur on the main branch.

## Test Disclaimers

The following are the exhaustive list of disclaimers that can be used as waivers by target owners 
when reporting the status of pass/fail on the execution of the architectural suite on their respective targets.

1. For the following set of misaligned-tests, signature mismatches will occur if misaligned accesses can sometimes succeed (without an exception) and sometimes fail on the DUT.

   1. rv32i_m/privilege/src/misalign-[lb[u],lh[u],lw,sh,sb,sw]-01.S
   2. rv64i_m/privilege/src/misalign-[lb[u],lh[u],lw[u],ld,sb,sh,sw,sd]-01.S

3. The machine mode trap handler used in the privilege tests assumes one of the following conditions. 
   Targets not satisfying any of the following conditions are bound to fail the entire 
   rv32i_m/privilege and rv64i_m/privilege tests:
   1. The target must have implemented mtvec which is completely writable by the test in machine mode.
   2. The target has initialized mtvec, before entering the test (via RVMODEL_BOOT), to point to a memory location which has both read and write permissions.

## Test Stats

The coverage and data propogation statistics of each test are hosted on
[Google-Drive](https://drive.google.com/drive/folders/1KBRy6OgxnOPTDgyfJDj0gcMi5VdMLtVo?usp=share_link) for reference. This to avoid bloating this repo in size.

## Contribution process

Please refer to to [CONTRIBUTION.md](CONTRIBUTION.md) for guidelines on contributions.

## Licensing

In general:
- code is licensed under one of the following:
  - the BSD 3-clause license (SPDX license identifier `BSD-3-Clause`);
  - the Apache License (SPDX license identifier `Apache-2.0`); while
- documentation is licensed under the Creative Commons Attribution 4.0 International license (SPDX license identifier `CC-BY-4.0`).

The files [`COPYING.BSD`](./COPYING.BSD), [`COPYING.APACHE`](./COPYING.APACHE) and [`COPYING.CC`](./COPYING.CC) in the top level directory contain the complete text of these licenses.

## Engineering practice

- Documentation uses the structured text format _AsciiDoc_.  See [`doc/README.adoc`](doc/README.adoc) for more details.

- Some directories use `ChangeLog` files to track changes in the code and documentation.  Please honor these, keeping them up to date and including the ChangeLog entry in the _git_ commit message.

- Please include a comment with the SPDX license identifier in all source files, for example:
```
// SPDX-License-Identifier: BSD-3-Clause
```

## Quick Links:

- RISCOF \[[DOCS](https://riscof.readthedocs.io/en/latest/)\] \[[REPO](https://github.com/riscv-software-src/riscof)\]: This is the next version of the architectural test framework currently under development
- RISCV-ISAC \[[DOCS](https://riscv-isac.readthedocs.io/en/latest/index.html)\]: This is an ISA level coverage extraction tool for RISC-V which used to generate the coverage statistics of the architectural tests.
- RISCV-CTG: \[[DOCS](https://riscv-ctg.readthedocs.io/en/latest/index.html)\]: This is a RISC-V Architectural Test generator used to generate some of the tests already checked into this repository.
- [Videos](https://youtu.be/VIW1or1Oubo): This Global Forum 2020 video provides an introduction to the above mentioned tools
- [riscvOVPsim](https://github.com/riscv-ovpsim/imperas-riscv-tests): Imperas freeware RISC-V reference simulator for compliance testing
- [riscvOVPsimPlus](https://www.ovpworld.org/riscvOVPsimPlus/): Imperas enhanced freeware RISC-V reference simulator for test development and verification

# Getting Started

This section serves as a quick guide to set up RISCOF and perform a sample validation check between Spike (DUT in this case) and Sail-riscv (Reference Golden Model). This guide will help you set up all the required tooling for running RISCOF on your system.

### Install Python

### Ubuntu

For Ubuntu, you can directly install Python using the Universe repository:

```bash
$ sudo apt-get install python3.6
$ pip3 install --upgrade pip
```
You should now have two binaries: `python3` and `pip3` available in your `$PATH`.

### Install riscv-ctg & riscv-isac
To install riscv-ctg, run this command in your terminal:

```
$ git clone https://github.com/riscv-non-isa/riscv-arch-test.git
$ cd riscv-ctg
$ pip3 install --editable .
$ cd ..
$ cd riscv-isac
$ pip3 install --editable .
```

This is the preferred method to install riscv-isac and riscv-ctg, as updated riscv-ctg will always be maintained here.

### Install RISCOF
To install RISCOF, run this command in your terminal:

```
$ pip3 install git+https://github.com/riscv/riscof.git
```
This is the preferred method to install RISCOF, as it will always install the most recent stable release.

To run RISCOF, you need to install two components: riscv-ctg and riscv-isac.


### Test RISCOF
Once you have installed `RISCOF`, you can execute `riscof --help` to print the help routine:

```bash
$ riscof --help
Usage: riscof [OPTIONS] COMMAND [ARGS]...

Options:
  --version                       Show the version and exit.
  -v, --verbose [info|error|debug]
                                  Set verbose level
  --help                          Show this message and exit.

Commands:
  arch-test     Setup and maintenance for Architectural TestSuite.
  coverage      Run the tests on DUT and reference and compare signatures
  gendb         Generate Database for the Suite.
  run           Run the tests on DUT and reference and compare signatures
  setup         Initiate Setup for riscof.
  testlist      Generate the test list for the given DUT and suite.
  validateyaml  Validate the Input YAMLs using riscv-config.
```


## Install RISCV-GNU Toolchain

This guide will use the 32-bit riscv-gnu toolchain to compile the architectural suite. If you already have the 32-bit gnu-toolchain available, you can skip to the next section.

> **Note**: The git clone and installation will take significant time. Please be patient. If you face issues with any of the following steps, please refer to [riscv-gnu-toolchain](https://github.com/riscv-collab/riscv-gnu-toolchain) for further help in installation.

### Ubuntu

```bash
$ sudo apt-get install autoconf automake autotools-dev curl python3 libmpc-dev \
      libmpfr-dev libgmp-dev gawk build-essential bison flex texinfo gperf libtool \
      patchutils bc zlib1g-dev libexpat-dev
$ git clone --recursive https://github.com/riscv/riscv-gnu-toolchain
$ git clone --recursive https://github.com/riscv/riscv-opcodes.git
$ cd riscv-gnu-toolchain
$ ./configure --prefix=/path/to/install --with-arch=rv32gc --with-abi=ilp32d # for 32-bit toolchain
$ [sudo] make # sudo is required depending on the path chosen in the previous setup
```

Make sure to add the path `/path/to/install` to your `$PATH` in the `.bashrc/cshrc`.

With this, you should now have all the following available as command line arguments:

```bash
riscv32-unknown-elf-addr2line      riscv32-unknown-elf-elfedit
riscv32-unknown-elf-ar             riscv32-unknown-elf-g++
riscv32-unknown-elf-as             riscv32-unknown-elf-gcc
riscv32-unknown-elf-c++            riscv32-unknown-elf-gcc-8.3.0
riscv32-unknown-elf-c++filt        riscv32-unknown-elf-gcc-ar
riscv32-unknown-elf-cpp            riscv32-unknown-elf-gcc-nm
riscv32-unknown-elf-gcc-ranlib     riscv32-unknown-elf-gprof
riscv32-unknown-elf-gcov           riscv32-unknown-elf-ld
riscv32-unknown-elf-gcov-dump      riscv32-unknown-elf-ld.bfd
riscv32-unknown-elf-gcov-tool      riscv32-unknown-elf-nm
riscv32-unknown-elf-gdb            riscv32-unknown-elf-objcopy
riscv32-unknown-elf-gdb-add-index  riscv32-unknown-elf-objdump
riscv32-unknown-elf-ranlib         riscv32-unknown-elf-readelf
riscv32-unknown-elf-run            riscv32-unknown-elf-size
riscv32-unknown-elf-strings        riscv32-unknown-elf-strip
```
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
$ ./build_simulator.sh
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
