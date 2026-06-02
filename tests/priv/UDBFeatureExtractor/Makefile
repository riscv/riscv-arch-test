# SPDX-License-Identifier: Apache-2.0
# Makefile for tests/priv/UDBFeatureExtractor

REPO_ROOT := $(shell git rev-parse --show-toplevel 2>/dev/null || pwd)
TEST_SRC  := $(REPO_ROOT)/tests/priv/UDBFeatureExtractor
BUILD_DIR := $(REPO_ROOT)/work/UDBFeatureExtractor

SAIL_CONFIG := $(REPO_ROOT)/config/sail/sail-RVA23S64
CVW_CONFIG  := $(REPO_ROOT)/config/cores/cvw/cvw-rv64gc

CC      := riscv64-unknown-elf-gcc
OBJDUMP := riscv64-unknown-elf-objdump
SIM     := sail_riscv_sim

ARCH := rv64i_zicsr
ABI  := lp64

COMMON_CFLAGS := -march=$(ARCH) -mabi=$(ABI) \
                 -mcmodel=medany \
                 -nostartfiles -nostdlib -static \
                 -DXLEN=64 \
                 -DTEST_FLEN=32 \
                 -DSIGNATURE \
                 -Wl,--no-warn-rwx-segments

ARCH_TEST_INC := $(REPO_ROOT)/tests/env

SAIL_CFLAGS := $(COMMON_CFLAGS) \
               -I $(SAIL_CONFIG) \
               -I $(ARCH_TEST_INC)

CVW_CFLAGS := $(COMMON_CFLAGS) \
              -I $(CVW_CONFIG) \
              -I $(ARCH_TEST_INC)

UART_OUT := $(BUILD_DIR)/output.yaml
SAIL_ELF := $(BUILD_DIR)/FeatureExtractor-sail.elf
CVW_ELF  := $(BUILD_DIR)/FeatureExtractor-cvw.elf
DUMP     := $(BUILD_DIR)/FeatureExtractor-sail.dump
NO_M_CFG := $(BUILD_DIR)/no_M_config.json

.PHONY: all sail sail-debug sail-no-M cvw dump clean help

all: sail

$(BUILD_DIR):
	mkdir -p $@

$(SAIL_ELF): $(TEST_SRC)/FeatureExtractor.S | $(BUILD_DIR)
	@echo "=== Compiling for Sail: $(ARCH) / $(ABI) ==="
	$(CC) $(SAIL_CFLAGS) \
	      -T $(SAIL_CONFIG)/link.ld \
	      $< -o $@

sail: $(SAIL_ELF)
	@echo "=== Running on Sail ==="
	$(SIM) --terminal-log $(UART_OUT) $(SAIL_ELF)
	@echo "=== Generated YAML ==="
	@echo "---"
	@cat $(UART_OUT)
	@echo "---"

sail-debug: $(SAIL_ELF)
	$(SIM) --terminal-log $(UART_OUT) \
	       --trace-exception \
	       --trace-htif \
	       $(SAIL_ELF) 2>&1
	@echo "=== UART output ==="
	@cat $(UART_OUT)

$(NO_M_CFG): | $(BUILD_DIR)
	@printf '{\n  "extensions": {\n    "M": { "supported": false }\n  }\n}\n' > $@

sail-no-M: $(SAIL_ELF) $(NO_M_CFG)
	@echo "=== Running Sail with M disabled ==="
	$(SIM) --terminal-log $(UART_OUT).noM \
	       --config-override $(NO_M_CFG) \
	       $(SAIL_ELF)
	@echo "=== Generated YAML without M ==="
	@echo "---"
	@cat $(UART_OUT).noM
	@echo "---"

$(CVW_ELF): $(TEST_SRC)/FeatureExtractor.S | $(BUILD_DIR)
	@echo "=== Compiling for CVW: $(ARCH) / $(ABI) ==="
	$(CC) $(CVW_CFLAGS) \
	      -T $(CVW_CONFIG)/link.ld \
	      $< -o $@

cvw: $(CVW_ELF)
	@echo "=== CVW ELF ready: $(CVW_ELF) ==="

dump: $(SAIL_ELF)
	$(OBJDUMP) -d -s $(SAIL_ELF) > $(DUMP)
	@echo "=== Disassembly written to $(DUMP) ==="

clean:
	rm -rf $(BUILD_DIR)

help:
	@echo "make -f tests/priv/UDBFeatureExtractor/Makefile sail"
	@echo "make -f tests/priv/UDBFeatureExtractor/Makefile sail-no-M"
	@echo "make -f tests/priv/UDBFeatureExtractor/Makefile sail-debug"
	@echo "make -f tests/priv/UDBFeatureExtractor/Makefile cvw"
	@echo "make -f tests/priv/UDBFeatureExtractor/Makefile dump"
	@echo "make -f tests/priv/UDBFeatureExtractor/Makefile clean"