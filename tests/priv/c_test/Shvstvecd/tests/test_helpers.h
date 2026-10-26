/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/*
 * test_helpers.h - Common definitions for the Shvstvecd test suite.
 *
 * All test files (test_mode.c / test_base.c / test_direct.c /
 * test_transparent.c / test_vectored.c) are #included into
 * test_register.c, so static functions and globals defined here are
 * visible across the whole compilation unit.
 *
 * Shvstvecd semantics (per SPEC/shvstvecd.adoc):
 *   - vstvec.MODE must be capable of holding 0 (Direct).
 *   - When vstvec.MODE=Direct, vstvec.BASE must be capable of holding
 *     any valid four-byte-aligned address.
 */

#ifndef SHVSTVECD_TEST_HELPERS_H
#define SHVSTVECD_TEST_HELPERS_H

#include "test_framework.h"
#include "hyp/hyp_defs.h"
#include "hyp/hyp_csr.h"
#include "hyp/hyp_priv.h"
#include "hyp/hyp_test.h"
#include "hyp/hyp_reset.h"
#include "hyp/hyp_vs_trap.h"
#include "hyp/two_stage_helpers.h"

/* SSIE / SSIP bit position (= bit 1) */
#define BIT_SSI                (1UL << 1)

/* ===================================================================
 * Globals provided by tests/shvstvecd_strap.S
 * =================================================================== */
extern volatile uintptr_t g_shvstvecd_trap_pc;
extern volatile uintptr_t g_shvstvecd_trap_cause;
extern void               shvstvecd_trap_entry(void);
extern unsigned long      shvstvecd_trap_scratch[];
extern void               shvstvecd_vectored_table(void);
extern void               shvstvecd_vectored_handler(void);
extern volatile uintptr_t g_shvstvecd_vec_marker;

/* ===================================================================
 * vstvec read/write helpers
 *
 * Use the framework's hyp_csr.h APIs: vstvec_read(), vstvec_write().
 * =================================================================== */

/* ===================================================================
 * Per-test save / restore vstvec
 * =================================================================== */
#define VSTVEC_SAVE()        uintptr_t __saved_vstvec = vstvec_read()
#define VSTVEC_RESTORE()     vstvec_write(__saved_vstvec)

/* ===================================================================
 * Reset trap-record globals
 * =================================================================== */
static inline void shvstvecd_reset_trap_record(void) {
    g_shvstvecd_trap_pc    = 0;
    g_shvstvecd_trap_cause = 0;
    /* Arm vsscratch so the asm trap entry can spill t0/t1.
     * Write to CSR 0x240 (vsscratch) from M/HS-mode. */
    asm volatile ("csrw " CSR_STR(CSR_VSSCRATCH) ", %0"
                  :: "r"(shvstvecd_trap_scratch) : "memory");
}

/* ===================================================================
 * scause helpers (delegate to common/cause_defs.h inline functions)
 * =================================================================== */
#define shvstvecd_is_interrupt  cause_is_interrupt
#define shvstvecd_cause_code    cause_get_code

/* ===================================================================
 * Unmapped VA for page-fault tests (DIR-03).
 * This address is deliberately NOT mapped in VS-stage page tables.
 * =================================================================== */
#define UNMAPPED_VA_1  0x40000000UL

#endif /* SHVSTVECD_TEST_HELPERS_H */
