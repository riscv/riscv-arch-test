# =====================================================================
# Sv39 + Sv39x4 Two-Stage Translation Compliance Test (主目录)
#
# 主目录持有全部 24 个 two-stage test .c 源文件。其余 8 个借用目录通过
# symlink 复用本目录 tests/ 下所有文件，各目录仅通过 Makefile 的
# -DSUITE_VSATP_MODE / -DSUITE_HGATP_MODE 控制编译期模式选择。
# =====================================================================

TARGET     = sv39x4_sv39_test.elf
ENABLE_VM  = 1
ENABLE_HYP = 1
ENABLE_PMP = 1
ENABLE_TWO_STAGE = 1

QEMU_CPU   = max

EXT_OBJS = \
    main.o \
    tests/test_register.o

include ../../../env/c_common/Makefile.common

# Suite mode: Sv39 (VS) + Sv39x4 (G-stage)
CFLAGS += -DSUITE_VSATP_MODE=SATP_MODE_SV39
CFLAGS += -DSUITE_HGATP_MODE=HGATP_MODE_SV39X4
