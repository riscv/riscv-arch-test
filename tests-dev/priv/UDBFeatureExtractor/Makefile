# SPDX-License-Identifier: Apache-2.0
# Makefile for tests-dev/priv/UDBFeatureExtractor
#
# Usage:
#   make                          # build and run with default config (Sail RVA23S64)
#   make run                      # run feature extractor, produce extracted_config.yaml
#   make run-no-M                 # run with M extension disabled
#   make dump                     # disassemble ELF
#   make clean                    # remove build artifacts
#
# Override defaults:
#   make CONFIG_DIR=config/sail/sail-RVA23S64 SIM=sail_riscv_sim
#   make CONFIG_DIR=config/cores/cvw/cvw-rv64gc SIM=<cvw_sim>

REPO_ROOT := $(shell git rev-parse --show-toplevel 2>/dev/null || pwd)
TEST_SRC  := $(REPO_ROOT)/tests-dev/priv/UDBFeatureExtractor
BUILD_DIR := $(REPO_ROOT)/work/UDBFeatureExtractor

# ── Per-target configuration (override on command line) ──────────────────────
CONFIG_DIR ?= $(REPO_ROOT)/config/sail/sail-RVA23S64
SIM        ?= sail_riscv_sim
XLEN       ?= 64

ifeq ($(XLEN),32)
ABI        ?= ilp32
else
ABI        ?= lp64
endif

CC      := riscv64-unknown-elf-gcc
OBJDUMP := riscv64-unknown-elf-objdump

ARCH := rv$(XLEN)i_zicsr_zifencei

ARCH_TEST_INC := $(REPO_ROOT)/tests/env

COMMON_FLAGS := \
    -march=$(ARCH) -mabi=$(ABI) \
    -mcmodel=medany \
    -nostartfiles -nostdlib -static \
    -DXLEN=$(XLEN) \
    -DTEST_FLEN=32 \
    -DSIGNATURE \
    -Wl,--no-warn-rwx-segments \
    -Wl,-e,rvtest_entry_point

CFLAGS := $(COMMON_FLAGS) \
	-I$(TEST_SRC) \
    -I$(CONFIG_DIR) \
    -I$(ARCH_TEST_INC)

# C-version extras:
#   -std=gnu11      required for inline asm syntax
#   -ffreestanding  no hosted-environment assumptions
#   -O1 -g          mild optimisation + debug info
C_EXTRA := -ffreestanding -O1 -g -std=gnu11 \
           -fno-builtin -fno-builtin-printf -fno-builtin-puts

YAML_C_OUT := $(BUILD_DIR)/extracted_config.yaml
YAML_C_NOM := $(BUILD_DIR)/extracted_config-no-M.yaml

ELF           := $(BUILD_DIR)/FeatureExtractorC.elf
NO_M_CFG      := $(BUILD_DIR)/no_M_config.json
LINKER_TEMPLATE := $(TEST_SRC)/link.template.ld
LINKER_SCRIPT   := $(BUILD_DIR)/link.ld


C_SRCS := \
    $(TEST_SRC)/FeatureExtractorC.S \
    $(TEST_SRC)/crt.S \
    $(TEST_SRC)/feature_extractor.c \
    $(TEST_SRC)/syscalls.c

.PHONY: all run run-no-M dump clean help
all: run

$(BUILD_DIR):
	mkdir -p $@

$(LINKER_SCRIPT): $(LINKER_TEMPLATE) | $(BUILD_DIR)
	@sed 's|INCLUDE "link.ld"|INCLUDE "$(CONFIG_DIR)/link.ld"|g' $< > $@

$(ELF): $(C_SRCS) $(LINKER_SCRIPT) | $(BUILD_DIR)
	@echo "=== Compiling FeatureExtractorC ==="
	$(CC) $(CFLAGS) $(C_EXTRA) -T $(LINKER_SCRIPT) $(C_SRCS) -o $@

$(NO_M_CFG): | $(BUILD_DIR)
	@printf '{\n  "extensions": {\n    "M": { "supported": false }\n  }\n}\n' > $@

run: $(ELF)
	@echo "=== Running FeatureExtractor ==="
	$(SIM) --terminal-log $(YAML_C_OUT) $(ELF)
	@echo "---"
	@cat $(YAML_C_OUT)
	@echo "---"

run-no-M: $(ELF) $(NO_M_CFG)
	@echo "=== Running FeatureExtractor with M disabled ==="
	$(SIM) --terminal-log $(YAML_C_NOM) --config-override $(NO_M_CFG) $(ELF)
	@echo "---"
	@cat $(YAML_C_NOM)
	@echo "---"

dump: $(ELF)
	$(OBJDUMP) -d -s $(ELF) > $(BUILD_DIR)/FeatureExtractorC.dump
	@echo "=== Disassembly written to $(BUILD_DIR)/FeatureExtractorC.dump ==="

clean:
	rm -rf $(BUILD_DIR)

help:
	@echo "Usage: make -f tests-dev/priv/UDBFeatureExtractor/Makefile [target] [CONFIG_DIR=...] [SIM=...]"
	@echo ""
	@echo "Targets:"
	@echo "  run        Build and run feature extractor (default)"
	@echo "  run-no-M   Run with M extension disabled"
	@echo "  dump       Disassemble ELF"
	@echo "  clean      Remove build artifacts"
	@echo ""
	@echo "Defaults:"
	@echo "  CONFIG_DIR = config/sail/sail-RVA23S64"
	@echo "  SIM        = sail_riscv_sim"
	@echo ""
	@echo "Example (CVW):"
	@echo "  make CONFIG_DIR=config/cores/cvw/cvw-rv64gc SIM=<cvw_sim>"
