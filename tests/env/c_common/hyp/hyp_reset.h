/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

#ifndef HYP_RESET_H
#define HYP_RESET_H

#include <stdbool.h>

/* ===================================================================
 * Hypervisor state reset for tests
 *
 * hyp_reset_state() returns ALL hypervisor state to a known clean
 * baseline (hgatp=Bare, hedeleg=0, hideleg=0, hvip=0, hie=0,
 * hstatus=0, menvcfg.ADUE=0 (force Svade G-stage A/D semantics),
 * henvcfg=0, hcounteren=0, htimedelta=0, all VS CSRs=0,
 * HFENCE.GVMA all) and then forwards to the base reset_state().
 *
 * Tests use HYP_TEST_END (defined in hyp_test.h) which calls this
 * helper instead of reset_state(), so each hypervisor-aware test
 * starts from a fully clean H-extension state.
 * =================================================================== */

void hyp_reset_state(void);

/**
 * hyp_misa_h - does this platform implement the H extension?
 *
 * Reads misa, which is M-level, so it raises to M first if needed.  H-aware
 * suites are built for platforms that MAY have H, not that must (norm:misa_h_op
 * allows misa.H to read zero), and every H CSR write in hyp_reset_state()
 * raises an illegal instruction when it does not.
 */
bool hyp_misa_h(void);

/**
 * hyp_reset_state_if_h - hyp_reset_state() where possible, reset_state() where not
 *
 * The form the test-exit path needs (see TEST_EXIT_RESET in hyp_test.h).  A
 * plain hyp_reset_state() cannot be used there because the exit path most in
 * need of it is TEST_SKIP, and the commonest reason to skip is that H is
 * absent - exactly when touching hypervisor CSRs would trap.  Either way the
 * base reset still runs, so the exit contract is the same as reset_state().
 */
void hyp_reset_state_if_h(void);

#endif /* HYP_RESET_H */
