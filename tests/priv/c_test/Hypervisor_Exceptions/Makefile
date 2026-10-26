# =====================================================================
# Hypervisor Exceptions Compliance Test
#
# Tests for the RISC-V Hypervisor (H) Extension exception and trap behavior.
# See DOCS/testplan/Hypervisor_Exceptions_test_plan.md for the full test plan.
#
# =====================================================================

TARGET     = hypervisor_exceptions_test.elf
ENABLE_VM  = 1
ENABLE_HYP = 1

# QEMU virt: explicitly request RV64 + H extension support.
QEMU_CPU   = max

# Spike: explicitly request RV64 + H extension support.

EXT_OBJS = \
    main.o \
    ../common/hyp/hyp_test_helpers_region.o \
    tests/test_register.o

include ../../../env/c_common/Makefile.common

# Suite G-stage / VS-stage paging mode: follow the platform-selected mode
# by default; override per build with `make HGATP_MODE=sv39|sv48|sv57`
# and/or `VSATP_MODE=sv39|sv48|sv57` (see common/Makefile.common).
SUITE_VSATP_MODE ?= PLATFORM_SATP_MODE
SUITE_HGATP_MODE ?= PLATFORM_HGATP_MODE
