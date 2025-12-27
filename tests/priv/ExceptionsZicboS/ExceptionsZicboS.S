///////////////////////////////////////////
// ExceptionsZicboS.S
//
// Written: Roman De Santos rdesantos@hmc.edu 17 April 2025
//
// Purpose: Functional coverage test for ExceptionsZicbo in S mode
//
// SPDX-License-Identifier: Apache-2.0
///////////////////////////////////////////

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: [I, Zicsr, Sm]
# MARCH: rv${XLEN}ic_zicsr_zicbom_zicboz
# CONFIG_DEPENDENT: true
##### END_TEST_CONFIG #####

.option norvc          # Do not automatically replace uncompressed instructions with compressed instructions

#include "rvtest_config.h"
#include "WALLY-init-lib.h"

main:

// machine cbie test
li a1, 3
jal cbieFunction

// Supervisor cbie test
li a1, 1
jal cbieFunction

// User cbie test
li a1, 0
jal cbieFunction

// Machine cbcfe test
li a1, 3
jal cbcfeFunction

// Supervisor cbcfe test
li a1, 1
jal cbcfeFunction

// User cbcfe test
li a1, 0
jal cbcfeFunction

// Machine cbze test
li a1, 3
jal cbzeFunction

// Supervisor cbze test
li a1, 1
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
// Tests cbo.inval with all possible combinations of cbze in the menvcfg and senvcfg csr.
// Program returns in privilege mode specified by a1.
//
// a1: Sets the privilege mode to test (0 = user, 1 = supervisor, 3 = machine).
cbieFunction:
    la t4, DataBlock       // load address of cache testing data block

    li      t6, 4          // outer and inner loop limit
    li      s0, 0          // s0 = i = 0  (outer loop counter)
outerCbieLoop:
    li      s1, 0          // s1 = j = 0  (inner loop counter)

innerCbieLoop:
    // change into machine mode
    li   a0, 3
    ecall

    // update csr {m/s}cbie
    slli  t2, s0, 4
    csrw  menvcfg, t2    // bits 4 and 5 of csr menvcfg

    slli t3, s1, 4
    csrw senvcfg, t3     // bits 4 and 5 of senvcfg

    // run test in desired privilege mode
    mv a0,a1
    ecall

    // execute cbo instruction in a temp data block
    #ifdef ZICBOM_SUPPORTED
        cbo.inval    0(t4)
    #endif

    // advance inner counter j
    addi    s1, s1, 1               // j++
    blt     s1, t6, innerCbieLoop   // while (j < 4) continue inner loop

    // advance outer counter i
    addi    s0, s0, 1               // i++
    blt     s0, t6, outerCbieLoop   // while (i < 4) repeat outer loop

    ret

// Function: cbcfeFunction
// Tests cbo.clean and cbo.flush with all possible combinations of cbcfe in the menvcfg and senvcfg csr.
// Program returns in privilege mode specified by a1.
//
// a1: Sets the privilege mode to test (0 = user, 1 = supervisor, 3 = machine).
cbcfeFunction:
    la t4, DataBlock       // load address of cache testing data block

    li      t6, 2          // outer and inner loop limit
    li      s0, 0          // s0 = i = 0  (outer loop counter)

outerCbcfeLoop:
    li      s1, 0          // s1 = j = 0  (inner loop counter)

innerCbcfeLoop:
    // change into machine mode
    li   a0, 3
    ecall

    // update csr {m/s}cbcfe
    slli  t2, s0, 6
    csrw  menvcfg, t2    // bit 6 of csr menvcfg

    slli t3, s1, 6
    csrw senvcfg, t3     // bit 6 of senvcfg

    // run test in desired privilege mode
    mv a0,a1
    ecall

    // execute cbo instruction in a temp data block
    #ifdef ZICBOM_SUPPORTED
        cbo.clean    0(t4)
        cbo.flush    0(t4)
    #endif

    // advance inner counter j
    addi    s1, s1, 1                // j++
    blt     s1, t6, innerCbcfeLoop   // while (j < 2) continue inner loop

    // advance outer counter i
    addi    s0, s0, 1                // i++
    blt     s0, t6, outerCbcfeLoop   // while (i < 2) repeat outer loop

    ret

// Function: cbzeFunction
// Tests cbo.zero with all possible combinations of cbze in the menvcfg and senvcfg csr.
// Program returns in privilege mode specified by a1.
//
// a1: Sets the privilege mode to test (0 = user, 1 = supervisor, 3 = machine).
cbzeFunction:
    la t4, DataBlock       // load address of cache testing data block

    li      t6, 2          // outer and inner loop limit
    li      s0, 0          // s0 = i = 0  (outer loop counter)
outerCbzeLoop:
    li      s1, 0          // s1 = j = 0  (inner loop counter)

innerCbzeLoop:
    // change into machine mode
    li   a0, 3
    ecall

    // update csr {m/s}cbze
    slli  t2, s0, 7
    csrw  menvcfg, t2    //bit 7 of menvcfg csr

    slli t3, s1, 7
    csrw senvcfg, t3     // bit 7 of senvcfg csr

    // run test in desired privilege mode
    mv a0, a1
    ecall

    // execute cbo instruction in a temp data block
    #ifdef ZICBOZ_SUPPORTED
        cbo.zero    0(t4)
    #endif

    // advance inner counter j
    addi    s1, s1, 1               // j++
    blt     s1, t6, innerCbzeLoop   // while (j < 4) continue inner loop

    // advance outer counter i
    addi    s0, s0, 1               // i++
    blt     s0, t6, outerCbzeLoop   // while (i < 4) repeat outer loop

    ret

// Scratch data area for cache operations.
// Larger than any reasonable cache line to prevent
// accidental clearing of program data.
.data
.align 10
DataBlock:
    .fill  2048
