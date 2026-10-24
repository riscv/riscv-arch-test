# =====================================================================
# Sha (Augmented Hypervisor) Extension Compliance Test
#
# Tests for the Sha composite extension. See
# DOCS/testplan/sha_test_plan.md for the plan.
#
# Sha = H + Ssstateen + Shcounterenw + Shvstvala + Shtvala +
#        Shvstvecd + Shvsatpa + Shgatpa
# =====================================================================

TARGET     = sha_test.elf
ENABLE_VM  = 1
ENABLE_HYP = 1

# QEMU virt: RV64 + H extension + all translation modes.
QEMU_CPU   = max

# Spike: explicitly request RV64 + H extension support.
# smcsrind_sscsrind needed for SHA-HCTL-05 (hstateen0 CSRIND gate test).

EXT_OBJS = \
    main.o \
    tests/sha_strap.o \
    tests/test_register.o

include ../../../env/c_common/Makefile.common

# Suite G-stage / VS-stage paging mode: follow the platform-selected mode
# by default; override per build with `make HGATP_MODE=sv39|sv48|sv57`
# and/or `VSATP_MODE=sv39|sv48|sv57` (see common/Makefile.common).
SUITE_VSATP_MODE ?= PLATFORM_SATP_MODE
SUITE_HGATP_MODE ?= PLATFORM_HGATP_MODE
