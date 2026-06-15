# SPDX-License-Identifier: Apache-2.0
# Makefile for tests-dev/priv/UDBFeatureExtractor

REPO_ROOT := $(shell git rev-parse --show-toplevel 2>/dev/null || pwd)
TEST_SRC  := $(REPO_ROOT)/tests-dev/priv/UDBFeatureExtractor
BUILD_DIR := $(REPO_ROOT)/work/UDBFeatureExtractor

SAIL_CONFIG := $(REPO_ROOT)/config/sail/sail-RVA23S64
CVW_CONFIG  := $(REPO_ROOT)/config/cores/cvw/cvw-rv64gc
CVW_WORK_CONFIG := $(REPO_ROOT)/work/cvw-rv64gc

CC      := riscv64-unknown-elf-gcc
OBJDUMP := riscv64-unknown-elf-objdump
SIM     := sail_riscv_sim

ARCH := rv64i_zicsr_zifencei
ABI  := lp64

# riscv_arch_test.h lives in tests/env; rvtest_config.h lives in the per-target config dir (e.g. config/sail/sail-RVA23S64).
# Both must be on the include path.
ARCH_TEST_INC := $(REPO_ROOT)/tests/env

COMMON_FLAGS := \
    -march=$(ARCH) -mabi=$(ABI) \
    -mcmodel=medany \
    -nostartfiles -nostdlib -static \
    -DXLEN=64 \
    -DTEST_FLEN=32 \
    -DSIGNATURE \
    -Wl,--no-warn-rwx-segments \
    -Wl,-e,rvtest_entry_point \

SAIL_FLAGS := $(COMMON_FLAGS) \
	-I$(SAIL_CONFIG) \
	-I$(CVW_WORK_CONFIG) \
	-I$(CVW_CONFIG) \
	-I$(ARCH_TEST_INC)

CVW_FLAGS := $(COMMON_FLAGS) \
    -I$(CVW_CONFIG) \
    -I$(ARCH_TEST_INC)

# C-version extras:
#   -std=gnu11   required for register-asm pin syntax (__asm__("a0"))
#   -ffreestanding  no hosted-environment assumptions
#   -O1 -g       mild optimisation + debug info
C_EXTRA := -ffreestanding -O1 -g -std=gnu11 \
           -fno-builtin -fno-builtin-printf -fno-builtin-puts

YAML_C_OUT   := $(BUILD_DIR)/output-c.yaml
YAML_C_NOM   := $(BUILD_DIR)/output-c-no-M.yaml

SAIL_C_ELF := $(BUILD_DIR)/FeatureExtractorC-sail.elf
CVW_C_ELF  := $(BUILD_DIR)/FeatureExtractorC-cvw.elf
NO_M_CFG   := $(BUILD_DIR)/no_M_config.json

SAIL_LD := $(BUILD_DIR)/sail_c.ld
CVW_LD  := $(BUILD_DIR)/cvw_c.ld

C_SRCS := \
    $(TEST_SRC)/FeatureExtractorC.S \
    $(TEST_SRC)/crt.S \
    $(TEST_SRC)/feature_extractor.c \
    $(TEST_SRC)/syscalls.c

.PHONY: all sail-c sail-c-no-M cvw dump-c clean help
all: sail-c

$(BUILD_DIR):
	mkdir -p $@

# ── Linker-script generation───────────────────────────────────────
# Wraps the target's link.ld and appends a 128-KB stack region.
$(SAIL_LD): | $(BUILD_DIR)
	@echo "=== Generating Sail C linker script ==="
	@printf 'INCLUDE "%s/link.ld"\nENTRY(rvtest_entry_point)\nSECTIONS {\n  .rodata : { *(.rodata .rodata.*) }\n  .sdata  : { *(.sdata .sdata.*) }\n  .bss (NOLOAD) : {\n    __bss_start = .;\n    *(.bss .bss.*)\n    *(COMMON)\n    . = ALIGN(8);\n    __bss_end = .;\n  }\n  .stack (NOLOAD) : {\n    . = ALIGN(16);\n    __stack_bottom = .;\n    . += 128K;\n    _stack_top = .;\n  }\n  PROVIDE(__global_pointer$$ = ADDR(.sdata) + 0x800);\n} INSERT AFTER .data;\n' "$(SAIL_CONFIG)" > $@

$(CVW_LD): | $(BUILD_DIR)
	@echo "=== Generating CVW C linker script ==="
	@printf 'INCLUDE "%s/link.ld"\nENTRY(rvtest_entry_point)\nSECTIONS {\n  .rodata : { *(.rodata .rodata.*) }\n  .sdata  : { *(.sdata .sdata.*) }\n  .bss (NOLOAD) : {\n    __bss_start = .;\n    *(.bss .bss.*)\n    *(COMMON)\n    . = ALIGN(8);\n    __bss_end = .;\n  }\n  .stack (NOLOAD) : {\n    . = ALIGN(16);\n    __stack_bottom = .;\n    . += 128K;\n    _stack_top = .;\n  }\n  PROVIDE(__global_pointer$$ = ADDR(.sdata) + 0x800);\n} INSERT AFTER .data;\n' "$(SAIL_CONFIG)" > $@

$(SAIL_C_ELF): $(C_SRCS) $(SAIL_LD) | $(BUILD_DIR)
	@echo "=== [C] Compiling for Sail ==="
	$(CC) $(SAIL_FLAGS) $(C_EXTRA) -T $(SAIL_LD) $(C_SRCS) -o $@

$(NO_M_CFG): | $(BUILD_DIR)
	@printf '{\n  "extensions": {\n    "M": { "supported": false }\n  }\n}\n' > $@

sail-c: $(SAIL_C_ELF)
	@echo "=== [C] Running on Sail ==="
	$(SIM) --terminal-log $(YAML_C_OUT) $(SAIL_C_ELF)
	@echo "---"
	@cat $(YAML_C_OUT)
	@echo "---"

sail-c-no-M: $(SAIL_C_ELF) $(NO_M_CFG)
	@echo "=== [C] Running Sail with M disabled ==="
	$(SIM) --terminal-log $(YAML_C_NOM) --config-override $(NO_M_CFG) $(SAIL_C_ELF)
	@echo "---"
	@cat $(YAML_C_NOM)
	@echo "---"

$(CVW_C_ELF): $(C_SRCS) $(CVW_LD) | $(BUILD_DIR)
	$(CC) $(CVW_FLAGS) $(C_EXTRA) -T $(CVW_LD) $(C_SRCS) -o $@

cvw: $(CVW_C_ELF)
	@echo "C: $(CVW_C_ELF)"

dump-c: $(SAIL_C_ELF)
	$(OBJDUMP) -d -s $(SAIL_C_ELF) > $(BUILD_DIR)/FeatureExtractorC-sail.dump

# ────────────────────────────────────────────────────────────────────────────
clean:
	rm -rf $(BUILD_DIR)

help:
	@echo "make -f tests-dev/priv/UDBFeatureExtractor/Makefile <target>"
	@echo ""
	@echo "C version: sail-c  sail-c-no-M  dump-c"
	@echo "shared:    cvw  clean"
