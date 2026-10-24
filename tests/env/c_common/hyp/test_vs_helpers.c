/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/* ===================================================================
 * common/hyp/test_vs_helpers.c — VS-mode test trampolines
 *
 * These run inside VS-mode (V=1, nominal S). They MUST NOT call
 * printf or any other M-mode-only helper. The M-mode caller is
 * responsible for arming traps via trap_expect_begin() before
 * invoking run_in_vs_mode/two_stage_run_in_vs.
 * =================================================================== */

#include "test_vs_helpers.h"
#include "hyp_defs.h"
#include "test_framework.h"
#include "mem_ops.h"

/* ===================================================================
 * Successful-access helpers
 * =================================================================== */

uintptr_t test_vs_read_write(uintptr_t arg) {
    volatile uint64_t *p = (volatile uint64_t *)arg;
    *p = HYP_TEST_MAGIC;
    uint64_t v = *p;
    return (v == HYP_TEST_MAGIC) ? 0 : 1;
}

uintptr_t test_vs_load(uintptr_t arg) {
    volatile uint64_t *p = (volatile uint64_t *)arg;
    return (uintptr_t)(*p);
}

uintptr_t test_vs_store(uintptr_t arg) {
    volatile uint64_t *p = (volatile uint64_t *)arg;
    *p = HYP_TEST_MAGIC;
    return 0;
}

/* ===================================================================
 * Fault-expecting helpers
 *
 * The M-mode caller must call trap_expect_begin() before entering
 * VS-mode, and must arrange for the trap to reach M at all: under the
 * delegation baseline ordinary stimulus raised at V=1 is delegated down
 * to the VS handler, so a caller that wants the M-mode record has to
 * clear the corresponding hedeleg bit for the duration of the case.
 * With that done the trap is recorded by common/trap.c, and the helper
 * reads back the captured cause via trap_get_cause() and returns it.
 *
 * To make the trap deterministic we issue the access then immediately
 * read trap_get_cause(); if no fault occurred, the cause is 0.
 * =================================================================== */

uintptr_t test_vs_load_expect_fault(uintptr_t arg) {
    volatile uint64_t *p = (volatile uint64_t *)arg;
    /* Discard the loaded value; on fault the trap handler will skip
     * past this instruction so we resume here normally. */
    (void)*p;
    /* trap_get_cause() is in M-mode-only memory? No — it lives in
     * a global which is identity-mapped at G-stage, so VS-mode
     * (with U=1 mappings) can read it. */
    return trap_get_cause();
}

uintptr_t test_vs_store_expect_fault(uintptr_t arg) {
    volatile uint64_t *p = (volatile uint64_t *)arg;
    *p = HYP_TEST_MAGIC;
    return trap_get_cause();
}

/* Recovery anchor used by m_trap_handler when a fetch fault occurs.
 * Defined as a weak symbol in common/trap.c. We're in VS-mode here,
 * but the variable lives in identity-mapped memory (G-stage maps the
 * kernel image) so a plain LA + STORE reaches it. */
extern uintptr_t _exec_return_addr;

uintptr_t test_vs_exec_expect_fault(uintptr_t arg) {
    /* Jump to arg expecting a guest-page-fault / inst-access-fault
     * on fetch. The naive `fn()` form has no recovery anchor: the
     * trap handler's fallback `mepc = epc + 2/4` lands inside the
     * same V=0 (or X=0) page and immediately re-faults, but armed
     * has already been cleared -> UNEXPECTED TRAP.
     *
     * Mirroring mem_ops.h::exec_at, we install the address of label
     * 1f into _exec_return_addr before jumping. m_trap_handler's
     * armed branch sees `_exec_return_addr != 0` and redirects mepc
     * straight here, escaping the fault page in one shot. We also
     * preload ra with the same recovery label so a successful (no-
     * fault) fetch-and-return path also lands at 1f. */
    asm volatile (
        ".option push\n\t"
        ".option norvc\n\t"
        "la   t0, 1f\n\t"
        "la   t1, _exec_return_addr\n\t"
        STORE "   t0, 0(t1)\n\t"
        "mv   ra, t0\n\t"
        "jr   %0\n\t"
        "1:\n\t"
        STORE "   zero, 0(t1)\n\t"
        ".option pop\n\t"
        :: "r"(arg)
        : "t0", "t1", "ra", "memory"
    );
    return trap_get_cause();
}
