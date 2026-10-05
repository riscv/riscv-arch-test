# riscv_arch_test.h
# Top-level riscv-arch-test header file
# Jordan Carlin jcarlin@hmc.edu October 2025
# SPDX-License-Identifier: Apache-2.0

#include "rvtest_config.h"
#include "derived_config.h"
#include "encoding.h"
#ifdef RVTEST_EXPERIMENTAL
  #include "rvtest_experimental.h"
#endif
#include "utils.h"
// Kit builds never see rvmodel_macros.h (implementations come from the shim,
// values from dut_environment.h). Normal builds include it as before, and
// dut_environment.h cross-checks the two.
// A driver-based (kit) config ships no rvmodel_macros.h at all: implementations
// come from the shim, values from dut_environment.h, and the reference build gets
// its model behaviour from sail_macros.h below.
#if !defined(RVMODEL_SHIM_EXTERN) && __has_include("rvmodel_macros.h")
  #include "rvmodel_macros.h"
#endif
#include "dut_environment.h"
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
#ifdef H_SUPPORTED
  #include "rvtest_macros_hypervisor.h"
#endif
#include "rvtest_trap_handler.h"
#include "rvtest_invisible_trap_handler.h"
#include "rvtest_failure_code.h"
#include "rvtest_setup.h"
