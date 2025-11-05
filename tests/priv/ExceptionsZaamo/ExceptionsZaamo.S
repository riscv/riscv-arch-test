///////////////////////////////////////////
// ExceptionsZaamo.S
//
// Written: Roman De Santos rdesantos@hmc.edu 31 March 2025
//
// Purpose: Functional coverage test for Exceptions from the Zaamo Extension
//
// SPDX-License-Identifier: Apache-2.0
///////////////////////////////////////////

##### START_TEST_CONFIG #####
# implemented_extensions: [I, Zicsr, Zaamo]
# MARCH: rv${XLEN}ia_zicsr
# CONFIG_DEPENDENT: true
##### END_TEST_CONFIG #####

#include "WALLY-init-lib.h"

main:

/////////////////////////////////
//cp_load_address_misaligned
/////////////////////////////////

// Test values 0-7 as the LSB for rs1 of the AMO instructions

    li   a2, 0         // loop counter
    li   a3, 8         // loop limit
loop:

    // Call the Zaamo_Instructions function
    // a2 = misalignment value, No instruction access fault (a1 = 0)
    mv  a0, a2
    li  a1, 0
    jal Zaamo_Instructions

    addi a2, a2, 1      // Increment loop counter by 1
    blt  a2, a3, loop   // If a2 is less than 8, branch back to 'loop'

/////////////////////////////////
//cp_load_access_fault
/////////////////////////////////

    // Call the Zaamo_Instructions function
    // No missalignment (a2 = 0),
    // Enable Instruction access fault (a1 = 1)
    li  a0, 0
    li  a1, 1
    jal Zaamo_Instructions

finished:
    j done

// Function: Zaamo_Instructions
// Purpose: Tests the atomic memory operations (AMOs) in RISC-V.
// The function performs a series of atomic memory operations from the Zaamo extension
//
// The function takes two arguments:
// a0: The misalignment value of rs1.
// a1: A flag indicating whether to load the Access Fault address.

Zaamo_Instructions:
    //initialize scratch memory
    la      t0, scratch

    li      t1, 0xDEADBEEF

    sw      t1, 0(t0)
    sw      t1, 4(t0)
    sw      t1, 8(t0)
    sw      t1, 12(t0)

    // Update scratch address to be misaligned based a0 argument
    add t0, a0, t0

    // If testing for an instruction
    // load the Access Fault address to the base address
    li t1, 1
    bne a1, t1, skipIAF
    li    t0, ACCESS_FAULT_ADDRESS

 skipIAF:

    amoswap.w t2, t1, (t0)

    amoadd.w t3, t2, (t0)

    amoxor.w t4, t3, (t0)

    amoand.w t5, t4, (t0)

    amoor.w t6, t5, (t0)

    amomin.w t1, t6, (t0)

    amomax.w t2, t1, (t0)

    amominu.w t3, t2, (t0)

    amomaxu.w t4, t3, (t0)

    // Test Rv64 AMO instructions
    #ifdef __riscv_xlen
        #if __riscv_xlen == 64
            amoswap.d t2, t1, (t0)

            amoadd.d t3, t2, (t0)

            amoxor.d t4, t3, (t0)

            amoand.d t5, t4, (t0)

            amoor.d t6, t5, (t0)

            amomin.d t1, t6, (t0)

            amomax.d t2, t1, (t0)

            amominu.d t3, t2, (t0)

            amomaxu.d t4, t3, (t0)
        #endif
    #endif

    ret
