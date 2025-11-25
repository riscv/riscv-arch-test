///////////////////////////////////////////
// ExceptionsF.S
//
// Written: Roman De Santos rdesantos@hmc.edu 20 March 2025
//
// Purpose: Functional coverage test for Exceptions in F mode
//
// SPDX-License-Identifier: Apache-2.0
///////////////////////////////////////////

#include "WALLY-init-lib.h"

main:

///////////////////////////////////////////////////////////
// cp_mstatus_fs_illegal_instr AND cp_mstatus_fs_csr_write
///////////////////////////////////////////////////////////
    // Test floating point instructions function with:
    // mstatus.FS = 0, frm = 0
    li  a0, 0
    li  a1, 0
    jal ra, fp_instructions

/////////////////////////////////
// cp_badfrm
/////////////////////////////////

    // Test floating point instructions function with:
    // mstatus.FS = 1, frm = 5
    li  a0, 1
    li  a1, 5
    jal ra, fp_instructions

    // Test floating point instructions function with:
    // mstatus.FS = 1, frm = 6
    li  a0, 1
    li  a1, 6
    jal ra, fp_instructions

    // Test floating point instructions function with:
    // mstatus.FS = 1, frm = 7
    li  a0, 1
    li  a1, 7
    jal ra, fp_instructions

/////////////////////////////////
// cp_mstatus_fs_legal
/////////////////////////////////

    // Test floating point instructions function with:
    // mstatus.FS = 1, frm = 0
    li  a0, 1
    li  a1, 0
    jal ra, fp_instructions

    // Test floating point instructions function with:
    // mstatus.FS = 2, frm = 0
    li  a0, 2
    li  a1, 0
    jal ra, fp_instructions

    //Test floating point instructions function with:
    //mstatus.FS = 3, frm = 0
    li  a0, 3
    li  a1, 0
    jal ra, fp_instructions

finished:
    j done

/////////////////////////////////
/////////////////////////////////
// fp_instructions
/////////////////////////////////
/////////////////////////////////

// Function that executes select floating point instructions in the F extension.
// Also test selected Zfa instructions, which will trap if Zfa is not supported.
// These instructions are executed with different mstatus.FS values and legal/illegal rounding modes.
//
// a0: Sets value of mstatus.FS (ranges from 0-3; Off, Initial, Clean, and Dirty respectively).
//    When a fp register is modified mstatus.FS is marked as dirty automatically. To test fp instructions
//    with different mstatus.FS values, mstatus.FS is updated to the value in a0 before each fp instruction.
//
// a1: Sets value of the frm CSR (ranges from 0-7).
//    This sets and restores the value of frm after each csrrw/csrrc instruction is tested.
fp_instructions:

    // Set up clear mask for mstatus.FS
    li s1, 0x6000      // (1's in bit 13 and 14 of mstatus)

    // Set mstatus.FS to 10 to enable fp for initialization
    li t0,0x4000
    csrs mstatus, t0

    // Set frm to a legal value for initialization
    csrw frm, 0

    // Initialize scratch memory
    la      t5, scratch

    li     t1, 0xDEADBEEF
    sw     t1, 0(t5)
    sw     t1, 4(t5)
    sw     t1, 8(t5)
    sw     t1, 12(t5)

    // Initialize floating point registers used
    li t0, 1
    fcvt.s.w f0, t0

    li t0, 2
    fcvt.s.w f1, t0

    li t0, 3
    fcvt.s.w f2, t0

    li t0, 4
    fcvt.s.w f3, t0

    li t0, 5
    fcvt.s.w f4, t0

    li t0, 6
    fcvt.s.w f5, t0

    li t0, 7
    fcvt.s.w f6, t0

    li t0, 8
    fcvt.s.w f7, t0

    li t0, 9
    fcvt.s.w f8, t0

    li t0, 10
    fcvt.s.w f9, t0

    li t0, 11
    fcvt.s.w f10, t0

    li t0, 12
    fcvt.s.w f11, t0

    li t0, 13
    fcvt.s.w f12, t0

    li t0, 14
    fcvt.s.w f13, t0

    li t0, 15
    fcvt.s.w f14, t0

    // Create mstatus.FS set mask dependent on a0
    slli s2, a0, 13  // shift a0 to mstatus.FS bits

    // After initialization set frm to the value in a1
    // in case the value in a1 is illegal
    csrw frm, a1

    // --- Floating-Point Memory Operations ---

        // Set mstatus.FS
        csrc mstatus, s1
        csrs mstatus, s2
    fsw    f0, 0(a4)

        // Set mstatus.FS
        csrc mstatus, s1
        csrs mstatus, s2
    flw    f1, 0(a4)

    // --- Floating-Point Arithmetic Operations ---
        // Set mstatus.FS
        csrc mstatus, s1
        csrs mstatus, s2
    fadd.s f2, f0, f1

        // Set mstatus.FS
        csrc mstatus, s1
        csrs mstatus, s2
    fsub.s f3, f0, f1

        // Set mstatus.FS
        csrc mstatus, s1
        csrs mstatus, s2
    fmul.s f4, f0, f1

        // Set mstatus.FS
        csrc mstatus, s1
        csrs mstatus, s2
    fdiv.s f5, f0, f1

    // --- Floating‑Point Conversions ---

        // Set mstatus.FS
        csrc mstatus, s1
        csrs mstatus, s2
    fcvt.w.s t2, f0

        // Set mstatus.FS
        csrc mstatus, s1
        csrs mstatus, s2
    fcvt.s.w f6, t2

        // Set mstatus.FS
        csrc mstatus, s1
        csrs mstatus, s2
    fcvt.s.d f7, f0

    // --- Floating Point Arithmetic ---

        // Set mstatus.FS
        csrc mstatus, s1
        csrs mstatus, s2
    fmadd.s f8, f0, f1, f2

        // Set mstatus.FS
        csrc mstatus, s1
        csrs mstatus, s2
    fsqrt.s f9, f0

        // Set mstatus.FS
        csrc mstatus, s1
        csrs mstatus, s2
    fsgnj.s f10, f0, f1

        // Set mstatus.FS
        csrc mstatus, s1
        csrs mstatus, s2
    feq.s  t3, f0, f1

    // --- Move Bit Representations ---
        // Set mstatus.FS
        csrc mstatus, s1
        csrs mstatus, s2
    fmv.x.w t4, f0

        // Set mstatus.FS
        csrc mstatus, s1
        csrs mstatus, s2
    fmv.w.x f11, t4

    // --- Floating‑Point Classification and Minimum ---
        // Set mstatus.FS
        csrc mstatus, s1
        csrs mstatus, s2
    fclass.s t5, f0

        // Set mstatus.FS
        csrc mstatus, s1
        csrs mstatus, s2
    fmin.s f12, f0, f1

    // --- Zfa Extension Instructions ---
        // Set mstatus.FS
        csrc mstatus, s1
        csrs mstatus, s2
    fround.s f14, f0

        // Set mstatus.FS
        csrc mstatus, s1
        csrs mstatus, s2
    fli.s  f2, 2.5

    // --- CSR Operations on Floating‑Point Status Registers ---

    // Note for the following csrrw and  csrrc instructions:
    // Since fcsr, frm, and fflags are part of the same csr, frm is restored after each
    // csrrw/csrrc instruction. This prevents accidental modification of the frm register.

        // Set mstatus.FS
        csrc mstatus, s1
        csrs mstatus, s2
    csrrw  t1, fcsr, x0

        // Restore frm
        csrw frm, a1
        // Set mstatus.FS
        csrc mstatus, s1
        csrs mstatus, s2
    csrrw  t0, frm, a1   // a1 stores the value of frm

        // Restore frm
        csrw frm, a1
        // Set mstatus.FS
        csrc mstatus, s1
        csrs mstatus, s2
    csrrw  t1, fflags, x0

        // Restore frm
        csrw frm, a1
        // Set mstatus.FS
        csrc mstatus, s1
        csrs mstatus, s2
    csrrs  t1, fcsr, t1

        // Set mstatus.FS
        csrc mstatus, s1
        csrs mstatus, s2
    csrrs  t1, fflags, t1

        // Set mstatus.FS
        csrc mstatus, s1
        csrs mstatus, s2
    csrrs  t0, frm, a1   // a1 stores the value of frm

        // Set mstatus.FS
        csrc mstatus, s1
        csrs mstatus, s2
    csrrc  t1, fcsr, t1

        // Restore frm
        csrw frm, a1
        // Set mstatus.FS
        csrc mstatus, s1
        csrs mstatus, s2
    csrrc  t1, fcsr, t1

        // Restore frm
        csrw frm, a1
        // Set mstatus.FS
        csrc mstatus, s1
        csrs mstatus, s2
    csrrc  t1, frm, a1   // a1 stores the value of frm

        // Restore frm
        csrw frm, a1
        // Set mstatus.FS
        csrc mstatus, s1
        csrs mstatus, s2
    csrrc  t1, fflags, t1

    // 32-bit only instructions
    #ifdef __riscv_xlen
    #if __riscv_xlen == 32
            // Set mstatus.FS
            csrc mstatus, s1
            csrs mstatus, s2
        fmv.x.w t1, f0

            // Set mstatus.FS
            csrc mstatus, s1
            csrs mstatus, s2
        fmvh.x.d t2, f0

            // Set mstatus.FS
            csrc mstatus, s1
            csrs mstatus, s2
        fmvp.d.x f1, t1, t2
    #endif
    #endif

    ret
