/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

#ifndef HYP_TEST_H
#define HYP_TEST_H

/* ===================================================================
 * Hypervisor-aware test macros
 *
 * Layered on top of common/test_framework.h:
 *   - TEST_EXIT_RESET override:   every test exit also clears H state.
 *   - HYP_TEST_END:               TEST_END counterpart, uses hyp_reset_state.
 *   - EXPECT_GUEST_PAGE_FAULT:    arm trap, run stmt, assert cause matches.
 *   - CHECK_HTVAL/HTINST/GVA:     post-trap inspectors.
 * =================================================================== */

#include "test_framework.h"
#include "hyp_reset.h"
#include "hyp_csr.h"
#include "hyp_defs.h"
#include "hyp_vs_trap.h"

/* Every exit from a test in this translation unit clears hypervisor state.
 *
 * HYP_TEST_END covered the case of a test that runs to completion, but
 * TEST_SKIP and TEST_FATAL return through the base TEST_EXIT_RESET and used to
 * leave the next test whatever hgatp/hstatus/vs* the abandoned one had already
 * installed.  Overriding the seam fixes all three at once and needs no change
 * in any suite: a skipped test now hands on the same clean baseline as a
 * passing one.
 *
 * Guarded rather than direct (see hyp_reset_state_if_h) because the most
 * frequent skip reason is that H is absent, which is precisely when writing
 * hypervisor CSRs would raise an illegal instruction.
 *
 * Only translation units that include this header are affected, and it is
 * itself only reachable under ENABLE_HYP - the same condition that puts
 * hyp_reset.o into the link. */
#undef TEST_EXIT_RESET
#define TEST_EXIT_RESET() hyp_reset_state_if_h()

/* HYP_TEST_END: like TEST_END but resets hypervisor state.
 * Uses the shared _test_end_record() from test_framework.h for
 * pass/fail bookkeeping (avoids duplicating statistics logic).
 *
 * Now equivalent to TEST_END given the override above; kept because it states
 * the intent at the call site, and because it resets unconditionally - a test
 * that got far enough to reach its own end has already proved H is there. */
#define HYP_TEST_END() do { \
    goto_priv(PRIV_M); \
    hyp_reset_state(); \
    return _test_end_record(); \
} while (0)

/* Execute stmt expecting a guest-page-fault with the given cause. */
#define EXPECT_GUEST_PAGE_FAULT(expected_cause, stmt) do { \
    trap_expect_begin(); \
    stmt; \
    TEST_ASSERT("guest-page-fault triggered", trap_was_triggered()); \
    if (trap_was_triggered()) { \
        TEST_ASSERT_EQ("guest-page-fault cause", trap_get_cause(), \
                       (uintptr_t)(expected_cause)); \
    } \
    trap_expect_end(); \
} while (0)

/* Check htval == expected (faulting GPA >> 2). */
#define CHECK_HTVAL(msg, expected_gpa_shifted) do { \
    TEST_ASSERT_EQ(msg, trap_get_htval(), (uintptr_t)(expected_gpa_shifted)); \
} while (0)

/* Tightened trap-report check for guest-page faults raised by implicit
 * memory accesses during VS-stage page-table walks.
 *
 * Spec semantics:
 *  - norm:htval_trapval: htval may be written with zero OR the
 *    faulting GPA >> 2. Both are compliant, so htval == 0 is accepted
 *    and no htinst requirement applies in that case.
 *  - norm:H_trap_xtinst_guestpage: once htval is nonzero (condition
 *    (b) met; condition (a) holds by construction in these tests),
 *    htinst MUST be the special pseudoinstruction - zero is NOT
 *    allowed.
 *
 * Do NOT accept htinst == 0 when htval != 0: that combination
 * violates the spec and must be reported, not worked around. */
#define CHECK_IMPLICIT_FAULT_REPORT(expected_gpa_shifted, expected_pseudo) do { \
    uintptr_t _hv = trap_get_htval(); \
    if (_hv != 0) { \
        TEST_ASSERT_EQ("htval == implicit-access GPA >> 2", \
                       _hv, (uintptr_t)(expected_gpa_shifted)); \
        TEST_ASSERT_EQ("htinst == pseudoinst (zero NOT allowed when htval != 0)", \
                       trap_get_htinst(), (uintptr_t)(expected_pseudo)); \
    } \
} while (0)

/* Check hstatus.GVA captured at trap. */
#define CHECK_GVA(msg, expected_gva) do { \
    TEST_ASSERT_EQ(msg, (uintptr_t)trap_get_gva(), (uintptr_t)((expected_gva) ? 1 : 0)); \
} while (0)

/* ===================================================================
 * Platform capability gates
 * =================================================================== */

/**
 * PAGING_MODE_UNAVAILABLE_ - Compile-time helper shared by the paging-mode
 * gates below. `mode` is an architectural satp/vsatp/hgatp MODE encoding:
 * Bare=0, Sv39=8, Sv48=9, Sv57=10 (the G-stage Sv*x4 modes share the same
 * encodings). Support is taken from the platform config declaration
 * normalized in capabilities.h (SV39/48/57_AVAILABLE), NOT from a runtime
 * WARL probe -- see capabilities.h design note #5 (config-declaration
 * driven; runtime probes are fragile and have produced false negatives).
 * The SV*_AVAILABLE flags are compile-time 0/1, so this also evaluates
 * correctly when `mode` is a runtime value (e.g. a per-mode loop variable).
 */
#define PAGING_MODE_UNAVAILABLE_(mode) ( \
    ((mode) == 0)                     || \
    ((mode) == 8  && !SV39_AVAILABLE) || \
    ((mode) == 9  && !SV48_AVAILABLE) || \
    ((mode) == 10 && !SV57_AVAILABLE))

/**
 * REQUIRE_HGATP_MODE - Skip test if the platform config does not declare
 * the given G-stage paging mode.
 *
 * Compile-time gate on SV39/48/57_AVAILABLE via PAGING_MODE_UNAVAILABLE_.
 * Tests whose SUBJECT is the runtime WARL behaviour of a specific MODE
 * (e.g. Shgatpa/Shvsatpa, Shtvala/test_htval_modes.c) call
 * hgatp_supports_mode() directly instead of relying on this gate.
 */
#define REQUIRE_HGATP_MODE(mode) do { \
    if (PAGING_MODE_UNAVAILABLE_(mode)) { \
        TEST_SKIP("hgatp mode not declared by platform config"); \
    } \
} while (0)

/* ===================================================================
 * Virtual-instruction exception macros
 * =================================================================== */

/**
 * EXPECT_VIRTUAL_INST - Execute stmt, expect virtual-instruction exception
 *
 * Used to verify that VTSR/VTW/VTVM traps or VS/VU-mode access to
 * hypervisor CSRs triggers cause=22.
 */
#define EXPECT_VIRTUAL_INST(stmt) do { \
    trap_expect_begin(); \
    stmt; \
    TEST_ASSERT("virtual-inst trap triggered", trap_was_triggered()); \
    if (trap_was_triggered()) { \
        TEST_ASSERT_EQ("cause=22 (virtual-instruction)", \
                       trap_get_cause(), (uintptr_t)CAUSE_VIRTUAL_INSTRUCTION); \
    } \
    trap_expect_end(); \
} while (0)

/**
 * VS_EXPECT_NO_TRAP - Execute stmt in VS-mode context, expect no trap
 *
 * Verifies that an operation completes without triggering any exception.
 * On failure, reports the unexpected trap cause to aid root-cause
 * analysis (e.g. distinguishing illegal vs virtual-instruction).
 */
#define VS_EXPECT_NO_TRAP(stmt) do { \
    trap_expect_begin(); \
    stmt; \
    if (trap_was_triggered()) { \
        printf("  UNEXPECTED TRAP: cause=%lu, epc=0x%lx, tval=0x%lx\n", \
               (unsigned long)trap_get_cause(), \
               (unsigned long)trap_get_epc(), \
               (unsigned long)trap_get_tval()); \
    } \
    TEST_ASSERT("no trap in VS-mode", !trap_was_triggered()); \
    trap_expect_end(); \
} while (0)

/* ===================================================================
 * vstval verification macros (shvstvala)
 * =================================================================== */

/**
 * CHECK_VSTVAL - Verify vstval matches expected value after VS trap.
 *
 * Used after a trap is delegated to VS-mode and the VS handler
 * records vstval. Reads vstval from HS/M-mode (CSR 0x243).
 */
#define CHECK_VSTVAL(msg, expected) do { \
    TEST_ASSERT_EQ(msg, vstval_read(), (uintptr_t)(expected)); \
} while (0)

/**
 * CHECK_VSTVAL_NONZERO - Assert vstval is non-zero (shvstvala core).
 */
#define CHECK_VSTVAL_NONZERO(msg) do { \
    TEST_ASSERT(msg, vstval_read() != 0); \
} while (0)

/**
 * CHECK_VSTVAL_ZERO - Assert vstval is zero.
 */
#define CHECK_VSTVAL_ZERO(msg) do { \
    TEST_ASSERT_EQ(msg, vstval_read(), (uintptr_t)0); \
} while (0)

/* ===================================================================
 * satp / vsatp mode capability gates (shvsatpa, shgatpa)
 * =================================================================== */

#define REQUIRE_SATP_MODE(mode) do { \
    if (PAGING_MODE_UNAVAILABLE_(mode)) { \
        TEST_SKIP("satp mode not declared by platform config"); \
    } \
} while (0)

#define REQUIRE_VSATP_MODE(mode) do { \
    if (PAGING_MODE_UNAVAILABLE_(mode)) { \
        TEST_SKIP("vsatp mode not declared by platform config"); \
    } \
} while (0)

/* ===================================================================
 * Illegal / Virtual-instruction unified trap check
 * =================================================================== */

/**
 * EXPECT_ILLEGAL_INST - Execute stmt, expect illegal-instruction (cause=2)
 */
#define EXPECT_ILLEGAL_INST(stmt) do { \
    trap_expect_begin(); \
    stmt; \
    TEST_ASSERT("illegal-inst trap triggered", trap_was_triggered()); \
    if (trap_was_triggered()) { \
        TEST_ASSERT_EQ("cause=2 (illegal-instruction)", \
                       trap_get_cause(), (uintptr_t)2); \
    } \
    trap_expect_end(); \
} while (0)

/**
 * EXPECT_ILLEGAL_OR_VIRTUAL_INST - Execute stmt, expect either
 * illegal-instruction (cause=2) or virtual-instruction (cause=22).
 *
 * Used for tests where the exact trap depends on privilege context:
 * non-virtualized gets cause=2, virtualized gets cause=22.
 */
#define EXPECT_ILLEGAL_OR_VIRTUAL_INST(stmt) do { \
    trap_expect_begin(); \
    stmt; \
    TEST_ASSERT("illegal/virtual-inst triggered", trap_was_triggered()); \
    if (trap_was_triggered()) { \
        uintptr_t _c = trap_get_cause(); \
        TEST_ASSERT("cause=2 or cause=22", \
                    _c == 2 || _c == CAUSE_VIRTUAL_INSTRUCTION); \
    } \
    trap_expect_end(); \
} while (0)

/* ===================================================================
 * Counter access exception macros (shcounterenw)
 * =================================================================== */

/**
 * EXPECT_COUNTER_TRAP - Execute counter access, expect trap.
 *
 * When hcounteren/scounteren bit is 0, VS/VU access to the counter
 * should trap (virtual-instruction from VS, illegal-inst from VU
 * if delegated).
 */
#define EXPECT_COUNTER_TRAP(stmt) do { \
    trap_expect_begin(); \
    stmt; \
    TEST_ASSERT("counter access trapped", trap_was_triggered()); \
    trap_expect_end(); \
} while (0)

/* ===================================================================
 * VS trap record assertion macros (shvstvecd / shvstvala)
 * =================================================================== */

/**
 * CHECK_VS_TRAP_CAUSE - Verify VS trap record cause.
 */
#define CHECK_VS_TRAP_CAUSE(msg, expected_cause) do { \
    vs_trap_record_t *_r = vs_trap_get_last(); \
    TEST_ASSERT_EQ(msg, _r->vs_cause, (uintptr_t)(expected_cause)); \
} while (0)

/**
 * CHECK_VS_TRAP_TVAL - Verify VS trap record tval (vstval at entry).
 */
#define CHECK_VS_TRAP_TVAL(msg, expected_tval) do { \
    vs_trap_record_t *_r = vs_trap_get_last(); \
    TEST_ASSERT_EQ(msg, _r->vs_tval, (uintptr_t)(expected_tval)); \
} while (0)

/**
 * CHECK_VS_TRAP_VECTORED_ENTRY - Verify vectored entry index.
 */
#define CHECK_VS_TRAP_VECTORED_ENTRY(msg, expected_idx) do { \
    vs_trap_record_t *_r = vs_trap_get_last(); \
    TEST_ASSERT_EQ(msg, _r->entry_idx, (int)(expected_idx)); \
} while (0)

#endif /* HYP_TEST_H */
