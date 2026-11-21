# =====================================================================
# Shgatpa Extension Compliance Test
#
# Tests for the Shgatpa extension (Translation Mode Support for hgatp,
# Version 1.0). See DOCS/testplan/shgatpa_test_plan.md for the plan.
#
# Spec summary:
#   (1) For every satp SvNN mode, hgatp SvNNx4 must be supported.
#   (2) hgatp Bare mode must always be supported.
# =====================================================================

TARGET     = shgatpa_test.elf
ENABLE_VM  = 1
ENABLE_HYP = 1

# QEMU virt: explicitly request RV64 + H extension support.
QEMU_CPU   = max

# Spike: explicitly request RV64 + H extension support.

EXT_OBJS = \
    main.o \
    tests/test_register.o

include ../../../env/c_common/Makefile.common
