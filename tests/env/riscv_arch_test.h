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
// Signature builds and coverage builds run on Sail, so they take Sail's macros.
#if !defined(RVTEST_SELFCHECK) && !defined(RVTEST_SAIL_MACROS)
  #define RVTEST_SAIL_MACROS
#endif
// Only the DUT driver (rvmodel_driver.S with RVTEST_SELFCHECK) sees the DUT's
// rvmodel_macros.h. Test objects call into the driver instead, and take device
// addresses and timings from dut_environment.h, which act generates from the
// config. Sail builds (RVTEST_SAIL_MACROS) get the reference model's values and
// macros from sail_macros.h.
#if defined(RVTEST_DRIVER) && !defined(RVTEST_SAIL_MACROS)
  #include "rvmodel_macros.h"
#endif
#include "dut_environment.h"
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
#ifdef RVTEST_CONFIG_CHECKS
  #include "rvtest_config_check.h"
#endif
#include "rvtest_setup.h"
