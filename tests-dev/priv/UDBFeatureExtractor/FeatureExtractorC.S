// SPDX-License-Identifier: Apache-2.0
// Copyright (c) 2026 RISC-V International

// FeatureExtractorC.S
// ACT wrapper for the C version.
// Sets up local trap counting, enters crt.S, and provides IO/trap helpers.

#define TEST_FILE "FeatureExtractorC.S"
#define SIGUPD_COUNT 64

#include "riscv_arch_test.h"

RVTEST_BEGIN

    // Save the ACT framework's mtvec before overwriting it.
    csrr    t0, mtvec
    LA      t1, saved_mtvec
    SREG    t0, 0(t1)

    // Use a local trap handler for feature-probe instructions.
    LA      t0, c_feature_trap_handler
    csrw    mtvec, t0

    // Clear trap counter before entering C.
    LA      t0, c_trap_count
    sw      zero, 0(t0)

    // Enter the C runtime in crt.S.
    // crt.S should set up stack/BSS and call main().
    call    _crt_start

    // Restore ACT framework mtvec after C returns.
    LA      t0, saved_mtvec
    LREG    t1, 0(t0)
    csrw    mtvec, t1

    j       c_done


// Called from syscalls.c.
// a0 contains a null-terminated string pointer.
.globl arch_write_str_asm
.type arch_write_str_asm, @function
arch_write_str_asm:
    addi    sp, sp, -32
    SREG    ra, 0(sp)
    SREG    t0, 8(sp)
    SREG    t1, 16(sp)
    SREG    t2, 24(sp)

    RVMODEL_IO_WRITE_STR(t0, t1, t2, a0)

    LREG    t2, 24(sp)
    LREG    t1, 16(sp)
    LREG    t0, 8(sp)
    LREG    ra, 0(sp)
    addi    sp, sp, 32
    ret
.size arch_write_str_asm, . - arch_write_str_asm

// Called from feature_extractor.c.
// Returns nonzero if an unexpected trap occurred.
.globl read_unexpected_trap_asm
.type read_unexpected_trap_asm, @function
read_unexpected_trap_asm:
    LA      t0, c_unexpected_trap
    lw      a0, 0(t0)
    ret
.size read_unexpected_trap_asm, . - read_unexpected_trap_asm

// Called from feature_extractor.c.
// Returns current trap count in a0.
.globl read_trap_count_asm
.type read_trap_count_asm, @function
read_trap_count_asm:
    LA      t0, c_trap_count
#if __riscv_xlen == 64
    lw     a0, 0(t0)
#else
    lw      a0, 0(t0)
#endif
    ret
.size read_trap_count_asm, . - read_trap_count_asm

// Local trap handler for feature-probe instructions.
// Handles expected illegal-instruction traps from fixed-width probe opcodes.
.align 4
c_feature_trap_handler:
    // Only illegal-instruction traps are expected for unsupported instruction probes.
    csrr    t0, mcause
    li      t1, 2
    bne     t0, t1, unexpected_trap

    // Count the trap.
    LA      t0, c_trap_count
#if __riscv_xlen == 64
    lw     t1, 0(t0)
#else
    lw      t1, 0(t0)
#endif
    addi    t1, t1, 1
    sw      t1, 0(t0)

    // TODO: Future compressed-instruction probes will need 2-byte mepc advance.
    // Current probes use fixed 32-bit instructions, so mepc += 4 is correct here.
    csrr    t0, mepc
    addi    t0, t0, 4
    csrw    mepc, t0

    mret

unexpected_trap:
    LA      t0, c_unexpected_trap
    li      t1, 1
    sw      t1, 0(t0)

    // advance mepc by 4 to avoid re-trapping forever and mret out
    csrr    t0, mepc
    addi    t0, t0, 4
    csrw    mepc, t0
    mret

c_done:
    RVTEST_CODE_END


RVTEST_DATA_BEGIN

.align 3
saved_mtvec:
    .dword 0

.align 2
c_trap_count:
    .word 0

.align 2
c_unexpected_trap:
    .word 0

RVTEST_DATA_END

RVTEST_SIG_SETUP
