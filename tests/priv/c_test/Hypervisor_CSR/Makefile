# =====================================================================
# Hypervisor CSR Compliance Test
#
# Tests for the RISC-V Hypervisor (H) Extension CSR behavior.
# See DOCS/testplan/Hypervisor_CSR_test_plan.md for the full test plan.
#
# =====================================================================

TARGET     = hypervisor_csr_test.elf
ENABLE_VM  = 1
ENABLE_HYP = 1

# QEMU virt: explicitly request RV64 + H extension support.
QEMU_CPU   = max

# Spike: explicitly request RV64 + H extension support.
# The runtime ISA string MUST carry every extension that config/spike-rv64-max
# declares and the tests exercise, otherwise a capability-gated test still runs
# (F_AVAILABLE/V_AVAILABLE are compile-time from the config) but the underlying
# CSR/instruction is unimplemented on Spike:
#   - f/d/v: the vsstatus FS/VS Dirty tests (VSST-06/09) execute real FP/vector
#     instructions (emitted as raw .4byte); without f/d/v they trap illegal.
#   - zicfilp/zicfiss: they define the "software check" exception (cause 18), so
#     hedeleg[18] must be writable (DELEG-01); without them Spike hardwires it 0.

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
