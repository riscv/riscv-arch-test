///////////////////////////////////////////
// ExceptionsZc.S
//
// Written: Roman De Santos rdesantos@hmc.edu 28 February 2025
//
// Purpose: Code coverage test for ExceptionsZc in M mode
//
// SPDX-License-Identifier: Apache-2.0
///////////////////////////////////////////

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: [I, Zicsr, Zca, Sm]
# MARCH: rv${XLEN}ic_zicsr_zca_zcb_zcd
# CONFIG_DEPENDENT: true
##### END_TEST_CONFIG #####


 #include "rvtest_config.h"
 #include "WALLY-init-lib.h"

 main:
    # set mstatus.FS to 01 to enable fp
    li t0,0x4000
    csrs mstatus, t0


/////////////////////////////////
//cp_load_address_misaligned
/////////////////////////////////

    // Set up a pointers to scratch memory.
    la      a4, scratch
    la      sp, scratch

    //Store a value to the scratch memory
    li     t1, 0xDEADBEEF
    sw     t1, 0(a4)
    sw     t1, 4(a4)
    sw     t1, 8(a4)
    sw     t1, 12(a4)

    //Loop over all 3-bit offsets (0..7)
    # These instructions use a base register (a2) plus a register offset.
    li      t0, 0         # loop index (offset 0..7)
    li      t5, 8         # loop limit


misaligned_loop:

    add     a2, a4, t0    # a2 = sctach + offset
    // Test compressed integer load instructions:
    c.lw    a3, 0(a2)     # compressed load word

    //Test hardware specific compressed load instructions
    #if __riscv_xlen == 64
        c.ld    a3, 0(a2)     # compressed load doubleword (RV64 only)
    #endif

    #ifdef ZCB_SUPPORTED
        c.lh    a3, 0(a2)     # compressed load halfword
        c.lhu   a3, 0(a2)     # compressed load halfword unsigned
        c.lbu   a3, 0(a2)     # compressed load byte unsigned
    #endif

    #ifdef ZCF_SUPPORTED
        c.flw   f9, 0(a2)    # compressed load floating-point word
    #endif

    #ifdef ZCD_SUPPORTED
        //Test shared compressed load floating instruction
        c.fld   f9, 0(a2)    # compressed load floating-point doubleword
    #endif

    #------------------------
    # Now test the _sp forms.
    c.lwsp  a3, 0(sp)

    #if __riscv_xlen == 64
        c.ldsp  a3, 0(sp)
    #endif

    #ifdef ZCF_SUPPORTED
        # Compressed load floating-point word from sp:
        c.flwsp f9, 0(sp)
    #endif

    #ifdef ZCD_SUPPORTED
        c.fldsp f9, 0(sp) # Compressed load floating-point doubleword from sp
    #endif


/////////////////////////////////
//cp_store_address_misaligned
/////////////////////////////////

    //load a test value into f8
    la      t1, scratch
    #ifdef ZCF_SUPPORTED
        flw    f8, 0(t1)
    #endif

    li a3,  0xDEADBEEF

    // Test compressed integer store instructions:
    c.sw    a3, 0(a2)     # compressed store word

    #platform dependent store instructions
    #if __riscv_xlen == 64
        c.sd    a3, 0(a2)     # compressed store doubleword (RV64 only)
    #endif

    #ifdef ZCB_SUPPORTED
        c.sh    a3, 0(a2)     # compressed store halfword
        c.sb    a3, 0(a2)
    #endif

    #ifdef ZCF_SUPPORTED
        c.fsw   f8, 0(a2)    # compressed store floating-point word
    #endif

    #ifdef ZCD_SUPPORTED
        //Test shared compressed store floating instruction
        c.fsd   f8, 0(a2)    # compressed store floating-point doubleword
    #endif

    #------------------------
    // Now test the _sp forms.
    c.swsp  a3, 0(sp)

    #if __riscv_xlen == 64
        c.sdsp  a3, 0(sp)
    #endif

    #ifdef ZCF_SUPPORTED
        c.fswsp f8, 0(sp)
    #endif

    #ifdef ZCD_SUPPORTED
        c.fsdsp f8, 0(sp)
    #endif

    //update loop
    addi    sp, sp, 1     #increment the sp offset
    addi    t0, t0, 1  #increment the loop index
    blt     t0, t5, misaligned_loop


/////////////////////////////////
//cp_load_access_fault
/////////////////////////////////

    // Load the illegal address into registers
    li      a2, ACCESS_FAULT_ADDRESS
    la      sp, ACCESS_FAULT_ADDRESS

    c.lw  a3, 0(a2)

    #platform dependent load instructions
    #if __riscv_xlen == 64
        c.ld a3, 0(a2)   // Load doubleword (compressed)
    #endif

    #ifdef ZCB_SUPPORTED
        //Compressed load instructions for rv32 and rv64
        c.lbu a3, 0(a2)
        c.lh  a3, 0(a2)
        c.lhu a3, 0(a2)
        c.lbu a3, 0(a2) //load byte
    #endif

    #ifdef ZCF_SUPPORTED
        c.flw   f9, 0(a2)       // Compressed floating-point load word
        c.flwsp f9, 0(sp)       // Compressed floating-point load word from sp
    #endif

    #ifdef ZCD_SUPPORTED
        //Test shared compressed floating instruction
        c.fld   f9, 0(a2)    # compressed load floating-point doubleword
        c.fldsp f9, 0(sp)       // Compressed floating-point load doubleword from sp
    #endif

    #------------------------
    # Now test the _sp forms.
    //Stack pointer variants:
    c.lwsp  a3, 0(sp)       // Compressed load word using stack-pointer offset

    #platform dependent load instructions
    #if __riscv_xlen == 64
        c.ldsp  a3, 0(sp)       // Compressed load doubleword using stack-pointer offset
    #endif

    #ifdef ZCF_SUPPORTED
        c.flwsp f9, 0(sp)       // Compressed floating-point load word from sp
    #endif

    #ifdef ZCD_SUPPORTED
        //Test shared compressed floating instruction
        c.fldsp f9, 0(sp)       // Compressed floating-point load doubleword from sp
    #endif


/////////////////////////////////
//cp_store_access_fault
/////////////////////////////////

    // Load the illegal address into registers
    li      a2, ACCESS_FAULT_ADDRESS
    la      sp, ACCESS_FAULT_ADDRESS

    // Test compressed integer load instructions:
    c.sw    a3, 0(a2)     # compressed store word

    #platform dependent load instructions
    #if __riscv_xlen == 64
        c.sd    a3, 0(a2)     # compressed load doubleword (RV64 only)
    #endif

    #ifdef ZCB_SUPPORTED
        c.sh    a3, 0(a2)     # compressed store halfword
        c.sb    a3, 0(a2)
    #endif

    //Test shared compressed floating instruction
    #ifdef ZCF_SUPPORTED
        c.fsw   f8, 0(a2)    # compressed load floating-point word
    #endif

    #ifdef ZCD_SUPPORTED
        c.fsd   f8, 0(a2)    # compressed load floating-point doubleword
    #endif

    #------------------------
    # Now test the _sp forms.
    c.swsp  a3, 0(sp)

    #if __riscv_xlen == 64
        c.sdsp  a3, 0(sp)
    #endif

    #ifdef ZCF_SUPPORTED
        c.fswsp f8, 0(sp)
    #endif

    #ifdef ZCD_SUPPORTED
        c.fsdsp f8, 0(sp)
    #endif


/////////////////////////////////
//cp_ebreak
////////////////////////////////
    c.ebreak


finished:
    j done
