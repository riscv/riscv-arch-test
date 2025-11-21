///////////////////////////////////////////
// @TEST_PATH@
// Copyright (C) 2025 Harvey Mudd College & Oklahoma State University, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
///////////////////////////////////////////

##### START_TEST_CONFIG #####
# implemented_extensions: @EXTENSION_LIST@
# params:
#   MXLEN: @XLEN@
# MARCH: @MARCH@
# CONFIG_DEPENDENT: @CONFIG_DEPENDENT@
##### END_TEST_CONFIG #####

#define SIGUPD_COUNT @SIGUPD_COUNT_FROM_TESTGEN@
#include "riscv_arch_test.h"

// Set up test environment and declare main entry point
RVTEST_BEGIN
