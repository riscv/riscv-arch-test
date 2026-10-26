# =====================================================================
# Shvstvecd Extension Compliance Test
#
# Tests for the Shvstvecd extension (Direct Trap Vectoring for VS-mode,
# Version 1.0). See DOCS/testplan/shvstvecd_test_plan.md for the test plan.
#
# Spec summary:
#   - vstvec.MODE must be capable of holding 0 (Direct).
#   - When vstvec.MODE=Direct, vstvec.BASE must be capable of holding any
#     valid four-byte-aligned address.
# =====================================================================

TARGET     = shvstvecd_test.elf
ENABLE_VM  = 1
ENABLE_HYP = 1
ENABLE_TWO_STAGE = 1

# QEMU virt: explicitly request RV64 + H extension support.
QEMU_CPU   = max

# Spike: explicitly request RV64 + H extension support.

EXT_OBJS = \
    main.o \
    tests/test_register.o \
    tests/shvstvecd_strap.o

include ../../../env/c_common/Makefile.common

# Suite G-stage / VS-stage paging mode: follow the platform-selected mode
# by default; override per build with `make HGATP_MODE=sv39|sv48|sv57`
# and/or `VSATP_MODE=sv39|sv48|sv57` (see common/Makefile.common).
SUITE_VSATP_MODE ?= PLATFORM_SATP_MODE
SUITE_HGATP_MODE ?= PLATFORM_HGATP_MODE
