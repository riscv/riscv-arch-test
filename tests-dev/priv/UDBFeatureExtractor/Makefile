# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 RISC-V International
#
# Makefile for the UDB feature extractor (tests-dev/priv/UDBFeatureExtractor)
#
# Adapted by David Harris from the original by Jayant Malvi (riscv-arch-test #1655),
# with assistance from Claude.
#
# Usage, from the repository root:
#   make -f tests-dev/priv/UDBFeatureExtractor/Makefile            # build and run on Sail (RVA23S64)
#   make -f tests-dev/priv/UDBFeatureExtractor/Makefile XLEN=32 CONFIG_DIR=config/sail/sail-rv32-max
#   make -f tests-dev/priv/UDBFeatureExtractor/Makefile test       # self-test against Sail configurations
#   make -f tests-dev/priv/UDBFeatureExtractor/Makefile regression JOBS=8   # every config/ vs its UDB yaml
#   make -f tests-dev/priv/UDBFeatureExtractor/Makefile elf CONFIG_DIR=config/cores/cvw/cvw-rv64gc
#
# CONFIG_DIR supplies the DUT's rvmodel_macros.h (console output and halt) and link.ld (memory
# map).  Nothing else from the configuration is used, because the point of this program is to
# produce the configuration.  SIM and SIM_FLAGS run the ELF; the console output is the YAML.

REPO_ROOT  := $(shell git rev-parse --show-toplevel 2>/dev/null || pwd)
SRC_DIR    := $(REPO_ROOT)/tests-dev/priv/UDBFeatureExtractor
BUILD_DIR  ?= $(REPO_ROOT)/work/UDBFeatureExtractor

XLEN       ?= 64
CONFIG_DIR ?= $(REPO_ROOT)/config/sail/sail-RVA23S64
SIM        ?= sail_riscv_sim
SIM_FLAGS  ?= --config $(CONFIG_DIR)/sail.json
OUT        ?= $(BUILD_DIR)/extracted_config$(XLEN).yaml

CC      := riscv64-unknown-elf-gcc
OBJDUMP := riscv64-unknown-elf-objdump
PYTHON  ?= python3

# Compiled for the E base so the extractor itself runs on RV32E and RV64E harts; each probe enables
# its own extension with `.option arch`.  GCC warns that the lp64e ABI may be deprecated, hence
# -Wno-deprecated.  --no-relax keeps the linker from introducing gp-relative addressing, so no gp
# setup is needed.
ARCH := rv$(XLEN)e_zicsr
ABI  := $(if $(filter 32,$(XLEN)),ilp32e,lp64e)

CFLAGS := -march=$(ARCH) -mabi=$(ABI) -mcmodel=medany \
          -O2 -g -std=gnu11 -ffreestanding -fno-builtin -nostdlib -nostartfiles -static \
          -Wall -Wextra -Wno-deprecated \
          -Wl,--no-relax -Wl,--no-warn-rwx-segments \
          -I$(SRC_DIR) -I$(CONFIG_DIR)

SRCS := start.S feature_extractor.c parameters.c console.c
DEPS := extensions.h probe.h console.h
ELF  := $(BUILD_DIR)/feature_extractor$(XLEN).elf

.PHONY: all elf run dump test regression clean help
all: run

$(BUILD_DIR):
	mkdir -p $@

elf: $(ELF)
$(ELF): $(addprefix $(SRC_DIR)/,$(SRCS) $(DEPS)) $(CONFIG_DIR)/link.ld $(CONFIG_DIR)/rvmodel_macros.h | $(BUILD_DIR)
	$(CC) $(CFLAGS) -T $(CONFIG_DIR)/link.ld $(addprefix $(SRC_DIR)/,$(SRCS)) -o $@

run: $(ELF)
	$(SIM) $(SIM_FLAGS) --terminal-log $(OUT) $(ELF)
	@echo "--- $(OUT)"
	@cat $(OUT)

dump: $(ELF)
	$(OBJDUMP) -d $(ELF) > $(ELF:.elf=.dump)
	@echo "Disassembly written to $(ELF:.elf=.dump)"

# Run the extractor on the Sail max configurations with extensions switched off in turn and check
# that the output matches each configuration
test:
	$(PYTHON) $(SRC_DIR)/test/run_sail_tests.py --repo-root $(REPO_ROOT) --sim $(SIM) --build-dir $(BUILD_DIR)

# Run the extractor on every configuration under config/ that has a run_cmd.txt, using that
# command, and compare the result with the configuration's UDB yaml.  JOBS configurations run in
# parallel; configurations whose simulator is not installed are skipped.
JOBS ?= 1
regression:
	$(PYTHON) $(SRC_DIR)/test/regression.py --repo-root $(REPO_ROOT) --build-dir $(BUILD_DIR)/regression --jobs $(JOBS)

clean:
	rm -rf $(BUILD_DIR)

help:
	@echo "make -f tests-dev/priv/UDBFeatureExtractor/Makefile [target] [XLEN=32|64] [CONFIG_DIR=...] [SIM=...] [SIM_FLAGS=...]"
	@echo "  run   build and run, writing the extracted UDB YAML to OUT (default)"
	@echo "  elf   build only"
	@echo "  dump  disassemble"
	@echo "  test  self-test against the Sail max configurations for both XLENs"
	@echo "  regression  run every config/**/run_cmd.txt configuration and compare with its UDB yaml (JOBS=n)"
	@echo "  clean remove $(BUILD_DIR)"
