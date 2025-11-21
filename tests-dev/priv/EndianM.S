///////////////////////////////////////////
// EndianM.S
//
// Written: David_Harris@hmc.edu 19 November 2024
//
// Purpose: Functional coverage tests for endianness in machine mode
//
// SPDX-License-Identifier: Apache-2.0
///////////////////////////////////////////

##### START_TEST_CONFIG #####
# implemented_extensions: ['I', 'Zicsr', 'NotSupportedInSail']
# params:
#   MXLEN: 32
# MARCH: rv32i_zicsr
# CONFIG_DEPENDENT: false
##### END_TEST_CONFIG #####


#include "WALLY-init-lib.h"
#include "priv-endian.h"
main:

/////////////////////////////////
// Endianness testing
// cp_mstatush_mbe_endianness
// cp_mstatus_mbe_endianness
//
// Goal is to store a pattern to a scratch location in memory
// using each endianness, and stores of every size.  Then
// read back the value using each endianness and loads of
// every size.  Stress that endianness works for every access.
//
// Saving and restoring from the stack is tricky because the
// code must work for both RV32 and RV64, and the endianness
// is constantly changing.  Therefore, we use s6 and s7 (found in priv-endian.h)for
// return addresses instead.
//
// Registers used:
//   s0: saved value of mstatus
//   s1: a 1 in bit 5 to set/clear mstatush.MBE (RV32) or bit 37 to set/clear mstatus.MBE (RV64)
//   s3: scratch address
//   s4: endianness for write test
//   s5: endianness for read test
//   s10: 0 to set/clear sstatus.UBE  (any other value otherwisse )
//   s11: To switch back to running privilege mode once set/clear endianness
/////////////////////////////////
    // save mstatus
    // prep s1 with bits to set/clear MBE for RV32/RV64
    // always do both.  One or the other will trap, but this
    // avoids needing separate code for the two architectures
    // code assumes s registers are saved during these tests
    // saving and restoring mstatus based on endianness
    // calling WALLY-priv-endian.h to store and load

    csrr s0, mstatus    # save CSR
    #ifdef __riscv_xlen
        #if __riscv_xlen == 64
            li s1, 0x2000000000     # 1 in bit 37 for mstatus.MBE
        #elif __riscv_xlen == 32
            li s1, 0x20             # 1 in bit 5 for mstatush.MBE
        #endif
    #else
        ERROR: __riscv_xlen not defined
    #endif
    la s3, scratch  # s3 = pointer to scratch
    li s10, 1
    li s11, 3       #passing privilege mode: machine

    // iterate over each endianness, doing all sizes of stores and loads
    li s4, 0        # endianness for write
    li s5, 0        # endianness for read
    jal s6, endiantest  # test little-endian read and write
    li s4, 1        # endianness for write
    jal s6, endiantest  # test big-endian write, little-endian read
    li s5, 1        # endianness for read
    jal s6, endiantest  # test big-endian read and write
    li s4, 0        # endianness for write
    jal s6, endiantest  # test little-endian write, big-endian read

post_cp_mstatus_mbe_endianness:
    csrrw t6, mstatus, s0    # restore CSR

finished:
    j done
