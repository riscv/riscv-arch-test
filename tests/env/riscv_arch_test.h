# riscv_arch_test.h
# Top-level riscv-arch-test header file
# Jordan Carlin jcarlin@hmc.edu October 2025
# SPDX-License-Identifier: Apache-2.0

#include "rvtest_config.h"
#include "encoding.h"
#ifdef SELFCHECK
  #include "model_test.h"
#else
  #include "sail_test.h"
#endif
#include "signature.h"
#include "arch_test.h" // TODO: clean up and split arch_test.h
#include "test_setup.h"

.macro RVTEST_END_INCLUDES
  #include "failure_code.h"
.endm
