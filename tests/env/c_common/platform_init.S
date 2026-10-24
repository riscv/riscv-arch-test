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
 * Common platform hardware initialization
 *
 * _platform_hw_init: Performs platform-specific CSR setup that all
 * projects need (e.g., clearing T-Head MAEE bit). This is a strong
 * symbol that can be called by any project's _platform_init.
 *
 * _platform_init (weak): Default platform init that just calls
 * _platform_hw_init. Projects with additional init needs (e.g., PMP
 * test code region filling) can override this weak symbol with their
 * own strong _platform_init that calls _platform_hw_init first.
 */

/* ===================================================================
 * _platform_hw_init - Hardware-level platform initialization
 *
 * Called by _platform_init (or overrides thereof) to perform
 * platform-specific CSR setup common to all projects.
 * =================================================================== */
    .section .text
    .global _platform_hw_init
_platform_hw_init:
    /* This is a non-leaf function (calls platform_clear_maee), so we
     * must save/restore ra around the call. Without this, the 'call'
     * instruction (jal ra, ...) clobbers ra, and 'ret' at the end
     * jumps back to itself in an infinite loop. */
    addi    sp, sp, -REGSIZE
    STORE   ra, 0(sp)

    /* Clear T-Head MAEE bit if needed (PLATFORM_CLEAR_MAEE is checked
     * at C compile time in platform_clear_maee via platform_config.h).
     * Called from C because platform_config.h is no longer in ASFLAGS. */
    call    platform_clear_maee

    /* Release RAS block from SoC reset if the platform defines the
     * E908A RAS reset control register (E908A_RAS_RESET_ADDR).  The
     * function is a no-op on platforms without this macro.  This must
     * happen before any RERI MMIO access, otherwise the CPU bus hangs. */
    call    platform_release_ras_reset

    LOAD    ra, 0(sp)
    addi    sp, sp, REGSIZE
    ret

/* ===================================================================
 * _platform_init (weak) - Default platform initialization
 *
 * Simply calls _platform_hw_init. Projects that need additional
 * initialization (e.g., PMP test code filling) should provide their
 * own strong _platform_init that calls _platform_hw_init first,
 * then performs project-specific setup.
 * =================================================================== */
    .global _platform_init
    .weak   _platform_init
_platform_init:
    addi    sp, sp, -REGSIZE
    STORE   ra, 0(sp)

    call    _platform_hw_init

    LOAD    ra, 0(sp)
    addi    sp, sp, REGSIZE
    ret
