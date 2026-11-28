# riscv_arch_test.h
# Top-level riscv-arch-test header file
# Jordan Carlin jcarlin@hmc.edu October 2025
# SPDX-License-Identifier: Apache-2.0

#include "rvtest_config.h"
#include "derived_config.h"
#include "encoding.h"
#include "tsbi.h"
#ifdef ENABLE_EXPERIMENTAL_EXTENSIONS
  #include "rvtest_experimental.h"
#endif
#include "utils.h"
// Signature builds and coverage builds run on Sail, so they replace DUT-specific macros with Sail macros.
#if !defined(RVTEST_SELFCHECK) && !defined(RVTEST_SAIL_MACROS)
  #define RVTEST_SAIL_MACROS
#endif
#include "rvmodel_macros.h"
// The DUT build sends illegal instructions from S- and U-mode to M-mode first for invisible emulation
// (see RVTEST_SAVE_MEDELEG_ILLEGAL), then forwards them to S in software. sail_macros.h turns emulation
// off for the signature build, so record this before it does: a test whose result depends on the
// hardware route must skip the same cases in both builds.
#if (defined(RVMODEL_INVISIBLE_TRAP_HANDLER) || defined(RVTEST_EMULATE_TIME_CSR)) && defined(S_SUPPORTED)
  #define RVTEST_ILLEGAL_THROUGH_M
#endif
#ifdef RVTEST_SAIL_MACROS
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
#include "rvtest_trap_handler.h"
#include "rvtest_invisible_trap_handler.h"
#include "rvtest_failure_code.h"
#include "rvtest_setup.h"
