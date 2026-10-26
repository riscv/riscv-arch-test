# =====================================================================
# Shcounterenw Extension Compliance Test
#
# Tests for the Shcounterenw extension (Counter-Enable Writability for
# Hypervisor, Version 1.0).
# See DOCS/testplan/shcounterenw_test_plan.md for the test plan.
#
# Spec summary:
#   - For any hpmcounter that is NOT read-only zero, the corresponding
#     hcounteren bit MUST be writable.
# =====================================================================

TARGET     = shcounterenw_test.elf
ENABLE_VM  = 1
ENABLE_HYP = 1

# QEMU virt: explicitly request RV64 + H extension support.
QEMU_CPU   = max

# Spike: explicitly request RV64 + H extension support.

EXT_OBJS = \
    main.o \
    tests/test_register.o

include ../../../env/c_common/Makefile.common
