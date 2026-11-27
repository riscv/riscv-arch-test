#include "encoding.h"

#if __riscv_xlen == 64
    #define REGSIZE 8
    #define LOAD    ld
    #define STORE   sd
#else
    #define REGSIZE 4
    #define LOAD    lw
    #define STORE   sw
#endif

/*
 * PMP platform-specific initialization
 *
 * Overrides the weak _platform_init symbol from common/platform_init.S.
 * Calls _platform_hw_init for common hardware setup (e.g., MAEE clear),
 * then fills the __pmp_test_code region with nop;ret pattern so that
 * exec_at() can safely jump to any 8-byte aligned address.
 */
    .section .text
    .global _platform_init
_platform_init:
    /* Save ra since we are called from entry.S */
    addi    sp, sp, -REGSIZE
    STORE   ra, 0(sp)

    /* Common hardware init (MAEE clear, etc.) */
    call    _platform_hw_init

    /* Fill __pmp_test_code region with nop;ret pattern */
    la      a0, __pmp_test_code
    la      a1, __pmp_test_nomap
    li      a2, 0x00000013          /* nop */
    li      a3, 0x00008067          /* ret (jalr x0, ra, 0) */
_pmp_fill_code:
    beq     a0, a1, _pmp_fill_done
    sw      a2, 0(a0)              /* nop */
    sw      a3, 4(a0)              /* ret */
    addi    a0, a0, 8
    j       _pmp_fill_code
_pmp_fill_done:

    /* Fence to ensure code writes are visible */
    fence.i

    /* Restore ra and return */
    LOAD    ra, 0(sp)
    addi    sp, sp, REGSIZE
    ret
