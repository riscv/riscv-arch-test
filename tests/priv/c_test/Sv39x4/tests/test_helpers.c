/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/* ===================================================================
 * test_helpers.c - Shared helpers for Sv*x4 G-stage tests
 *
 * Thin wrappers around common/hyp/two_stage_helpers.h APIs,
 * specializing for G-stage-only tests (VS-stage = Bare).
 *
 * See test_helpers.h for prototypes / contracts.
 * =================================================================== */

#include "test_helpers.h"
#include "hyp/two_stage_helpers.h"

void _setup_with_victim(two_stage_ctx_t *ctx,
                        uintptr_t victim_gpa,
                        uintptr_t victim_flags)
{
    ts2_setup_with_g_victim(ctx, SATP_MODE_BARE, SUITE_HGATP_MODE,
                            victim_gpa, victim_flags);
}

bool _vsfault_check(uintptr_t (*helper)(uintptr_t),
                    uintptr_t target,
                    uintptr_t victim_flags,
                    uintptr_t expected_cause)
{
    two_stage_ctx_t ctx;
    _setup_with_victim(&ctx, target, victim_flags);
    return ts2_run_check_fault(&ctx, helper, target, expected_cause);
}
