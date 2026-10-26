# =====================================================================
# Shvsatpa Extension Compliance Test
#
# Tests for the Shvsatpa extension (Translation Mode Support for vsatp,
# Version 1.0). See DOCS/testplan/shvsatpa_test_plan.md for the plan.
#
# Spec summary:
#   All satp-supported translation modes must also be supported by
#   vsatp. i.e. satp.MODE legal values == vsatp.MODE legal values.
# =====================================================================

TARGET     = shvsatpa_test.elf
ENABLE_VM  = 1
ENABLE_HYP = 1

# QEMU virt: explicitly request RV64 + H extension support.
QEMU_CPU   = max

# Spike: explicitly request RV64 + H extension support.

EXT_OBJS = \
    main.o \
    tests/test_register.o

include ../../../env/c_common/Makefile.common
