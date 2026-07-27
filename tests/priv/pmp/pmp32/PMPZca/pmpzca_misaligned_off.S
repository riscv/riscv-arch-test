// ---------------------------------------------------------------------------
// Copyright (C) 2025 Harvey Mudd College & Oklahoma State University, UET Lahore, Habib University
// SPDX-License-Identifier: Apache-2.0
//
// Title        : Comprehensive PMP (Physical Memory Protection) Verification
// Authors      : Umer Shahid, Allen Baum, David Harris
//                Muhammad Abdullah, Hamza Ali, Muhammad Zain
//
// Description : This test verifies the functionality and enforcement of
//               Physical Memory Protection (PMP) configurations in RISC-V
//               systems. It specifically tests the Read, Write, and Execute
//               permissions for a designated memory region, ensuring that
//               the PMP settings are correctly applied and that the system
//               behaves as expected when accessing this region.
//
//
// Coverpoints : cp_misaligned_off for PMPZca is partially covered
//               in this test file.
//
// Test Cases  : Check that misaligned 32-bit fetches that cross a OFF PMP boundary fail.
//               Setting up 3 standard consecutive OFF PMP regions with L=1, XWR=111
//               (XWR = 000 for region 3).Place an uncompressed ret = jalr straddling the
//               start and end of the second regions. Attempt jalr to each ret.
//
// ---------------------------------------------------------------------------
##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: ['I','Zca','Sm']
# params:
#   MXLEN: 32
#   NUM_PMP_ENTRIES: '>0'
# MARCH: rv32i_zca_zicsr_zifencei
##### END_TEST_CONFIG #####

// Define the size of the signature region
#define SIGUPD_COUNT 50




// Include framework macros
#include "riscv_arch_test.h"

// Set up test environment and declare main entry point
RVTEST_BEGIN

#if UDB_PMP_GRANULARITY > 3
  #define NAPOT_REGION_SIZE         (1 << (UDB_PMP_GRANULARITY))
#else
  #define NAPOT_REGION_SIZE         (1 << (UDB_PMP_GRANULARITY + 1))
#endif


main:
    // Loop to SET ALL pmpcfg REGs to zero
    .set pmpcfgi, CSR_PMPCFG0
    .rept UDB_NUM_PMP_ENTRIES/4
    csrw pmpcfgi , x0
    .set pmpcfgi, pmpcfgi+1
    .endr

    // Loop to SET ALL pmpaddr REGs to zero
    .set pmpaddri, CSR_PMPADDR0
    .rept UDB_NUM_PMP_ENTRIES
    csrw pmpaddri, x0
    .set pmpaddri, pmpaddri+1
    .endr

#define PMP0CFG             ((((PMP_L|PMP_R|PMP_W|PMP_X         )&0xFF) << PMP0_CFG_SHIFT))
#define PMP1CFG             ((((PMP_L|PMP_R|PMP_W|PMP_X         )&0xFF) << PMP1_CFG_SHIFT))
#define PMP2CFG             ((((PMP_L|PMP_R|PMP_W|PMP_X         )&0xFF) << PMP2_CFG_SHIFT))

#define REGIONSTART         TEST_FOR_EXECUTION_1
#define NEWREGION1          (REGIONSTART)
#define NEWREGION2          (REGIONSTART+NAPOT_REGION_SIZE)
#define NEWREGION3          (REGIONSTART+(2*NAPOT_REGION_SIZE))

    RVTEST_PMP_SET_BACKGROUND x4

//                                          Verification Section
// Test Case: Setting up 3 OFF regions with LWXR = 1111

    LA(x5, NEWREGION1)
    srl x5, x5, PMP_SHIFT  // This will create dynamic PMP_ADDRESS_0
    csrw pmpaddr0, x5

    LA(x5, NEWREGION2)
    srl  x5, x5, PMP_SHIFT  // This will create dynamic PMP_ADDRESS_1
    csrw pmpaddr1, x5

    LA(x5, NEWREGION3)
    srl x5, x5, PMP_SHIFT  // This will create dynamic PMP_ADDRESS_2
    csrw pmpaddr2, x5

    LI(x4, PMP0CFG|PMP1CFG|PMP2CFG)
    csrw pmpcfg0, x4

    // Test Case 1: Uncompressed return straddling the start of 2nd region
    PMP_VERIFICATION_X_C TEST_FOR_EXECUTION_2, test_1

    // Test Case 2: Uncompressed return straddling the end of 2nd region
    PMP_VERIFICATION_X_C TEST_FOR_EXECUTION_4, test_2

    j exit                                                      // Verification Complete, exit the test


exit:

RVTEST_CODE_END
RVTEST_DATA_BEGIN
.p2align 4

// Test case strings for reporting
test_1_str: .string "\"test: 1; cp: pmpzca_aligned_na4_region_execute\""

.p2align 12
TEST_FOR_EXECUTION_0:
    .rept PMP_NAPOT_REGION_PAD_WORDS                    // NAPOT-safe return fillers: puts TEST_FOR_EXECUTION_1 at PMP_NAPOT_REGION_START
    jalr x0, x1, 0
    .endr

TEST_FOR_EXECUTION_1:
    .rept ((NAPOT_REGION_SIZE / 2) -1)
    c.nop                                                        // 2-byte fillers: precise offsets so _2/_4's uncompressed jalr genuinely straddle the region boundary
    .endr

// No .p2align here (and none before _3/_4 below): the c.nop offsets above must survive
// unrounded so these uncompressed jalr instructions land mid-word, genuinely straddling the
// region boundary, instead of being pushed back onto the next grain-aligned boundary.
TEST_FOR_EXECUTION_2:
    jalr x0, x1, 0                                              //uncompressed return straddling the start of the second region

TEST_FOR_EXECUTION_3:
    .rept ((NAPOT_REGION_SIZE / 2) -2)
    c.nop
    .endr

TEST_FOR_EXECUTION_4:
    jalr x0, x1, 0                                              // Uncompressed return straddling the end of the second region

RETURN_INSTRUCTION:
    nop
    nop
    jr ra                                                       // Get back to the point from where TEST_FOR_EXECUTION was called.


RVTEST_DATA_END

// Signature region for self-checking
RVTEST_SIG_SETUP
