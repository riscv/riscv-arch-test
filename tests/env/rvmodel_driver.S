// rvmodel_driver.S
// Source of the driver library that every test object links against
// SPDX-License-Identifier: BSD-3-Clause

// Assembled once per config and ABI, never per test:
//   DUT driver:       -DRVTEST_SELFCHECK, with rvmodel_macros.h on the include path.
//                     The result, librvmodel.a, is linked into the ELFs that run on the DUT.
//   reference driver: without RVTEST_SELFCHECK. sail_macros.h supplies the macros, and the
//                     result is linked into the ELFs the reference model runs to produce
//                     the expected signature.
// The test object itself is identical for both and never sees rvmodel_macros.h.

#define RVTEST_DRIVER
#define RVTEST_NOSIG

#include "riscv_arch_test.h"
#include "rvtest_driver.h"

RVTEST_DRIVER_CODE
