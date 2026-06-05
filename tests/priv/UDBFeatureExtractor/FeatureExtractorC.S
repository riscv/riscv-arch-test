// SPDX-License-Identifier: Apache-2.0
// Copyright (c) 2026 RISC-V International

// FeatureExtractorC.S
// ACT wrapper for the C version.
// Sets up local trap counting, enters crt.S, and provides IO/trap helpers.

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: [I, Zicsr, Zifencei, Sm]
# MARCH: rv${XLEN}i_zicsr_zifencei
##### END_TEST_CONFIG #####

#define TEST_FILE "FeatureExtractorC.S"
#define SIGUPD_COUNT 64

#include "riscv_arch_test.h"

RVTEST_BEGIN

    // Save the ACT framework's mtvec before overwriting it.
    csrr    t0, mtvec
    la      t1, saved_mtvec
    SREG    t0, 0(t1)

    // Use a local trap handler for feature-probe instructions.
    la      t0, c_feature_trap_handler
    csrw    mtvec, t0

    // Clear trap counter before entering C.
    la      t0, c_trap_count
    sw      zero, 0(t0)

    // Enter the C runtime in crt.S.
    // crt.S should set up stack/BSS and call main().
    call    _crt_start

    // Restore ACT framework mtvec after C returns.
    la      t0, saved_mtvec
    LREG    t1, 0(t0)
    csrw    mtvec, t1

    j       c_done


// Called from syscalls.c.
// a0 contains a null-terminated string pointer.
.globl arch_write_str_asm
.type arch_write_str_asm, @function
arch_write_str_asm:
    RVMODEL_IO_WRITE_STR(t0, t1, t2, a0)
    ret
.size arch_write_str_asm, . - arch_write_str_asm


// Called from feature_extractor.c.
// Returns current trap count in a0.
.globl read_trap_count_asm
.type read_trap_count_asm, @function
read_trap_count_asm:
    la      t0, c_trap_count
#if __riscv_xlen == 64
    lwu     a0, 0(t0)
#else
    lw      a0, 0(t0)
#endif
    ret
.size read_trap_count_asm, . - read_trap_count_asm


// Local trap handler for probe instructions.
// Handles only expected illegal-instruction traps from 32-bit probe opcodes.
.align 4
c_feature_trap_handler:
    // Save temporaries without using the stack.
    csrw    mscratch, t0

    LA      t0, c_saved_t1
    SREG    t1, 0(t0)

    // Only illegal instruction is expected for the current DIV probe.
    csrr    t1, mcause
    li      t0, 2
    bne     t1, t0, unexpected_trap

    // Count the trap.
    LA      t0, c_trap_count
    lw      t1, 0(t0)
    addi    t1, t1, 1
    sw      t1, 0(t0)

    // Skip the faulting 4-byte probe instruction.
    csrr    t0, mepc
    addi    t0, t0, 4
    csrw    mepc, t0

    // Restore temporaries and resume.
    LA      t0, c_saved_t1
    LREG    t1, 0(t0)
    csrr    t0, mscratch
    mret

unexpected_trap:
    // Unexpected traps should not be treated as feature-probe results.
    RVMODEL_HALT_FAIL

c_done:
    RVTEST_CODE_END


RVTEST_DATA_BEGIN

.align 3
saved_mtvec:
    .dword 0

.align 3
c_saved_t1:
#if __riscv_xlen == 64
    .dword 0
#else
    .word 0
#endif

.align 2
c_trap_count:
    .word 0

RVTEST_DATA_END

RVTEST_SIG_SETUP