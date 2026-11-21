/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

#ifndef TEST_UTILS_H
#define TEST_UTILS_H

/* ===================================================================
 * test_utils.h - Mode-agnostic test utility payloads (opt-in)
 *
 * Access probes: single memory-access payloads with the callback
 * signature uintptr_t (*)(uintptr_t), meant to be handed to a privilege
 * runner -- vm_run_in_smode() / vm_run_in_umode() (common/vm), or
 * run_in_priv() (common/privilege.c).
 *
 * The payload itself is PRIVILEGE AGNOSTIC: it performs one access
 * inside a trap_expect window and returns
 *   - 0      : the access completed without trapping
 *   - scause : the access trapped (value from trap_get_cause())
 * so the SAME probe can be run at M / S / U mode simply by choosing the
 * runner and the target privilege (e.g. run_in_priv(PRIV_U, probe_load,
 * addr) reuses probe_load for U-mode).
 *
 * VS / VU mode are intentionally NOT covered here: their accesses fault
 * as guest-page-faults routed to HS-mode and need htval/SPV/GVA capture,
 * which is the separate common/hyp machinery (test_vs_load/store,
 * fire_vs_load_fault/fire_vs_store_fault, hyp_vs_capture.h). Note that
 * common/hyp's test_vs_load returns the loaded value (no trap window) --
 * a different contract from the probes below.
 *
 * Depends only on the trap framework (test_framework.h), exec_at
 * (mem_ops.h) and MAGIC_WRITE (vm/vm_defs.h). This is an opt-in header:
 * suites that use it must include it explicitly.
 * =================================================================== */

#include "test_framework.h"   /* trap_expect_begin/end, trap_was_triggered, trap_get_cause */
#include "mem_ops.h"          /* exec_at */
#include "vm/vm_defs.h"       /* MAGIC_WRITE */

/* Load uintptr_t at @addr; return 0, or the scause if it trapped. */
static inline uintptr_t probe_load(uintptr_t addr) {
    trap_expect_begin();
    volatile uintptr_t val = *(volatile uintptr_t *)addr;
    (void)val;
    trap_expect_end();
    if (trap_was_triggered())
        return trap_get_cause();
    return 0;
}

/* Store MAGIC_WRITE to uintptr_t at @addr; return 0, or the scause.
 * The stored value is a probe payload only -- callers check the return
 * (fault status), never the written bytes, so a single fixed magic is
 * used for all suites. */
static inline uintptr_t probe_store(uintptr_t addr) {
    trap_expect_begin();
    *(volatile uintptr_t *)addr = MAGIC_WRITE;
    trap_expect_end();
    if (trap_was_triggered())
        return trap_get_cause();
    return 0;
}

/* Fetch/execute at @addr (target must contain a nop sled ending in
 * ret); return 0, or the scause. exec_at() records the return address
 * so the trap handler can recover even when the page is not readable. */
static inline uintptr_t probe_exec(uintptr_t addr) {
    trap_expect_begin();
    exec_at(addr);
    trap_expect_end();
    if (trap_was_triggered())
        return trap_get_cause();
    return 0;
}

/* Load then store uintptr_t at @addr, each in its own trap window;
 * return 0, or the scause of whichever access trapped first. */
static inline uintptr_t probe_load_store(uintptr_t addr) {
    volatile uintptr_t *ptr = (volatile uintptr_t *)addr;

    trap_expect_begin();
    uintptr_t val = ptr[0];
    (void)val;
    trap_expect_end();
    if (trap_was_triggered())
        return trap_get_cause();

    trap_expect_begin();
    ptr[0] = MAGIC_WRITE;
    trap_expect_end();
    if (trap_was_triggered())
        return trap_get_cause();

    return 0;
}

#endif /* TEST_UTILS_H */
