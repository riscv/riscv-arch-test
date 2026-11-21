/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

#ifndef COMMON_HYP_VS_CAPTURE_H
#define COMMON_HYP_VS_CAPTURE_H

/* ===================================================================
 * Shared VS-mode trap capture facility for the Hypervisor_Z atomic
 * cross-test suites (Zaamo / Zabha / Zacas / Zalasr / Zalrsc).
 *
 * Provides a minimal naked VS-mode trap handler that records
 * vscause/vsepc/vstval (observed as scause/sepc/stval while V=1),
 * advances sepc past the 4-byte faulting instruction, forces SPP=1 so
 * sret returns to VS-mode, plus a helper to install it through the
 * framework's vs_trap_setup_direct() and a helper to clear hstatus
 * GVA/SPV before an HS-delivered trap.
 *
 * Symbol names are intentionally kept identical to the former per-suite
 * copies so existing call sites need no change. These suites use a unity
 * build (every tests .c file is #included into test_register.c), so the
 * static state below has exactly one instance per test binary.
 * =================================================================== */

#include "encoding.h"          /* uintptr_t / bool, HSTATUS_GVA / HSTATUS_SPV */
#include "hyp/hyp_csr.h"       /* hstatus_read / hstatus_write */
#include "hyp/hyp_vs_trap.h"   /* vs_trap_setup_direct */

/* Captured VS-mode trap state (written by hz_vs_handler). */
static volatile uintptr_t g_hz_vs_cause;
static volatile uintptr_t g_hz_vs_epc;
static volatile uintptr_t g_hz_vs_tval;
static volatile bool      g_hz_vs_triggered;

/* ===================================================================
 * VS-mode trap handler (for hedeleg -> VS-mode delivery cases). Records
 * vscause/vsepc/vstval, advances sepc by 4, forces SPP=1, returns.
 * =================================================================== */
static void hz_vs_handler(void) __attribute__((naked, aligned(4)));
static void hz_vs_handler(void)
{
    asm volatile (
        "addi   sp, sp, -40\n\t"
        "sd     ra, 0(sp)\n\t"
        "sd     t0, 8(sp)\n\t"
        "sd     t1, 16(sp)\n\t"
        "sd     t2, 24(sp)\n\t"
        "csrr   t0, scause\n\t"
        "la     t2, g_hz_vs_cause\n\t"
        "sd     t0, 0(t2)\n\t"
        "csrr   t0, sepc\n\t"
        "la     t2, g_hz_vs_epc\n\t"
        "sd     t0, 0(t2)\n\t"
        "csrr   t0, stval\n\t"
        "la     t2, g_hz_vs_tval\n\t"
        "sd     t0, 0(t2)\n\t"
        "li     t0, 1\n\t"
        "la     t2, g_hz_vs_triggered\n\t"
        "sb     t0, 0(t2)\n\t"
        "csrr   t0, sepc\n\t"
        "addi   t0, t0, 4\n\t"
        "csrw   sepc, t0\n\t"
        "li     t0, 0x22\n\t"
        "csrc   sstatus, t0\n\t"
        "li     t0, 0x100\n\t"
        "csrs   sstatus, t0\n\t"
        "ld     ra, 0(sp)\n\t"
        "ld     t0, 8(sp)\n\t"
        "ld     t1, 16(sp)\n\t"
        "ld     t2, 24(sp)\n\t"
        "addi   sp, sp, 40\n\t"
        "sret\n\t"
    );
}

/* Reset capture state and install hz_vs_handler as the VS Direct handler. */
static inline void hz_vs_handler_install(void)
{
    g_hz_vs_cause = 0;
    g_hz_vs_epc = 0;
    g_hz_vs_tval = 0;
    g_hz_vs_triggered = false;
    vs_trap_setup_direct((uintptr_t)hz_vs_handler);
}

/* ===================================================================
 * HS-mode routing for GVA/SPV verification (hstatus.GVA/SPV are written
 * only for traps taken into HS-mode; see norm:hstatus_gva_op/spv_op).
 * hyp_route_exc_to_hs()/hyp_unroute_exc_from_hs() from common.
 * =================================================================== */
static inline void hz_clear_gva_spv(void)
{
    hstatus_write(hstatus_read() & ~(HSTATUS_GVA | HSTATUS_SPV));
}

#endif /* COMMON_HYP_VS_CAPTURE_H */
