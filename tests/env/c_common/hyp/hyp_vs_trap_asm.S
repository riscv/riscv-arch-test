/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/*
 * common/hyp/hyp_vs_trap_asm.S -- VS-mode trap entry (Direct mode)
 *
 * Installed into vstvec by vs_trap_setup_framework().  This is the bottom of
 * the three handler levels: with hedeleg delegating a cause down, a VU/VS-mode
 * trap lands here instead of at the HS handler.
 *
 * Why this exists at all, given that several suites already ship their own
 * hand-rolled VS entry (Sha/tests/sha_strap.S and friends): those are
 * stack-free stubs that spill two temporaries through vsscratch, which is
 * enough to record a stimulus but cannot carry a T-SBI dispatch layer.  A
 * dispatch layer has to hand a full trap frame to a C handler, because the
 * protocol's a0/a1/a2 travel in frame slots (tsbi.h SECTION 6) and the service
 * result has to be written back into frame[TSBI_FRAME_A0].  Hence the same
 * 31-slot frame the M/S/HS entries build - see trap_context.h for why that
 * layout is a protocol rather than a local choice.
 *
 * A VS-mode stack is fine here: the suites run one flat identity-mapped
 * address space with a single stack, so sp is valid at V=1 exactly as it is at
 * V=0 and no vsscratch swap is needed.
 *
 * In VS-mode the plain S CSR names alias the virtual ones, so the C handler's
 * CSRR(scause)/CSRW(sepc) reach vscause/vsepc with no special casing - which is
 * what lets the shared T-SBI service stages in trap.c run here unchanged.
 */

#ifdef ENABLE_HYP

#include "trap_context.h"

    .section .text
    .global _vs_trap_entry
    .p2align 4                      /* vstvec.BASE discards bits 1:0 */
_vs_trap_entry:
    SAVE_CONTEXT

    /* Call C handler: void vs_trap_handler(uintptr_t *frame) */
    mv      a0, sp                  /* frame pointer -> first argument */
    call    vs_trap_handler

    /* RESTORE_CONTEXT reloads a0 from the frame, so a T-SBI result reaches the
     * requester through frame[TSBI_FRAME_A0] and never through a C return
     * value.  VS has exactly one way out, so the handler returns void: there is
     * no mret/sret choice to make here. */
    RESTORE_CONTEXT

    sret

#endif /* ENABLE_HYP */
