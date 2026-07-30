// --------------------------------------------------------------------------------
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
// Coverpoints : cp_cfg_A_napot_all for PMPM is fully covered in this test file.
//
// Test Cases  : Checking A=NAPOT works in each region with pmpcfg.L = 1,
//               pmpcfg.A=NAPOT, pmpcfg.XWR=000, standard regions and making lw,
//               sw and jalr at that address, address - 4, and just beyond top
//               of the region. Test file will get reasonably large in size if
//               Grain Index value will increase.
//
// --------------------------------------------------------------------------------


##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS:  ['Sm']
# params:
#   MXLEN: 32
#   NUM_PMP_ENTRIES: '>0'
#   PMP_NAPOT_SUPPORTED: true
# MARCH: rv32i_zicsr_zifencei
##### END_TEST_CONFIG #####

// Define the size of the signature region
#define SIGUPD_COUNT 50


// Include framework macros
#include "riscv_arch_test.h"

// Set up test environment and declare main entry point
RVTEST_BEGIN

#if UDB_PMP_GRANULARITY != 2
  #define g   (1 << (UDB_PMP_GRANULARITY))
#else
  #define g   (1 << (UDB_PMP_GRANULARITY + 1))
#endif


.macro VERIFICATION_RWX ADDRESS, TEST_CASE

    LA(a5, \ADDRESS)                                                            // Address to be verified
    \TEST_CASE\()_1:
    lw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_1, test_1_str)                                   // Signature update

    addi a5, a5, -4
    \TEST_CASE\()_2:
    lw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_2, test_2_str)                                   // Signature update


    LI(t0, g)
    add    a5, a5, t0
    addi a5, a5, 4
    \TEST_CASE\()_3:
    lw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_3, test_3_str)                                   // Signature update

.endm

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

#define PMPREGION0_XWR_000  (((PMP_L|PMP_NAPOT)&0xFF) << PMP0_CFG_SHIFT)
#define PMPREGION1_XWR_000  (((PMP_L|PMP_NAPOT)&0xFF) << PMP1_CFG_SHIFT)
#define PMPREGION2_XWR_000  (((PMP_L|PMP_NAPOT)&0xFF) << PMP2_CFG_SHIFT)
#define PMPREGION3_XWR_000  (((PMP_L|PMP_NAPOT)&0xFF) << PMP3_CFG_SHIFT)

#define REGIONSTART         TEST_FOR_EXECUTION
#if UDB_PMP_GRANULARITY != 2
    #define PMP_MASK            ~((1 << (UDB_PMP_GRANULARITY - 3))-1)
    #define PMP_REGION_SIZE     (1 << (UDB_PMP_GRANULARITY - 3)) - 1
    #define SIZE                (1<<(UDB_PMP_GRANULARITY))
#else
    #define PMP_MASK            ~0
    #define PMP_REGION_SIZE     0
    #define SIZE                (1<<(UDB_PMP_GRANULARITY+1))
#endif

    RVTEST_PMP_SET_BACKGROUND x4

//                                          Verification Section
// Test Case: 1 : L -> 1 and No Permissions given to the PMP Region 14

    LA(x5, REGIONSTART)
    srl x5, x5, PMP_SHIFT
    LI(x6,PMP_MASK)
    and x5, x5, x6
    LI(x6,PMP_REGION_SIZE)
    or x5, x5, x6
    csrw pmpaddr14, x5

    LI(x4, (PMPREGION2_XWR_000))
    csrw pmpcfg3, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_1

// Test Case: 2 : L -> 1 and No Permissions given to the PMP Region 13

    LA(x5, REGIONSTART)
    srl x5, x5, PMP_SHIFT
    LI(x6,PMP_MASK)
    and x5, x5, x6
    LI(x6,PMP_REGION_SIZE)
    or x5, x5, x6
    csrw pmpaddr13, x5

    LI(x4, (PMPREGION1_XWR_000))
    csrw pmpcfg3, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_2

// Test Case: 3 : L -> 1 and No Permissions given to the PMP Region 12

    LA(x5, REGIONSTART)
    srl x5, x5, PMP_SHIFT
    LI(x6,PMP_MASK)
    and x5, x5, x6
    LI(x6,PMP_REGION_SIZE)
    or x5, x5, x6
    csrw pmpaddr12, x5

    LI(x4, (PMPREGION0_XWR_000))
    csrw pmpcfg3, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_3

// Test Case: 4 : L -> 1 and No Permissions given to the PMP Region 11

    LA(x5, REGIONSTART)
    srl x5, x5, PMP_SHIFT
    LI(x6,PMP_MASK)
    and x5, x5, x6
    LI(x6,PMP_REGION_SIZE)
    or x5, x5, x6
    csrw pmpaddr11, x5

    LI(x4, (PMPREGION3_XWR_000))
    csrw pmpcfg2, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_4

// Test Case: 5 : L -> 1 and No Permissions given to the PMP Region 10

    LA(x5, REGIONSTART)
    srl x5, x5, PMP_SHIFT
    LI(x6,PMP_MASK)
    and x5, x5, x6
    LI(x6,PMP_REGION_SIZE)
    or x5, x5, x6
    csrw pmpaddr10, x5

    LI(x4, (PMPREGION2_XWR_000))
    csrw pmpcfg2, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_5

// Test Case: 6 : L -> 1 and No Permissions given to the PMP Region 9

    LA(x5, REGIONSTART)
    srl x5, x5, PMP_SHIFT
    LI(x6,PMP_MASK)
    and x5, x5, x6
    LI(x6,PMP_REGION_SIZE)
    or x5, x5, x6
    csrw pmpaddr9, x5

    LI(x4, (PMPREGION1_XWR_000))
    csrw pmpcfg2, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_6

// Test Case: 7 : L -> 1 and No Permissions given to the PMP Region 8

    LA(x5, REGIONSTART)
    srl x5, x5, PMP_SHIFT
    LI(x6,PMP_MASK)
    and x5, x5, x6
    LI(x6,PMP_REGION_SIZE)
    or x5, x5, x6
    csrw pmpaddr8, x5

    LI(x4, (PMPREGION0_XWR_000))
    csrw pmpcfg2, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_7

// Test Case: 8 : L -> 1 and No Permissions given to the PMP Region 7

    LA(x5, REGIONSTART)
    srl x5, x5, PMP_SHIFT
    LI(x6,PMP_MASK)
    and x5, x5, x6
    LI(x6,PMP_REGION_SIZE)
    or x5, x5, x6
    csrw pmpaddr7, x5

    LI(x4, (PMPREGION3_XWR_000))
    csrw pmpcfg1, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_8

// Test Case: 9 : L -> 1 and No Permissions given to the PMP Region 6

    LA(x5, REGIONSTART)
    srl x5, x5, PMP_SHIFT
    LI(x6,PMP_MASK)
    and x5, x5, x6
    LI(x6,PMP_REGION_SIZE)
    or x5, x5, x6
    csrw pmpaddr6, x5

    LI(x4, (PMPREGION2_XWR_000))
    csrw pmpcfg1, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_9

// Test Case: 10 : L -> 1 and No Permissions given to the PMP Region 5

    LA(x5, REGIONSTART)
    srl x5, x5, PMP_SHIFT
    LI(x6,PMP_MASK)
    and x5, x5, x6
    LI(x6,PMP_REGION_SIZE)
    or x5, x5, x6
    csrw pmpaddr5, x5

    LI(x4, (PMPREGION1_XWR_000))
    csrw pmpcfg1, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_10

// Test Case: 11 : L -> 1 and No Permissions given to the PMP Region 4

    LA(x5, REGIONSTART)
    srl x5, x5, PMP_SHIFT
    LI(x6,PMP_MASK)
    and x5, x5, x6
    LI(x6,PMP_REGION_SIZE)
    or x5, x5, x6
    csrw pmpaddr4, x5

    LI(x4, (PMPREGION0_XWR_000))
    csrw pmpcfg1, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_11

// Test Case: 12 : L -> 1 and No Permissions given to the PMP Region 3

    LA(x5, REGIONSTART)
    srl x5, x5, PMP_SHIFT
    LI(x6,PMP_MASK)
    and x5, x5, x6
    LI(x6,PMP_REGION_SIZE)
    or x5, x5, x6
    csrw pmpaddr3, x5

    LI(x4, (PMPREGION3_XWR_000))
    csrw pmpcfg0, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_12

// Test Case: 13 : L -> 1 and No Permissions given to the PMP Region 2

    LA(x5, REGIONSTART)
    srl x5, x5, PMP_SHIFT
    LI(x6,PMP_MASK)
    and x5, x5, x6
    LI(x6,PMP_REGION_SIZE)
    or x5, x5, x6
    csrw pmpaddr2, x5

    LI(x4, (PMPREGION2_XWR_000))
    csrw pmpcfg0, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_13

// Test Case: 14 : L -> 1 and No Permissions given to the PMP Region 1

    LA(x5, REGIONSTART)
    srl x5, x5, PMP_SHIFT
    LI(x6,PMP_MASK)
    and x5, x5, x6
    LI(x6,PMP_REGION_SIZE)
    or x5, x5, x6
    csrw pmpaddr1, x5

    LI(x4, (PMPREGION1_XWR_000))
    csrw pmpcfg0, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_14

// Test Case: 15 : L -> 1 and No Permissions given to the PMP Region 0

    LA(x5, REGIONSTART)
    srl x5, x5, PMP_SHIFT
    LI(x6,PMP_MASK)
    and x5, x5, x6
    LI(x6,PMP_REGION_SIZE)
    or x5, x5, x6
    csrw pmpaddr0, x5

    LI(x4, (PMPREGION0_XWR_000))
    csrw pmpcfg0, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_15


RVTEST_CODE_END

RVTEST_DATA_BEGIN
.p2align 4

// Test case strings for reporting
test_1_str: .string "\"test: 1; cp: pmpm_cfg_napot_all_lw_address\""
test_2_str: .string "\"test: 2; cp: pmpm_cfg_napot_all_address-4\""
test_3_str: .string "\"test: 3; cp: pmpm_cfg_napot_all_address+4\""

.p2align 12
.p2align (UDB_PMP_GRANULARITY)
TEST_FOR_EXECUTION_0:
    .rept (g>>2)                                        // NAPOT region must be g_napot-aligned: g_napot-byte pad puts the region at PMP_NAPOT_REGION_START (0x80005008 at grain 2), so pmpaddr matches STANDARD_REGION and the region does not swallow the pad
    jr ra
    .endr

TEST_FOR_EXECUTION:
    .rept (SIZE/4)
    nop
    .endr

RETURN_INSTRUCTION:
    nop
    nop
    jr ra                                                        // Get back to the point from where TEST_FOR_EXECUTION was called.

RVTEST_DATA_END

// Signature region for self-checking
RVTEST_SIG_SETUP
