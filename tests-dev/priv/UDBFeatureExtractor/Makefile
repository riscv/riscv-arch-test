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
# test_config.yaml may name a linker script and include directory other than CONFIG_DIR's
LINKER_SCRIPT   ?= $(CONFIG_DIR)/link.ld
DUT_INCLUDE_DIR ?= $(CONFIG_DIR)

CC      := riscv64-unknown-elf-gcc
OBJDUMP := riscv64-unknown-elf-objdump

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
          -I$(SRC_DIR) -I$(REPO_ROOT)/tests/env -I$(DUT_INCLUDE_DIR)

# make_config.py adds -DTRACE_PROBES and -DSKIP_PROBES='"name,..."' when a probe stopped the simulation
EXTRA_CFLAGS ?=

SRCS := start.S feature_extractor.c parameters.c console.c
DEPS := extensions.h probe.h udb_parameters.h console.h
ELF  := $(BUILD_DIR)/feature_extractor$(XLEN).elf

.PHONY: all elf xlen-elf run dump test regression config config-regression clean help
all: run

$(BUILD_DIR):
	mkdir -p $@

elf: $(ELF)
$(ELF): $(addprefix $(SRC_DIR)/,$(SRCS) $(DEPS)) $(LINKER_SCRIPT) $(DUT_INCLUDE_DIR)/rvmodel_macros.h | $(BUILD_DIR)
	$(CC) $(CFLAGS) $(EXTRA_CFLAGS) -T $(LINKER_SCRIPT) $(addprefix $(SRC_DIR)/,$(SRCS)) -o $@

# xlen_probe prints the hart's XLEN; its code is the same for both builds, which differ only in
# ELF class (simulators refuse an ELF of the other class)
XLEN_ELF := $(BUILD_DIR)/xlen_probe$(XLEN).elf
xlen-elf: $(XLEN_ELF)
$(XLEN_ELF): $(SRC_DIR)/xlen_probe.S $(LINKER_SCRIPT) $(DUT_INCLUDE_DIR)/rvmodel_macros.h | $(BUILD_DIR)
	$(CC) -march=rv$(XLEN)i_zicsr -mabi=$(if $(filter 32,$(XLEN)),ilp32,lp64) -nostdlib -nostartfiles -static \
	  -Wl,--no-relax -Wl,--no-warn-rwx-segments -I$(DUT_INCLUDE_DIR) -T $(LINKER_SCRIPT) $< -o $@

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
	uv run $(SRC_DIR)/test/run_sail_tests.py --repo-root $(REPO_ROOT) --sim $(SIM) --build-dir $(BUILD_DIR)

# Run the extractor on every configuration under config/ that has a run_cmd.txt, using that
# command, and compare the result with the configuration's UDB yaml.  JOBS configurations run in
# parallel; configurations whose simulator is not installed are skipped.
JOBS ?= 1
regression:
	uv run $(SRC_DIR)/test/regression.py --build-dir $(BUILD_DIR)/regression --jobs $(JOBS)

# Generate CONFIG_DIR's UDB yaml and sail.json in CONFIG_OUT from its test_config.yaml, run_cmd.txt,
# link.ld and rvmodel_macros.h; config-regression does that for every configuration and compares
CONFIG_OUT ?= $(BUILD_DIR)/config/$(notdir $(CONFIG_DIR))
config:
	uv run $(SRC_DIR)/make_config.py --config-dir $(CONFIG_DIR) --out-dir $(CONFIG_OUT)
config-regression:
	uv run $(SRC_DIR)/test/make_config_regression.py --build-dir $(BUILD_DIR)/make_config --jobs $(JOBS)

clean:
	rm -rf $(BUILD_DIR)

help:
	@echo "make -f tests-dev/priv/UDBFeatureExtractor/Makefile [target] [XLEN=32|64] [CONFIG_DIR=...] [SIM=...] [SIM_FLAGS=...]"
	@echo "  run   build and run, writing the extracted UDB YAML to OUT (default)"
	@echo "  elf   build only"
	@echo "  dump  disassemble"
	@echo "  test  self-test against the Sail max configurations for both XLENs"
	@echo "  regression  run every config/**/run_cmd.txt configuration and compare with its UDB yaml (JOBS=n)"
	@echo "  config     generate CONFIG_DIR's UDB yaml and sail.json in CONFIG_OUT"
	@echo "  config-regression  generate every configuration and compare with the checked-in yaml and sail.json"
	@echo "  clean remove $(BUILD_DIR)"
