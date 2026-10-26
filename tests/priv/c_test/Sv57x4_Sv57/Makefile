# =====================================================================
# Sv57 + Sv57x4 Two-Stage Translation Compliance Test
#
# 通过 symlink 共享 Sv39_Sv39x4/tests/ 下所有源文件，
# 仅 Makefile -D 宏与 main.c banner 不同。
# =====================================================================

TARGET     = sv57x4_sv57_test.elf
ENABLE_VM  = 1
ENABLE_HYP = 1
ENABLE_PMP = 1
ENABLE_TWO_STAGE = 1

QEMU_CPU   = max

EXT_OBJS = \
    main.o \
    tests/test_register.o

include ../../../env/c_common/Makefile.common

# Suite mode: Sv57 (VS) + Sv57x4 (G-stage)
CFLAGS += -DSUITE_VSATP_MODE=SATP_MODE_SV57
CFLAGS += -DSUITE_HGATP_MODE=HGATP_MODE_SV57X4
