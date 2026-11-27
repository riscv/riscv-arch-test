# =====================================================================
# Sv*x4 G-stage Translation Compliance Test (Master Directory)
#
# This directory holds all shared source files for Sv39x4/Sv48x4/Sv57x4
# G-stage tests. Sv48x4/ and Sv57x4/ directories reuse these sources
# via symlinks; each directory controls the G-stage mode at compile
# time through -DSUITE_HGATP_MODE in its own Makefile.
# =====================================================================

TARGET     = sv39x4_test.elf
ENABLE_VM  = 1
ENABLE_HYP = 1
ENABLE_PMP = 1
ENABLE_TWO_STAGE = 1

# QEMU virt: explicitly request RV64 + H extension support.
QEMU_CPU   = max

# Spike: explicitly request RV64 + H extension support.

EXT_OBJS = \
    main.o \
    tests/test_helpers.o \
    tests/test_register.o

include ../../../env/c_common/Makefile.common

# G-stage mode: Sv39x4
CFLAGS += -DSUITE_HGATP_MODE=HGATP_MODE_SV39X4
