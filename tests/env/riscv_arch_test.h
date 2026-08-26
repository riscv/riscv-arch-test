# riscv_arch_test.h
# Top-level riscv-arch-test header file
# Jordan Carlin jcarlin@hmc.edu October 2025
# SPDX-License-Identifier: Apache-2.0

#include "rvtest_config.h"
#undef H_SUPPORTED // TODO: Remove this once Sail supports Hypervisor
#include "derived_config.h"
#include "encoding.h"
#include "utils.h"
// Kit builds never see rvmodel_macros.h (implementations come from the shim,
// values from dut_environment.h). Normal builds include it as before, and
// dut_environment.h cross-checks the two.
#ifndef RVMODEL_SHIM_EXTERN
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
#ifdef RVTEST_HYPERVISOR
  #include "rvtest_macros_hypervisor.h"
#endif
#include "rvtest_trap_handler.h"
#include "rvtest_failure_code.h"
#include "rvtest_setup.h"
