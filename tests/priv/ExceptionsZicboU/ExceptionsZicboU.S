///////////////////////////////////////////
// ExceptionsZicboU.S
//
// Written: Roman De Santos rdesantos@hmc.edu 17 April 2025
//
// Purpose: Functional coverage test for ExceptionsZicbo in U mode
//
// SPDX-License-Identifier: Apache-2.0
///////////////////////////////////////////

##### START_TEST_CONFIG #####
# implemented_extensions: [I, U, Zicsr, Zicbom, Zicboz]
# MARCH: rv${XLEN}i_zicsr_zicbom_zicboz
# CONFIG_DEPENDENT: true
##### END_TEST_CONFIG #####


#include "WALLY-init-lib.h"

main:

// machine cbie test
li a1, 3
jal cbieFunction

// user cbie test
li a1, 0
jal cbieFunction

// Machine cbcfe test
li a1, 3
jal cbcfeFunction

// User cbcfe test
li a1, 0
jal cbcfeFunction

// Machine cbze test
li a1, 3
jal cbzeFunction

// User cbze test
li a1, 0
jal cbzeFunction

finished:
    j done


////////////////
// Helper functions
////////////////

// Function: cbieFunction
// Tests cbo.inval with all possible combinations of cbie in the menvcfg csr.
// Program returns in privilege mode specified by a1.
//
// a1: Sets the privilege mode to test (0 = user, 1 = supervisor, 3 = machine).
cbieFunction:
    la t4, DataBlock       // load address of cache testing data block

    li      t6, 4          // loop limit
    li      s0, 0          // s0 = i = 0  (loop counter)

cbieLoop:

    // switch to machine priv mode
    li   a0, 3
    ecall

    // shift i to bits 4-5 of menvcfg (cbie value)
    slli  t1, s0, 4
    csrw  menvcfg, t1

    // switch back to requested priv mode
    mv a0,a1
    ecall

    // execute cbo instruction in a temp data block
    cbo.inval    0(t4)

    // loop update
    addi    s0, s0, 1
    blt     s0, t6, cbieLoop

    ret


// Function: cbcfeFunction
// Tests cbo.clean and cbo.flush with all possible combinations of cbcfe in the menvcfg csr.
// Program returns in privilege mode specified by a1.
//
// a1: Sets the privilege mode to test (0 = user, 1 = supervisor, 3 = machine).
cbcfeFunction:
    la t4, DataBlock       // load address of cache testing data block

    li      t6, 2          // loop limit
    li      s0, 0          // s0 = i = 0  (loop counter)

cbcfeLoop:

    // load into machine mode
    li   a0, 3
    ecall

    // update csr cbcfe
    slli  t1, s0, 6
    csrw  menvcfg, t1    //bit 6 of csr menvcfg

    // run test in desired privilege mode
    mv a0,a1
    ecall

    // execute cbo instruction in a temp data block
    cbo.clean    0(t4)
    cbo.flush    0(t4)


    // loop update
    addi    s0, s0, 1          # i++
    blt     s0, t6, cbcfeLoop   # while (i < 2) repeat outer loop

    ret


// Function: cbzeFunction
// Tests cbo.zero with all possible combinations of cbze in the menvcfg csr.
// Program returns in privilege mode specified by a1.
//
// a1: Sets the privilege mode to test (0 = user, 1 = supervisor, 3 = machine).
cbzeFunction:
    la t4, DataBlock       // load address of cache testing data block

    li      t6, 2          // loop limit
    li      s0, 0          // s0 = i = 0  (loop counter)

cbzeLoop:

    // load into machine mode
    li   a0, 3
    ecall

    // update csr cbze
    slli  t1, s0, 7
    csrw  menvcfg, t1    // bit 7 csr menvcfg

    // run test in desired privilege mode
    mv a0,a1
    ecall

    // execute cbo instruction in a temp data block
    cbo.zero    0(t4)

    // loop update
    addi    s0, s0, 1          // i++
    blt     s0, t6, cbzeLoop   // while (i < 2) repeat

    ret


// Scratch data area for cache operations.
// Larger than any reasonable cache line to prevent
// accidental clearing of program data.
.data
.align 10
DataBlock:
    .fill  2048
