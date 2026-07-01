// SPDX-License-Identifier: Apache-2.0
// Copyright (c) 2026 RISC-V International
//
// crt.S  –  Minimal bare-metal C runtime for UDBFeatureExtractor (C version).

#if __riscv_xlen == 64
# define LREG ld
# define SREG sd
# define REGBYTES 8
#else
# define LREG lw
# define SREG sw
# define REGBYTES 4
#endif

.section ".text.init", "ax", @progbits
.globl _crt_start
.type _crt_start, @function

_crt_start:

    // Only hart 0 continues
    csrr    a0, mhartid
    bnez    a0, _hart_park

    // Initialize global pointer
    .option push
    .option norelax
    la      gp, __global_pointer$
    .option pop

    // This minimal runtime clears .bss only. It assumes the target/linker setup
    // loads .data at its runtime address. If a future target uses separate
    // LMA/VMA for .data, add a .data copy loop here.
    la      t0, __bss_start
    la      t1, __bss_end
1:
    bge     t0, t1, 2f
    SREG    zero, 0(t0)
    addi    t0, t0, REGBYTES
    j       1b
2:

    // Set up stack
    la      sp, _stack_top
    li      t0, -16
    and     sp, sp, t0

    // Save return address back to FeatureExtractorC.S.
    addi    sp, sp, -16
    SREG    ra, 0(sp)

    // Call main(argc=0, argv=NULL, envp=NULL).
    li      a0, 0
    li      a1, 0
    li      a2, 0
    call    main

    // Restore return address and return to FeatureExtractorC.S.
    LREG    ra, 0(sp)
    addi    sp, sp, 16
    ret

_hart_park:
    wfi
    j       _hart_park

.size _crt_start, . - _crt_start
