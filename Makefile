# SPDX-License-Identifier: BSD-3-Clause

XLEN ?= 32
DEBUG ?= 0

RISCV_PREFIX ?= riscv$(XLEN)-unknown-elf-
RISCV_GCC ?= $(RISCV_PREFIX)gcc
RISCV_OBJDUMP ?= $(RISCV_PREFIX)objdump
RISCV_OBJCOPY ?= $(RISCV_PREFIX)objcopy

MODEL_DIR ?= riscof-plugins/rv32/spike_simple/env
INCDIRS = -I. -I./riscv-test-suite/env -I$(MODEL_DIR)

CPPFLAGS += $(INCDIRS)
CPPFLAGS += -DXLEN=$(XLEN) -DFLEN=$(XLEN)
CPPFLAGS += -DRVTEST_ENAB_INSTRET_CNT

ifeq ($(DEBUG),1)
CPPFLAGS += -DRVTEST_DEBUG
endif

ifeq ($(XLEN),64)
    ASFLAGS += -march=rv64gc -mabi=lp64
else
    ASFLAGS += -march=rv32gc -mabi=ilp32
endif
LDFLAGS += -static -nostdlib -nostartfiles

TEST_SRCS = $(shell find riscv-test-suite -name "*.S")
TEST_ELFS = $(TEST_SRCS:.S=.elf)

all: $(TEST_ELFS)

%.elf: %.S
	$(RISCV_GCC) $(CPPFLAGS) $(ASFLAGS) $(LDFLAGS) -T $(MODEL_DIR)/link.ld $< -o $@

clean:
	rm -f $(TEST_ELFS)

.PHONY: all clean
