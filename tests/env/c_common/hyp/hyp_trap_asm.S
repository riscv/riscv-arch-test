/* ===================================================================
 * common/hyp/hyp_trap_asm.S — HS-mode trap vector entry point
 *
 * Provides _hs_trap_entry for use as the stvec value when testing
 * hedeleg-delegated traps (traps from VS/VU-mode delivered to
 * HS-mode via stvec instead of mtvec).
 *
 * The frame is built with the shared SAVE_CONTEXT/RESTORE_CONTEXT macros
 * from common/trap_context.h, byte-identical to the one m_trap_entry /
 * s_trap_entry build.  That is mandatory, not tidiness: while a test has
 * this vector installed in stvec it REPLACES s_trap_entry, so this is the
 * only S-level T-SBI service point in existence - and hs_trap_handler can
 * only serve a request if it can read the opcode out of the frame at
 * TSBI_FRAME_A0 and write the result back there.  A private layout would
 * shift that slot.
 *
 * Using the full x1-x31 frame also removes the old 23-register frame's
 * caveat that VS-mode payloads must avoid s7-s11.
 *
 * NOTE: This is only needed when tests explicitly set up hedeleg to
 * delegate certain exceptions to VS-mode (which first traps to
 * HS-mode via stvec). For the majority of G-stage tests that keep
 * hedeleg=0, all traps go directly to M-mode and this code is not
 * invoked.
 * =================================================================== */

#ifdef ENABLE_HYP

#include "trap_context.h"

.section .text
.global _hs_trap_entry
.p2align 4

_hs_trap_entry:
    /* Save context on the current stack.  Tests run with a shared flat
     * address space and a single stack, so no sscratch swap is needed even
     * when the trap came from V=1. */
    SAVE_CONTEXT

    /* Call C handler: unsigned hs_trap_handler(uintptr_t *frame) */
    mv      a0, sp                  /* frame pointer -> first argument */
    call    hs_trap_handler

    /* The return value only documents the handler level (always PRIV_S
     * here); RESTORE_CONTEXT reloads a0 from the frame, so a T-SBI result
     * reaches the requester through frame[TSBI_FRAME_A0], never through the
     * C return value.  HS always leaves via sret. */
    RESTORE_CONTEXT

    sret

#endif /* ENABLE_HYP */
