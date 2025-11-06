///////////////////////////////////////////
// ExceptionsZalrsc.S
//
// Written: Roman De Santos rdesantos@hmc.edu 1 April 2025
//
// Purpose: Functional coverage test for Zalrsc extension Exceptions
//
// SPDX-License-Identifier: Apache-2.0
///////////////////////////////////////////

##### START_TEST_CONFIG #####
# implemented_extensions: [I, Zicsr, Zalrsc]
# MARCH: rv${XLEN}ia_zicsr
# CONFIG_DEPENDENT: true
##### END_TEST_CONFIG #####

#include "WALLY-init-lib.h"

main:

////////////////////////////////////////////////////////////////
//cp_load_address_misaligned AND cp_store_address_misaligned
////////////////////////////////////////////////////////////////

// Test values 0-7 as the LSB for rs1 when lw.x/sc.x is executed

    li   a0, 0         // loop counter (also the misalignment value)
    li   a3, 8         // loop limit
loop:

    // Call the atomic_instr function
    // a0 = misalignment value (loop counter), No instruction access fault (a1 = 0)
    li  a1, 0
    jal atomic_instr

    // loop update
    addi a0, a0, 1      // Increment loop counter by 1
    blt  a0, a3, loop


//////////////////////////////////////////////////////////////////
//cp_load_address_access_fault AND cp_store_address_access_fault
//////////////////////////////////////////////////////////////////
    // Call the atomic_instr function
    // No misalignment a2 = 0, instruction access fault (a1 = 1)
    li  a0, 0
    li  a1, 1
    jal atomic_instr

////////////////////////
//cp_misaligned_priority
////////////////////////

    // Call the atomic_instr function
    // Enable misalignment a2 = 1, enable instruction access fault (a1 = 1)
    li  a0, 1
    li  a1, 1
    jal atomic_instr


finished:
    j done

// Function: atomic_instr
// Purpose: Tests the lr.x and sc.x instructions from the Zalsc extension.
// This function tests misaligned and access fault addresses with lr.x and sc.x.
//
// The function takes two arguments:
// a0: The misalignment value of rs1.
// a1: A flag indicating whether to load the Access Fault address.
//     If this flag is enabled the address tested will be (Access Fault Address + a0).
atomic_instr:

    // Initialize scratch memory
    la      t0, scratch

    li      t1, 0xDEADBEEF

    sw      t1, 0(t0)
    sw      t1, 4(t0)
    sw      t1, 8(t0)
    sw      t1, 12(t0)

    // Load the Access Fault address if enabled
    li  t1, 1
    bne a1, t1, skipIAF

    li  t0, ACCESS_FAULT_ADDRESS

 skipIAF:
    // Update scratch/Instruction fault address to be misaligned based on a0 argument
    add t0, a0, t0

    // Attempt an sc.w with the same address as lr.w
    lr.w   t4, (t0)        // Load the current 32-bit value from the memory address in a0,

    addi   t4, t4, 2       // Update loaded value

    // Note the test is better than the cover point. With our current toolflow
    // Testing that the rs1 value of the previous lr.x matches the rs1 of the sc.x
    // is not possible.
    // As a proxy we can check that the rd value changes as expected for rd when an
    // sc.x instruction is executed. Load rd with a value > 1.
    // Faulting instructions should not modify this value
    // Succesful instructions modify rd to be 0

    li t2, 2

    sc.w   t2, t4, (t0)    // Attempt to store the value back to the memory address in a0.

    // Attempt a sc.w out of reservation range
    addi    t4, t4, 2     // update value to distinguish from previous sc.w

    // Increment address to be outside of reserved range
    li t3, 4000
    add t1, t0, t3

    lr.w   t4, (t0)


    // Test Rv64 AMO instructions
    #ifdef __riscv_xlen
        #if __riscv_xlen == 64

            // Attempt an sc.d with the same address as lr.d
            lr.d   t4, (t0)        // Load the current 32-bit value from the memory address in a0,

            addi   t4, t4, 2       // Update loaded value

            // Load rd with a value > 1.
            // Faulting instructions should not modify this value
            // Succesful instructions modify rd to be 0

            li t2, 2

            sc.d   t2, t4, (t0)    // Attempt to store the value back to the memory address in a0.

            // Attempt a sc.d out of reservation range
            addi    t4, t4, 2     // update value to distinguish from previous sc.d

            // Increment address to be outside of reserved range
            li t3, 4000
            add t1, t0, t3

            lr.d   t4, (t0)

            sc.d   t2, t4, (t1)   // address in t0 from previous lr.d is significantly different from t1
        #endif
    #endif



    ret
