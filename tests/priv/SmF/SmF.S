///////////////////////////////////////////
// SmF.S
//
// Written: Roman De Santos rdesantos@hmc.edu 26 March 2025
//
// Purpose: Functional coverage test for SmF in M mode
//
// SPDX-License-Identifier: Apache-2.0
///////////////////////////////////////////

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: [I, F, Sm]
# MARCH: rv${XLEN}ifdzfa
# CONFIG_DEPENDENT: true
##### END_TEST_CONFIG #####

#include "rvtest_config.h"
#include "WALLY-init-lib.h"

main:

//    When a fp register is modified mstatus.FS is marked as dirty automatically. To test fp instructions
//    with different mstatus.FS values, mstatus.FS is updated to the value in a0 before each fp instruction
//    when required by the coverpoint.

///////////////////////
//cp_fcsr_frm_write
///////////////////////

// Function that writes values 0-7 to the frm bits in the fcsr CSR with mstatus.FS values from 1-3.
// Restores original CSR value at the end of the function.
cp_fcsr_frm_write:
    li      t0, 0           //  Initialize counter t0 to 0
    csrr    s0, fcsr        //  Save the original fcsr CSR

    //  Set up clear/dirty mask for mstatus.FS (bits 13 and 14)
    li      t1, 0x6000
    //  Set up init mask for mstatus.FS (FS = 01)
    li      t2, 0x2000
    //  Set up clean mask for mstatus.FS (FS = 10)
    li      t3, 0x4000
    //  Set up loop limit
    li      t4, 8

  fcsr_frm_write_loop:

    slli    t5, t0, 5       //  Shift counter to the fmr bits in the fcsr CSR

    //  Write to frm when mstatus.FS = 01
        // mstatus.FS = 01
        csrc    mstatus, t1
        csrs    mstatus, t2
    csrrw   x0, fcsr, t5

    //  Write to frm when mstatus.FS = 10
        // mstatus.FS = 10
        csrc    mstatus, t1
        csrs    mstatus, t3
    csrrw   x0, fcsr, t5

    //  Write to frm when mstatus.FS = 11
        // mstatus.FS = 11
        csrs    mstatus, t1
    csrrw   x0, fcsr, t5

    addi    t0, t0, 1                 //  Increment counter
    blt     t0, t4, fcsr_frm_write_loop    //  Loop until t0 equals 8

    //Restore the original frm CSR
    csrrw   x2, fcsr, s0

///////////////////////
//cp_fcsr_fflags_write
///////////////////////

// Function that writes values 0-31 to the fflags bits in the fcsr CSR with mstatus.FS values from 1-3.
// Restores original CSR value at the end of the function.
cp_fcsr_fflags_write:
    li      t0, 0           //  Initialize counter t0 to 0
    csrr    s0, fcsr        //  Save the original fcsr CSR

    //  Set up clear mask for mstatus.FS (bits 13 and 14)
    li      t1, 0x6000
    //  Set up init mask for mstatus.FS (FS = 01)
    li      t2, 0x2000
    //  Set up clean mask for mstatus.FS (FS = 10)
    li      t3, 0x4000
    //  Set up loop limit in a different register (use t4)
    li      t4, 32

 fcsr_fflags_write_loop:

    //  fflags are bits 0-4 of the fcsr CSR, no shift necessary

    //  Write to frm when mstatus.FS = 01
    csrc    mstatus, t1
    csrs    mstatus, t2
    csrrw   x0, fcsr, t0

    //  Write to frm when mstatus.FS = 10
    csrc    mstatus, t1
    csrs    mstatus, t3
    csrrw   x0, fcsr, t0

    //  Write to frm when mstatus.FS = 11
    csrs    mstatus, t1
    csrrw   x0, fcsr, t0

    addi    t0, t0, 1                         //  Increment counter
    blt     t0, t4, fcsr_fflags_write_loop    //  Loop until t0 equals 8

    //Restore the original frm CSR
    csrrw   x2, fcsr, s0

///////////////////////
//cp_fcsrwalk
///////////////////////

// Function that writes walking 1's and 0's to the fcsr CSR with mstatus.FS values from 1-3.
// Restores original CSR value at the end of the function.
cp_fcsrwalk:
    li      t0, 0           //  Initialize loop counter t0 to 3 (start walking 1 in bit 3)
    csrr    s0, fcsr        //  Save the original frm csr

    //  Set up clear mask for mstatus.FS (bits 13 and 14)
    li      t1, 0x6000
    //  Set up init mask for mstatus.FS (FS = 01)
    li      t2, 0x2000
    //  Set up clean mask for mstatus.FS (FS = 10)
    li      t3, 0x4000
    // Initialize walking pattern
    li      t5, 1


 fcsrwalk_loop:

    // walking 1

        // clear csr
        csrrw x0, fcsr, x0
        //  Write to fcsr when mstatus.FS = 01
        csrc    mstatus, t1
        csrs    mstatus, t2
    csrrs   x0, fcsr, t5

        // clear csr
        csrrw x0, fcsr, x0
        //  Write to fcsr when mstatus.FS = 10
        csrc    mstatus, t1
        csrs    mstatus, t3
    csrrs   x0, fcsr, t5

        // clear csr
        csrrw x0, fcsr, x0
        //  Write to fcsr when mstatus.FS = 11
        csrs    mstatus, t1
    csrrs   x0, fcsr, t5

    // walking 0

    //set csr to all 1s
    li t6, -1           //  all 1s
    csrrs t6, fcsr, t1    //  set all bits

        // clear csr
        csrrw x0, fcsr, x0
        //  Write to fcsr when mstatus.FS = 01
        csrc    mstatus, t1
        csrs    mstatus, t2
    csrrc   x0, fcsr, t5

        // clear csr
        csrrw x0, fcsr, x0
        //  Write to fcsr when mstatus.FS = 10
        csrc    mstatus, t1
        csrs    mstatus, t3
    csrrc   x0, fcsr, t5

        // clear csr
        csrrw x0, fcsr, x0
        //  Write to fcsr when mstatus.FS = 11
        csrs    mstatus, t1
    csrrc   x0, fcsr, t5

    // Compute walking pattern:
    slli     t5, t5, 1             // walk one
    bnez     t5, fcsrwalk_loop     // Loop until t5 is shifted past XLEN

    //  Restore the original fcsr
    csrrw   x2, fcsr, s0

///////////////////////
//cp_frm_write
///////////////////////
// Function that writes values 0-7 to the frm CSR with mstatus.FS values from 1-3.
// Restores original CSR value at the end of the function.
cp_frm_write:
    li      t0, 0           //  Initialize counter t0 to 0
    csrr    s0, frm         //  Save the original frm CSR

    //  Set up clear mask for mstatus.FS (bits 13 and 14)
    li      t1, 0x6000
    //  Set up init mask for mstatus.FS (FS = 01)
    li      t2, 0x2000
    //  Set up clean mask for mstatus.FS (FS = 10)
    li      t3, 0x4000
    //  Set up loop limit in a different register (use t4)
    li      t4, 8

 frm_write_loop:
    //  Write to frm when mstatus.FS = 01
    csrc    mstatus, t1
    csrs    mstatus, t2
    csrrw   x0, frm, t0

    //  Write to frm when mstatus.FS = 10
    csrc    mstatus, t1
    csrs    mstatus, t3
    csrrw   x0, frm, t0

    //  Write to frm when mstatus.FS = 11
    csrs    mstatus, t1
    csrrw   x0, frm, t0

    addi    t0, t0, 1                 // Increment counter
    blt     t0, t4, frm_write_loop    // Loop until t0 equals 8

    //Restore the original frm CSR
    csrrw   x2, frm, s0

///////////////////////
//cp_frmwalk
///////////////////////

// Writes walking 1's and 0's to the frm CSR with mstatus.FS values from 1-3.
// Restores original CSR value at the end of the function.
cp_frm_walk:
    li      t0, 0          // Initialize loop counter t0 to 0
    csrr    s0, frm        // Save the original frm csr

    //  Set up clear mask for mstatus.FS (bits 13 and 14)
    li      t1, 0x6000
    //  Set up init mask for mstatus.FS (FS = 01)
    li      t2, 0x2000
    //  Set up clean mask for mstatus.FS (FS = 10)
    li      t3, 0x4000
    //initialize walking pattern
    li      t5, 1

 fcsr_frm_walk_loop:
    //walking 1
        // clear csr
        csrrw x0, frm, x0
        // Write to fcsr when mstatus.FS = 01
        csrc    mstatus, t1
        csrs    mstatus, t2
    csrrs   x0, frm, t5

        // clear csr
        csrrw x0, frm, x0
        // Write to fcsr when mstatus.FS = 10
        csrc    mstatus, t1
        csrs    mstatus, t3
    csrrs   x0, frm, t5

        // clear csr
        csrrw x0, frm, x0
        //  Write to fcsr when mstatus.FS = 11
        csrs    mstatus, t1
    csrrs   x0, frm, t5

    //walking 0

    //set csr to all 1s
    li t6, -1           // all 1s
    csrrs t6, frm, t1   //  set all bits

            // clear csr
        csrrw x0, frm, x0
        //  Write to fcsr when mstatus.FS = 01
        csrc    mstatus, t1
        csrs    mstatus, t2
    csrrc   x0, frm, t5

        // clear csr
        csrrw x0, frm, x0
        //  Write to fcsr when mstatus.FS = 10
        csrc    mstatus, t1
        csrs    mstatus, t3
    csrrc   x0, frm, t5

        // clear csr
        csrrw x0, frm, x0
        // Write to fcsr when mstatus.FS = 11
        csrs    mstatus, t1
    csrrc   x0, frm, t5

    // Compute walking pattern:
    slli     t5, t5, 1              // walk one
    bnez    t5, fcsr_frm_walk_loop  // Loop until t5 is shifted past XLEN

    // Restore the original fcsr
    csrrw   x2, frm, s0


///////////////////////
//cp_fflags_write
///////////////////////
// Function that writes values 0-31 to the fflags CSR with different mstatus.FS values.
// Restores original CSR value at the end of the function.
cp_fflags_write:
    li      t0, 0           // Initialize counter t0 to 0
    csrr    s0, fflags      // Save the original fflags CSR

    // Set up clear mask for mstatus.FS (bits 13 and 14)
    li      t1, 0x6000
    // Set up init mask for mstatus.FS (FS = 01)
    li      t2, 0x2000
    // Set up clean mask for mstatus.FS (FS = 10)
    li      t3, 0x4000
    // Set up loop limit
    li      t4, 32

 fflags_write_loop:
    // Write to frm when mstatus.FS = 01
    csrc    mstatus, t1
    csrs    mstatus, t2
    csrrw   x0, fflags, t0

    // Write to frm when mstatus.FS = 10
    csrc    mstatus, t1
    csrs    mstatus, t3
    csrrw   x0, fflags, t0

    // Write to frm when mstatus.FS = 11
    csrs    mstatus, t1
    csrrw   x0, fflags, t0

    addi    t0, t0, 1                    // Increment counter
    blt     t0, t4, fflags_write_loop    // Loop until t0 equals 8

    //Restore the original fflags CSR
    csrrw   x2, frm, s0

///////////////////////
//cp_fflagswalk
///////////////////////

// Writes walking 1's and 0's to the fflags CSR with mstatus.FS.
// Restores original CSR value at the end of the function.
cp_fflagswalk:
    // Save the original frm csr
    csrr    s0, fflags
    // Set up clear mask for mstatus.FS (bits 13 and 14)
    li      t1, 0x6000
    // Set up init mask for mstatus.FS (FS = 01)
    li      t2, 0x2000
    // Set up clean mask for mstatus.FS (FS = 10)
    li      t3, 0x4000
    // Initialize walking pattern
    li      t5, 1


 fflagswalk_loop:

    //walking 1
        // clear csr
        csrrw x0, fflags, x0
        // Write to fflags when mstatus.FS = 01
        csrc    mstatus, t1
        csrs    mstatus, t2

    csrrs   x0, fflags, t5

        // clear csr
        csrrw x0, fflags, x0
        // Write to fflags when mstatus.FS = 10
        csrc    mstatus, t1
        csrs    mstatus, t3

    csrrs   x0, fflags, t5

        // clear csr
        csrrw x0, fflags, x0
        // Write to fflags when mstatus.FS = 11
        csrs    mstatus, t1

    csrrs   x0, fflags, t5

    // walking 0

    //set csr to all 1s
    li t6, -1
    csrrs t6, fflags, t1

        // clear csr
        csrrw x0, fflags, x0
        // Write to fflags when mstatus.FS = 01
        csrc    mstatus, t1
        csrs    mstatus, t2
    csrrc   x0, fflags, t5

        // clear csr
        csrrw x0, fflags, x0
        // Write to fflags when mstatus.FS = 10
        csrc    mstatus, t1
        csrs    mstatus, t3
    csrrc   x0, fflags, t5

        // clear csr
        csrrw x0, fflags, x0
        // Write to fflags when mstatus.FS = 11
        csrs    mstatus, t1
    csrrc   x0, fflags, t5

    // Compute walking pattern:
    slli     t5, t5, 1      // (walking one)
    bnez     t5, fflagswalk_loop   // Loop until t5 is shifted past XLEN

    // Restore the original fflags
    csrrw   x2, fflags, s0

///////////////////////
//csr_fflags_set_m_*
///////////////////////

    // Set up clear/set mask for mstatus.FS (bits 13 and 14)
    li      t1, 0x6000
    // Set up init mask for mstatus.FS (FS = 01)
    li      t2, 0x2000
    // Set up clean mask for mstatus.FS (FS = 10)
    li      t3, 0x4000

 // Set mstatus.FS to 11 to enable fp for initialization
    csrs mstatus, t1

    // Initialize floating point registers used

    // zero
    li t0, 0
    fcvt.s.w f0, t0

    // one
    li t0, 1
    fcvt.s.w f1, t0

    // three
    li t0, 3
    fcvt.s.w f3, t0

    // infinity          (single precision)
    li t0, 0x7f800000
    fmv.s.x f4, t0

    // smallest fp value (single precision)
    li t0, 0x00800000
    fmv.s.x f5, t0

    // largest fp value  (single precision)
    li t0, 0x7f7fffff
    fmv.s.x f6, t0

// Test when mstatus.FS = 00
        // mstatus.FS = 00
        csrc    mstatus, t1

    //inf – inf sets invalid flag
    fsub.s   f7, f4, f4

        // mstatus.FS = 00
        csrc    mstatus, t1

    // 1/0 sets division by zero flag
    fdiv.s   f8, f1, f0

        // mstatus.FS = 00
        csrc    mstatus, t1

    // largest + largest sets overflow flag
    fadd.s   f9, f6, f6

        // mstatus.FS = 00
        csrc    mstatus, t1

    // smallest * smallest sets underflow flag
    fmul.s   f10, f5, f5

        // mstatus.FS = 00
        csrc    mstatus, t1

    // 1/3 sets inexact flag
    fdiv.s   f11, f1, f3

// Test when mstatus.FS = 01
        // mstatus.FS = 01
        csrc    mstatus, t1
        csrs    mstatus, t2

    //inf – inf sets invalid flag
    fsub.s   f7, f4, f4

        // mstatus.FS = 01
        csrc    mstatus, t1
        csrs    mstatus, t2

    // 1/0 sets division by zero flag
    fdiv.s   f8, f1, f0

        // mstatus.FS = 01
        csrc    mstatus, t1
        csrs    mstatus, t2

    // largest + largest sets overflow flag
    fadd.s   f9, f6, f6

        // mstatus.FS = 01
        csrc    mstatus, t1
        csrs    mstatus, t2

    // smallest * smallest sets underflow flag
    fmul.s   f10, f5, f5

        // mstatus.FS = 01
        csrc    mstatus, t1
        csrs    mstatus, t2

    // 1/3 sets inexact flag
    fdiv.s   f11, f1, f3

// Test when mstatus.FS = 10
        // msstatus.FS = 10
        csrc    mstatus, t1
        csrs    mstatus, t3

    // inf – inf sets invalid flag
    fsub.s   f7, f4, f4

        // mstatus.FS = 10
        csrc    mstatus, t1
        csrs    mstatus, t3

    // 1/0 sets division by zero flag
    fdiv.s   f8, f1, f0

        // mstatus.FS = 10
        csrc    mstatus, t1
        csrs    mstatus, t3

    // largest + largest sets overflow flag
    fadd.s   f9, f6, f6

        // mstatus.FS = 10
        csrc    mstatus, t1
        csrs    mstatus, t3

    // smallest * smallest sets underflow flag
    fmul.s   f10, f5, f5

        // msstatus.FS = 10
        csrc    mstatus, t1
        csrs    mstatus, t3

    // 1/3 sets inexact flag
    fdiv.s   f11, f1, f3

// Test when mstatus.FS = 11
        // mstatus.FS = 11
        csrs    mstatus, t1

    // inf – inf sets invalid flag
    fsub.s   f7, f4, f4

        // mstatus.FS = 11
        csrs    mstatus, t1

    // 1/0 sets division by zero flag
    fdiv.s   f8, f1, f0

        // mstatus.FS = 11
        csrs    mstatus, t1

    // largest + largest sets overflow flag
    fadd.s   f9, f6, f6

        // mstatus.FS = 11
        csrs    mstatus, t1

    // smallest * smallest sets underflow flag
    fmul.s   f10, f5, f5
        // mstatus.FS = 11
        csrs    mstatus, t1

    // 1/3 sets inexact flag
    fdiv.s   f11, f1, f3

/////////////////////////////
//cp_mstatus_FS_transition
/////////////////////////////
    // Test floating point instructions function with:
    // mstatus.FS = 0
    li  a0, 0
    jal ra, fp_instructions

    // Test floating point instructions function with:
    // mstatus.FS = 1
    li  a0, 1
    jal ra, fp_instructions

    // Test floating point instructions function with:
    // mstatus.FS = 2
    li  a0, 2
    jal ra, fp_instructions

    // Test floating point instructions function with:
    // mstatus.FS = 3
    li  a0, 3
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
// These instructions are executed with different mstatus.FS values.
//
// a0: Sets value of mstatus.FS (ranges from 0-3; Off, Initial, Clean, and Dirty respectively).
//    When a fp register is modified mstatus.FS is marked as dirty automatically. To test fp instructions
//    with different mstatus.FS values, mstatus.FS is updated to the value in a0 before each fp instruction.
fp_instructions:

    // Set up clear mask for mstatus.FS
    li s1, 0x6000      // (1's in bit 13 and 14 of mstatus)

    // Set mstatus.FS to 10 to enable fp for initialization
    li t0,0x4000
    csrs mstatus, t0

    // Set frm to a legal value for initialization
    csrw frm, 0
    li a1, 0    //store the value of frm for restoring after each csrrw/csrrc instruction

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

    // Test a non-fp instruction (should not change mstatus.FS to dirty)
    li t0, 1
    li t1, 2
    add t0, t0, t1

    // --- Floating-Point Memory Operations ---

    // write a0 to mstatus.FS
    csrc mstatus, s1
    csrs mstatus, s2
    fsw    f0, 0(a4)

    // write a1 to mstatus.FS
    csrc mstatus, s1
    csrs mstatus, s2
    flw    f1, 0(a4)

    // --- Floating-Point Arithmetic Operations ---
        // write a1 to mstatus.FS
    csrc mstatus, s1
    csrs mstatus, s2
    fadd.s f2, f0, f1

    // write a1 to mstatus.FS
    csrc mstatus, s1
    csrs mstatus, s2
    fsub.s f3, f0, f1

    // write a1 to mstatus.FS
    csrc mstatus, s1
    csrs mstatus, s2
    fmul.s f4, f0, f1

    // write a1 to mstatus.FS
    csrc mstatus, s1
    csrs mstatus, s2
    fdiv.s f5, f0, f1

    // --- Floating‑Point Conversions ---

        // write a1 to mstatus.FS
    csrc mstatus, s1
    csrs mstatus, s2
    fcvt.w.s t2, f0

    // write a1 to mstatus.FS
    csrc mstatus, s1
    csrs mstatus, s2
    fcvt.s.w f6, t2

    // write a1 to
    #ifdef D_SUPPORTED
        csrc mstatus, s1
        csrs mstatus, s2
        fcvt.s.d f7, f0
    #endif
    // --- Floating Point Arithmetic ---

    // write a1 to mstatus.FS
    csrc mstatus, s1
    csrs mstatus, s2
    fmadd.s f8, f0, f1, f2

    // write a1 to mstatus.FS
    csrc mstatus, s1
    csrs mstatus, s2
    fsqrt.s f9, f0

    // write a1 to mstatus.FS
    csrc mstatus, s1
    csrs mstatus, s2
    fsgnj.s f10, f0, f1

    // write a1 to mstatus.FS
    csrc mstatus, s1
    csrs mstatus, s2
    feq.s  t3, f0, f1

    // --- Move Bit Representations ---
    // write a1 to mstatus.FS
    csrc mstatus, s1
    csrs mstatus, s2
    fmv.x.w t4, f0

    // write a1 to mstatus.FS
    csrc mstatus, s1
    csrs mstatus, s2
    fmv.w.x f11, t4

    // --- Floating‑Point Classification and Minimum ---
    // write a1 to mstatus.FS
    csrc mstatus, s1
    csrs mstatus, s2
    fclass.s t5, f0

    // write a1 to mstatus.FS
    csrc mstatus, s1
    csrs mstatus, s2
    fmin.s f12, f0, f1

    // --- Zfa Extension Instructions ---
    #ifdef ZFA_SUPPORTED
        // write a1 to mstatus.FS
        csrc mstatus, s1
        csrs mstatus, s2
        fround.s f14, f0

    // write a1 to mstatus.FS
        csrc mstatus, s1
        csrs mstatus, s2
        fli.s  f2, 2.5
    #endif
    // --- CSR Operations on Floating‑Point Status Registers ---

    // Note for the following csrrw and  csrrc instructions:
    // Since fcsr, frm, and fflags are part of the same csr, frm is restored after each
    // csrrw/csrrc instruction. This prevents accidental modification of the frm register.

    // write a1 to mstatus.FS
    csrc mstatus, s1
    csrs mstatus, s2
    csrrw  t1, fcsr, x0

    // Restore frm
    csrw frm, a1
    // write a1 to mstatus.FS
    csrc mstatus, s1
    csrs mstatus, s2
    csrrw  t0, frm, a1   // a1 stores the value of frm

    // Restore frm
    csrw frm, a1
    // write a1 to mstatus.FS
    csrc mstatus, s1
    csrs mstatus, s2
    csrrw  t1, fflags, x0

    // Restore frm
    csrw frm, a1
    // write a1 to mstatus.FS
    csrc mstatus, s1
    csrs mstatus, s2
    csrrs  t1, fcsr, t1

    // write a1 to mstatus.FS
    csrc mstatus, s1
    csrs mstatus, s2
    csrrs  t1, fflags, t1

    // write a1 to mstatus.FS
    csrc mstatus, s1
    csrs mstatus, s2
    csrrs  t0, frm, a1   // a1 stores the value of frm

    // write a1 to mstatus.FS
    csrc mstatus, s1
    csrs mstatus, s2
    csrrc  t1, fcsr, t1

    // Restore frm
    csrw frm, a1
    // write a1 to mstatus.FS
    csrc mstatus, s1
    csrs mstatus, s2
    csrrc  t1, fcsr, t1

    // Restore frm
    csrw frm, a1
    // write a1 to mstatus.FS
    csrc mstatus, s1
    csrs mstatus, s2
    csrrc  t1, frm, a1   // a1 stores the value of frm

    // Restore frm
    csrw frm, a1
    // write a1 to mstatus.FS
    csrc mstatus, s1
    csrs mstatus, s2
    csrrc  t1, fflags, t1

    // write a1 to mstatus.FS
    csrc mstatus, s1
    csrs mstatus, s2
    csrr t1,  frm

    // write a1 to mstatus.FS
    csrc mstatus, s1
    csrs mstatus, s2
    csrr t1,  fflags

    // write a1 to mstatus.FS
    csrc mstatus, s1
    csrs mstatus, s2
    csrr t1,  fcsr

    // 32-bit only instructions
    #ifdef __riscv_xlen
    #if __riscv_xlen == 32
        // write a1 to mstatus.FS
        csrc mstatus, s1
        csrs mstatus, s2
        fmv.x.w t1, f0

        #ifdef D_SUPPORTED
         // write a1 to mstatus.FS
            csrc mstatus, s1
            csrs mstatus, s2
            fmvh.x.d t2, f0

            // write a1 to mstatus.FS
            csrc mstatus, s1
            csrs mstatus, s2
            fmvp.d.x f1, t1, t2
        #endif
    #endif
    #endif

    ret
