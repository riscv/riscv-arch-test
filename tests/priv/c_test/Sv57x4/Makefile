# =====================================================================
# Sv57x4 G-stage Translation Compliance Test
#
# 通过 symlink 共享 Sv39x4/tests/ 下所有源文件，
# 仅 Makefile -D 宏与 main.c banner 不同。
# =====================================================================

TARGET     = sv57x4_test.elf
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

# G-stage mode: Sv57x4
CFLAGS += -DSUITE_HGATP_MODE=HGATP_MODE_SV57X4
