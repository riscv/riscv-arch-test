# One time setup needed to build and run tests for rv64 (rv32 would also require a custom toolchain)

# Tested against Ubuntu 24.04 in Feb 2025. Spike and the other tools change occasionally, breaking things below

sudo apt-get install autoconf automake autotools-dev curl python3 libmpc-dev libmpfr-dev libgmp-dev gawk build-essential bison flex texinfo gperf libtool patchutils bc zlib1g-dev libexpat-dev python3.6 gcc-riscv64-unknown-elf device-tree-compiler

python3 -m venv env/venv

env/venv/bin/pip3 install git+https://github.com/riscv/riscof.git
env/venv/bin/pip3 install --editable riscv-ctg
env/venv/bin/pip3 install --editable riscv-isac

# Install newer riscv-config
env/venv/bin/pip3 install git+https://github.com/riscv-software-src/riscv-config.git

# Build Spike
cd env
git clone https://github.com/riscv-software-src/riscv-isa-sim.git
cd riscv-isa-sim
mkdir build
cd build
../configure --prefix $(pwd)/../../spike
make -j16
cd ../../..
