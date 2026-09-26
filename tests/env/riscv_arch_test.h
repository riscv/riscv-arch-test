# riscv_arch_test.h
# Top-level riscv-arch-test header file
# Jordan Carlin jcarlin@hmc.edu October 2025
# SPDX-License-Identifier: Apache-2.0

#include "rvtest_config.h"
#undef H_SUPPORTED // TODO: Remove this once Sail supports Hypervisor
#include "derived_config.h"
#include "encoding.h"
#ifdef RVTEST_EXPERIMENTAL
  #include "rvtest_experimental.h"
#endif
#include "utils.h"
#include "rvmodel_macros.h"

// UDB_{MEI,MTI,MSI}_INTR_IMPL record whether the platform can raise each machine interrupt.
// They must be derived HERE, from the DUT's own macros and before sail_macros.h runs, because
// that header defines RVMODEL_SET_MEXT_INT for the signature build whether or not the DUT does --
// deriving them afterwards would put a different set of testcases in the reference ELF than in
// the DUT ELF.
// TODO: take these from riscv-unified-db once it carries the parameters (riscv-unified-db#1963).
#ifdef RVMODEL_SET_MEXT_INT
  #define UDB_MEI_INTR_IMPL
#endif
#ifdef RVMODEL_MTIMECMP_ADDRESS
  #define UDB_MTI_INTR_IMPL
#endif
#if defined(RVMODEL_MSIP_ADDRESS) || defined(RVMODEL_SET_MSW_INT)
  #define UDB_MSI_INTR_IMPL
#endif

// The supervisor-level ones need no platform support: rvtest_set_{sext,ssw}_int_* fall back to
// mip.SEIP / mip.SSIP when the platform defines no controller macro, and rvtest_set_stime_int_*
// always uses mip.STIP. All three are writable, so S-mode interrupts are raisable wherever
// S-mode exists.
#ifdef S_SUPPORTED
  #define UDB_SEI_INTR_IMPL
  #define UDB_STI_INTR_IMPL
  #define UDB_SSI_INTR_IMPL
#endif

#ifndef RVTEST_SELFCHECK
  #include "sail_macros.h"
#endif
#include "check_defines.h"
#include "signature.h"
#include "rvtest_macros.h"
#if UDB_NUM_PMP_ENTRIES > 0
  #include "rvtest_pmp_macros.h"
#endif
#ifdef RVTEST_VECTOR
  #include "rvtest_macros_vector.h"
#endif
#ifdef RVTEST_HYPERVISOR
  #include "rvtest_macros_hypervisor.h"
#endif
#include "rvtest_trap_handler.h"
#include "rvtest_invisible_trap_handler.h"
#include "rvtest_failure_code.h"
#include "rvtest_setup.h"
