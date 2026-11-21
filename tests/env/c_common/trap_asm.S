/*
 * Trap entry points (assembly layer)
 *
 * Saves/restores full register context, calls C handlers,
 * and returns via mret or sret based on handler return value.
 *
 * The frame layout itself lives in trap_context.h so that the HS-mode entry
 * in common/hyp/hyp_trap_asm.S builds a byte-identical frame; see that
 * header for why the layout must not be duplicated.
 */

#include "trap_context.h"

/* =================================================================
 * M-mode trap entry
 *
 * Calls: unsigned m_trap_handler(uintptr_t *frame)
 *   a0 = frame pointer (== sp after SAVE_CONTEXT), so the handler can read
 *   the trapped a0/a1 (T-SBI opcode/argument) at frame[9]/frame[10] and write
 *   a return value back into frame[9].  See tsbi.h SECTION 6.
 *
 * Return value in a0:
 *   PRIV_M (3) -> mret
 *   PRIV_S (1) -> sret (delegated)
 *   PRIV_U (0) -> sret (delegated)
 *
 * NOTE: RESTORE_CONTEXT reloads a0 from frame[9], so the C return value only
 * selects mret vs sret and never reaches the trapped code.  A T-SBI service
 * result MUST be written into frame[9] by the handler.
 * ================================================================= */
    .balign 16
    .global m_trap_entry
m_trap_entry:
    SAVE_CONTEXT
    mv      a0, sp                  /* frame pointer -> first argument */
    jal     m_trap_handler
    j       _trap_return

/* =================================================================
 * S-mode trap entry
 *
 * Calls: unsigned s_trap_handler(uintptr_t *frame)
 * Return value in a0 is always PRIV_S or PRIV_U -> sret
 * ================================================================= */
    .balign 16
    .global s_trap_entry
s_trap_entry:
    SAVE_CONTEXT
    mv      a0, sp                  /* frame pointer -> first argument */
    jal     s_trap_handler
    j       _trap_return

/* =================================================================
 * _tsbi_forward_goto - forward a privilege-raising T-SBI request upwards
 *
 * void _tsbi_forward_goto(uintptr_t *frame);   -- a0 = frame, never returns
 *
 * A handler that cannot serve a GOTO re-issues it as a bare ecall to the next
 * level, which then lands its xret on the ORIGINAL requester instead of on us
 * (the requester's resume PC travels in g_tsbi_forward_resume).  Because
 * control never comes back here, the register context the upper level saves -
 * and therefore restores into the requester - is whatever we leave in the
 * registers now.  So the requester's full context MUST be reloaded before the
 * ecall, and that is something a C function cannot do: the compiler owns
 * sp/s0/ra inside it.  Hence this three-instruction assembly helper.
 *
 * RESTORE_CONTEXT does exactly the required job once sp points at the frame:
 * it reloads x1 and x3-x31 (a0/a1/a2 included, so the T-SBI arguments come
 * straight from the frame) and leaves sp at frame + CONTEXT_SIZE, i.e. the
 * trap-entry sp - the requester's own sp.  Our now-dead frame sits just below
 * that and is simply overwritten by the upper level's SAVE_CONTEXT.
 * ================================================================= */
    .balign 16
    .global _tsbi_forward_goto
_tsbi_forward_goto:
    mv      sp, a0                  /* sp -> frame; our own frame is dead */
    RESTORE_CONTEXT                 /* requester's x1,x3-x31 + sp restored */
    ecall                           /* upper level resumes the requester */

/* =================================================================
 * Common return path
 *
 * a0 = privilege level to return to
 *   3 (PRIV_M) -> mret
 *   otherwise  -> sret
 * ================================================================= */
_trap_return:
    li      t0, 3
    beq     a0, t0, _do_mret

_do_sret:
    RESTORE_CONTEXT
    sret

_do_mret:
    RESTORE_CONTEXT
    mret
