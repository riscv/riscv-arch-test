/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

#ifndef TEST_VS_HELPERS_H
#define TEST_VS_HELPERS_H

/* ===================================================================
 * VS-mode test trampolines
 *
 * These helpers run *inside* VS-mode (called via run_in_vs_mode /
 * two_stage_run_in_vs). They perform a single memory operation
 * against the GPA passed as `arg` and return either:
 *   - a magic-derived value (success path), or
 *   - the trap cause they observed (fault path).
 *
 * The fault helpers rely on trap_expect_begin()/end() being armed
 * by the M-mode caller before run_in_vs_mode() is invoked. The
 * trap handler will record the cause; on the way back to M-mode the
 * helper returns trap_get_cause().
 *
 * NOTE: All helpers terminate with the implicit `ecall` issued by
 *       the run_in_vs_mode trampoline (caller side).
 * =================================================================== */

#include "types.h"

/* Write HYP_TEST_MAGIC to *(uint64_t *)arg, read it back; returns 0
 * on read-back match, non-zero on mismatch. */
uintptr_t test_vs_read_write(uintptr_t arg);

/* Single load from arg; returns the loaded value (or 0 if the trap
 * handler skipped the instruction). */
uintptr_t test_vs_load(uintptr_t arg);

/* Single store to arg; returns 0 (or non-zero if trapped). */
uintptr_t test_vs_store(uintptr_t arg);

/* Load expecting a fault; returns the captured fault cause (or 0
 * if no fault was observed). */
uintptr_t test_vs_load_expect_fault(uintptr_t arg);

/* Store expecting a fault; returns the captured fault cause. */
uintptr_t test_vs_store_expect_fault(uintptr_t arg);

/* Jump-and-execute at arg expecting a fault; returns the captured
 * fault cause. */
uintptr_t test_vs_exec_expect_fault(uintptr_t arg);

#endif /* TEST_VS_HELPERS_H */
