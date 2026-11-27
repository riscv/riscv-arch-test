/*
 * Trap frame layout — shared by every assembly trap entry point
 *
 * ASSEMBLY-ONLY header: it defines .macro directives and must never be
 * included from C.
 *
 * The layout below is a protocol, not a local implementation detail:
 *   - common/tsbi/tsbi.h SECTION 6 hard-codes the a0/a1/a2 slot indices
 *     (TSBI_FRAME_A0/A1/A2 = 9/10/11) and locks them with _Static_assert;
 *   - _tsbi_forward_goto() in common/trap_asm.S recovers the trap-entry sp as
 *     `frame + CONTEXT_SIZE` while reloading the requester's context.
 *
 * So every entry point that hands its frame to a T-SBI-aware C handler MUST
 * build that frame with the macros here instead of rolling its own; a
 * private layout would silently shift the opcode slot and hand the handler
 * a garbage request.
 */

#ifndef COMMON_TRAP_CONTEXT_H
#define COMMON_TRAP_CONTEXT_H

#if __riscv_xlen == 64
    #define LOAD    ld
    #define STORE   sd
    #define REGSIZE 8
#else
    #define LOAD    lw
    #define STORE   sw
    #define REGSIZE 4
#endif

#define CONTEXT_SIZE (REGSIZE * 31)

/* ===== Save all general-purpose registers (x1-x31) =====
 * sp[i] == x(i+1); the x2 (sp) slot at index 1 is left unused. */
.macro SAVE_CONTEXT
    addi    sp, sp, -CONTEXT_SIZE

    STORE   x1,  0*REGSIZE(sp)
    STORE   x3,  2*REGSIZE(sp)
    STORE   x4,  3*REGSIZE(sp)
    STORE   x5,  4*REGSIZE(sp)
    STORE   x6,  5*REGSIZE(sp)
    STORE   x7,  6*REGSIZE(sp)
    STORE   x8,  7*REGSIZE(sp)
    STORE   x9,  8*REGSIZE(sp)
    STORE   x10, 9*REGSIZE(sp)
    STORE   x11, 10*REGSIZE(sp)
    STORE   x12, 11*REGSIZE(sp)
    STORE   x13, 12*REGSIZE(sp)
    STORE   x14, 13*REGSIZE(sp)
    STORE   x15, 14*REGSIZE(sp)
    STORE   x16, 15*REGSIZE(sp)
    STORE   x17, 16*REGSIZE(sp)
    STORE   x18, 17*REGSIZE(sp)
    STORE   x19, 18*REGSIZE(sp)
    STORE   x20, 19*REGSIZE(sp)
    STORE   x21, 20*REGSIZE(sp)
    STORE   x22, 21*REGSIZE(sp)
    STORE   x23, 22*REGSIZE(sp)
    STORE   x24, 23*REGSIZE(sp)
    STORE   x25, 24*REGSIZE(sp)
    STORE   x26, 25*REGSIZE(sp)
    STORE   x27, 26*REGSIZE(sp)
    STORE   x28, 27*REGSIZE(sp)
    STORE   x29, 28*REGSIZE(sp)
    STORE   x30, 29*REGSIZE(sp)
    STORE   x31, 30*REGSIZE(sp)
.endm

/* ===== Restore all general-purpose registers (x1-x31) ===== */
.macro RESTORE_CONTEXT
    LOAD    x1,  0*REGSIZE(sp)
    LOAD    x3,  2*REGSIZE(sp)
    LOAD    x4,  3*REGSIZE(sp)
    LOAD    x5,  4*REGSIZE(sp)
    LOAD    x6,  5*REGSIZE(sp)
    LOAD    x7,  6*REGSIZE(sp)
    LOAD    x8,  7*REGSIZE(sp)
    LOAD    x9,  8*REGSIZE(sp)
    LOAD    x10, 9*REGSIZE(sp)
    LOAD    x11, 10*REGSIZE(sp)
    LOAD    x12, 11*REGSIZE(sp)
    LOAD    x13, 12*REGSIZE(sp)
    LOAD    x14, 13*REGSIZE(sp)
    LOAD    x15, 14*REGSIZE(sp)
    LOAD    x16, 15*REGSIZE(sp)
    LOAD    x17, 16*REGSIZE(sp)
    LOAD    x18, 17*REGSIZE(sp)
    LOAD    x19, 18*REGSIZE(sp)
    LOAD    x20, 19*REGSIZE(sp)
    LOAD    x21, 20*REGSIZE(sp)
    LOAD    x22, 21*REGSIZE(sp)
    LOAD    x23, 22*REGSIZE(sp)
    LOAD    x24, 23*REGSIZE(sp)
    LOAD    x25, 24*REGSIZE(sp)
    LOAD    x26, 25*REGSIZE(sp)
    LOAD    x27, 26*REGSIZE(sp)
    LOAD    x28, 27*REGSIZE(sp)
    LOAD    x29, 28*REGSIZE(sp)
    LOAD    x30, 29*REGSIZE(sp)
    LOAD    x31, 30*REGSIZE(sp)

    addi    sp, sp, CONTEXT_SIZE
.endm

#endif /* COMMON_TRAP_CONTEXT_H */
