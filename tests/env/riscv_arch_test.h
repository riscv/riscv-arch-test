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
