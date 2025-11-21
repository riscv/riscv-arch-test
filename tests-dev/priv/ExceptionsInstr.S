///////////////////////////////////////////
// ExceptionsInstr.S
//
// Written: David_Harris@hmc.edu 26 November 2024
//
// Purpose: Functional coverage tests for illegal instructions
//          Portion of ExceptionsM_coverage
//
// SPDX-License-Identifier: Apache-2.0
///////////////////////////////////////////


#include "WALLY-init-lib.h"

main:

    # set up fast trap handler for uncompressed illegal instructions
    # because these tests will throw a huge number of traps
    # This handler just adds 4 to PC and returns.  It cannot
    # handle other functions, so substitute the normal trap handler
    # at the end of the program

    la t0, trap_handler_returnplus4
    csrw mtvec, t0

    # set mstatus.FS to 01 to enable fp
    li t0,0x4000
    csrs mstatus, t0

    #### ***  fix RV32I imperas.ic to flag unimplemented ShangMi crypto

/////////////////////////////////
// cp_reserved
/////////////////////////////////
    .word 0b00010000000000000000000000001111 # fence with reserved fm
    .word 0b10000000000000000000000000001111 # fence.tso with reserved ordering
    .word 0b00001111111100001000000000001111 # fence with reserved rs1
    .word 0b00001111111100000000000010001111 # fence with reserved rd

/////////////////////////////////
// Test illegal uncompressed instructions
/////////////////////////////////

    #include "ExceptionInstr-Tests.h"

// Test AMO instructions that would be unhappy if accessing random uninitialized memory
    li x1, 0x80000000 # safe place to access; might need to be parameterized if physical memory begins at a different cp_load_address_misaligned

    // exercise every legal flavor of amo.w/d with rs1 = x1

     .word 0b00000101101100001010101010101111
     .word 0b00000011110000001011101010101111
     .word 0b00001110011000001010111110101111
     .word 0b00001000000100001011001000101111
     .word 0b00100010101100001010110110101111
     .word 0b00100011111000001011001110101111
     .word 0b01000110101000001010100010101111
     .word 0b01000110011000001011110010101111
     .word 0b01100111111000001010111100101111
     .word 0b01100000110100001011001010101111
     .word 0b10000100101100001010111010101111
     .word 0b10000101000000001011101010101111
     .word 0b10100000110100001010100000101111
     .word 0b10100111010000001011100000101111
     .word 0b11000100110100001010001000101111
     .word 0b11000110001000001011010100101111
     .word 0b11100110101100001010000010101111
     .word 0b11100110011000001011011100101111

// Restore trap handler before returning

    la t0, trap_handler
    csrw mtvec, t0

finished:
    j done
