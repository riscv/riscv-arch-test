# =====================================================================
# Shtvala Extension Compliance Test
#
# Tests for the Shtvala extension (Trap Value Reporting for Hypervisor,
# Version 1.0). See DOCS/testplan/shtvala_test_plan.md for the test plan.
#
# Spec summary:
#   On a guest-page-fault, htval MUST be written with the faulting
#   guest physical address (right-shifted by 2). The H-extension
#   baseline allows implementations to write 0; Shtvala forbids that
#   relaxation.
# =====================================================================

TARGET     = shtvala_test.elf
ENABLE_VM  = 1
ENABLE_HYP = 1
ENABLE_TWO_STAGE = 1

# QEMU virt: explicitly request RV64 + H extension support.
QEMU_CPU   = max

# Spike: explicitly request RV64 + H extension support.


EXT_OBJS = \
    main.o \
    tests/test_helpers.o \
    tests/test_register.o \
    $(COMMON_DIR)/hyp/hyp_test_helpers_region.o

include ../../../env/c_common/Makefile.common

# Suite G-stage / VS-stage paging mode: follow the platform-selected mode
# by default; override per build with `make HGATP_MODE=sv39|sv48|sv57`
# and/or `VSATP_MODE=sv39|sv48|sv57` (see common/Makefile.common).
SUITE_VSATP_MODE ?= PLATFORM_SATP_MODE
SUITE_HGATP_MODE ?= PLATFORM_HGATP_MODE
