// SPDX-License-Identifier: Apache-2.0
// Copyright (c) 2026 RISC-V International
//
// Minimal stub rvtest_config.h for UDBFeatureExtractor.
// The feature extractor runs before the real UDB config is generated.
// Only the defines required by the ACT env headers are provided here.

#ifndef RVTEST_CONFIG_H
#define RVTEST_CONFIG_H

// Minimum defines needed by rvtest_trap_handler.h, rvtest_setup.h,
// rvtest_failure_code.h. Match XLEN passed on compiler command line.
#ifndef UDB_MXLEN
#define UDB_MXLEN XLEN
#endif

// Trap on unimplemented instructions (needed by rvtest_trap_handler.h)
#define UDB_TRAP_ON_UNIMPLEMENTED_INSTRUCTION

#endif /* RVTEST_CONFIG_H */
