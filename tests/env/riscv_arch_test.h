# riscv_arch_test.h
# Top-level riscv-arch-test header file
# Jordan Carlin jcarlin@hmc.edu October 2025
# SPDX-License-Identifier: Apache-2.0

#include "rvtest_config.h"
#undef H_SUPPORTED // TODO: Remove this once Sail supports Hypervisor
#include "derived_config.h"
#include "encoding.h"
#include "utils.h"
// A certification-kit build never sees the DUT's private rvmodel_macros.h: the
// implementations live in the separately assembled rvmodel_shim.S, and the
// values come from the config's dut_environment block instead. Normal builds
// include the DUT header as before, and dut_environment.h then cross-checks the
// two against each other.
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
