// --------------------------------------------------------------------------------
// Copyright (C) 2025 Harvey Mudd College & Oklahoma State University, UET Lahore, Habib University
// Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
// SPDX-License-Identifier: Apache-2.0
//
// Title           : PMP address grain readback verification
// Authors         : Umer Shahid, Allen Baum, David Harris
//                  Muhammad Abdullah, Hamza Ali, Muhammad Zain
//                  Jordan Carlin
//
// Description : This test verifies PMP address grain readback behavior.
//               It writes pmpaddr0 in OFF and NAPOT modes, changes the
//               address-matching mode, and checks the grain-controlled
//               low pmpaddr bits.
//
// Coverpoints: cp_grain for PMPSm is fully covered in this test file.
//
// Test case  : Checking that low bits read as 0/1s depending on grain and address
//                matching mode. Set up pmpcfg0.L = 0, pmpcfg.A = {OFF/NAPOT}, write
//                pmpaddr0 = {all 0s / all 1s / checkerboard}. Change pmpcfg.A to
//                {OFF/TOR/NAPOT} and read back pmpaddr0. Bottom G-1 bits always read
//                as 1s in NAPOT. Bottom G bits read as 0s in TOR/OFF.
// --------------------------------------------------------------------------------


##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS:  ['Sm']
# params:
#   MXLEN: 64
#   NUM_PMP_ENTRIES: '>0'
# MARCH: rv64i_zicsr_zifencei
##### END_TEST_CONFIG #####

// Define the size of the signature region
#define SIGUPD_COUNT 18


// Include framework macros
#include "riscv_arch_test.h"

// Set up test environment and declare main entry point
RVTEST_BEGIN

main:
    // Loop to SET ALL pmpcfg REGs to zero
    .set pmpcfgi, CSR_PMPCFG0
    .rept UDB_NUM_PMP_ENTRIES/8
    csrw pmpcfgi , x0
    .set pmpcfgi, pmpcfgi+2
    .endr

    // Loop to SET ALL pmpaddr REGs to zero
    .set pmpaddri, CSR_PMPADDR0
    .rept UDB_NUM_PMP_ENTRIES
    csrw pmpaddri, x0
    .set pmpaddri, pmpaddri+1
    .endr

#define PMPREGION_OFF          ((((     PMP_R|PMP_W|PMP_X)               &0xFF) << PMP0_CFG_SHIFT))
#define PMPREGION_NAPOT     ((((     PMP_R|PMP_W|PMP_X |PMP_NAPOT) &0xFF) << PMP0_CFG_SHIFT))
#define PMPREGION_TOR          ((((     PMP_R|PMP_W|PMP_X |PMP_TOR)   &0xFF) << PMP0_CFG_SHIFT))

#define PMP_GRAIN_MASK     ((1 << (UDB_PMP_GRANULARITY - 2)) - 1)

#define REGIONSTART            TEST_FOR_EXECUTION        // RAM_BASE_ADDR + PROGRAM_SIZE
#define CHECKERBOARD        0xAAAAAAAAAAAAAAAA


    RVTEST_PMP_SET_BACKGROUND x4

    LA(x4, REGIONSTART)
    srl x4, x4, PMP_SHIFT
    csrw     pmpaddr0, x4

    LI(t3, PMP_GRAIN_MASK)
                                                //Verification Section
    // Test Case 1: Writing all 0s in pmpaddr0 when A = NAPOT and read back when A= {OFF,NAPOT,TOR}

// Write all 0s in NAPOT

    LI(x6, PMPREGION_NAPOT)
    csrw pmpcfg0, x6
    LI(x6, 0)
    csrw pmpaddr0, x6

// Read back in OFF

    LI(x6, PMPREGION_OFF)
    csrw pmpcfg0, x6
    test_1:
        csrr x7, pmpaddr0
        and x7, x7, t3
        RVTEST_SIGUPD(x2, x5, x4, x7, test_1, test_1_str)


// Write all 0s in NAPOT

    LI(x6, PMPREGION_NAPOT)
    csrw pmpcfg0, x6
    LI(x6, 0)
    csrw pmpaddr0, x6

// Read back in NAPOT

    LI(x6, PMPREGION_NAPOT)
    csrw pmpcfg0, x6
    test_2:
        csrr x7, pmpaddr0
        and x7, x7, t3
        RVTEST_SIGUPD(x2, x5, x4, x7, test_2, test_2_str)

#ifdef UDB_PMP_TOR_SUPPORTED

// Write all 0s in NAPOT

    LI(x6, PMPREGION_NAPOT)
    csrw pmpcfg0, x6
    LI(x6, 0)
    csrw pmpaddr0, x6

// Read back in  TOR

    LI(x6, PMPREGION_TOR)
    csrw pmpcfg0, x6
    test_3:
        csrr x7, pmpaddr0
        and x7, x7, t3
        RVTEST_SIGUPD(x2, x5, x4, x7, test_3, test_3_str)

#endif

// Test Case 2: Writing all 0s in pmpaddr0 when A = OFF and read back when A= {OFF,NAPOT,TOR}

// Write all 0s in OFF

    LI(x6, PMPREGION_OFF)
    csrw pmpcfg0, x6
    LI(x6, 0)
    csrw pmpaddr0, x6

// Read back in OFF

    LI(x6, PMPREGION_OFF)
    csrw pmpcfg0, x6
    test_4:
        csrr x7, pmpaddr0
        and x7, x7, t3
        RVTEST_SIGUPD(x2, x5, x4, x7, test_4, test_4_str)

// Write all 0s in OFF

    LI(x6, PMPREGION_OFF)
    csrw pmpcfg0, x6
    LI(x6, 0)
    csrw pmpaddr0, x6

// Read back in NAPOT

    LI(x6, PMPREGION_NAPOT)
    csrw pmpcfg0, x6
    test_5:
        csrr x7, pmpaddr0
        and x7, x7, t3
        RVTEST_SIGUPD(x2, x5, x4, x7, test_5, test_5_str)

#ifdef UDB_PMP_TOR_SUPPORTED

// Write all 0s in OFF

    LI(x6, PMPREGION_OFF)
    csrw pmpcfg0, x6
    LI(x6, 0)
    csrw pmpaddr0, x6

// Read back in TOR

    LI(x6, PMPREGION_TOR)
    csrw pmpcfg0, x6
    test_6:
        csrr x7, pmpaddr0
        and x7, x7, t3
        RVTEST_SIGUPD(x2, x5, x4, x7, test_6, test_6_str)

#endif

// Test Case 3: Writing all 1s in pmpaddr0 when A = NAPOT and read back when A= {OFF,NAPOT,TOR}

// Write all 1s in NAPOT

    LI(x6, PMPREGION_NAPOT)
    csrw pmpcfg0, x6
    LI(x6, -1)
    csrw pmpaddr0, x6

// Read back in OFF

    LI(x6, PMPREGION_OFF)
    csrw pmpcfg0, x6
    test_7:
        csrr x7, pmpaddr0
        and x7, x7, t3
        RVTEST_SIGUPD(x2, x5, x4, x7, test_7, test_7_str)

// Write all 1s in NAPOT

    LI(x6, PMPREGION_NAPOT)
    csrw pmpcfg0, x6
    LI(x6, -1)
    csrw pmpaddr0, x6

// Read back in NAPOT

    LI(x6, PMPREGION_NAPOT)
    csrw pmpcfg0, x6
    test_8:
        csrr x7, pmpaddr0
        and x7, x7, t3
        RVTEST_SIGUPD(x2, x5, x4, x7, test_8, test_8_str)

#ifdef UDB_PMP_TOR_SUPPORTED

// Write all 1s in NAPOT

    LI(x6, PMPREGION_NAPOT)
    csrw pmpcfg0, x6
    LI(x6, -1)
    csrw pmpaddr0, x6

// Read back in TOR

    LI(x6, PMPREGION_TOR)
    csrw pmpcfg0, x6
    test_9:
        csrr x7, pmpaddr0
        and x7, x7, t3
        RVTEST_SIGUPD(x2, x5, x4, x7, test_9, test_9_str)

#endif

// Test Case 4: Writing all 1s in pmpaddr0 when A = OFF and read back when A= {OFF,NAPOT,TOR}

// Write all 1s in OFF

    LI(x6, PMPREGION_OFF)
    csrw pmpcfg0, x6
    LI(x6, -1)
    csrw pmpaddr0, x6

// Read back in OFF

    LI(x6, PMPREGION_OFF)
    csrw pmpcfg0, x6
    test_10:
        csrr x7, pmpaddr0
        and x7, x7, t3
        RVTEST_SIGUPD(x2, x5, x4, x7, test_10, test_10_str)

// Write all 1s in OFF

    LI(x6, PMPREGION_OFF)
    csrw pmpcfg0, x6
    LI(x6, -1)
    csrw pmpaddr0, x6

// Read back in NAPOT

    LI(x6, PMPREGION_NAPOT)
    csrw pmpcfg0, x6
    test_11:
        csrr x7, pmpaddr0
        and x7, x7, t3
        RVTEST_SIGUPD(x2, x5, x4, x7, test_11, test_11_str)

#ifdef UDB_PMP_TOR_SUPPORTED

// Write all 1s in OFF

    LI(x6, PMPREGION_OFF)
    csrw pmpcfg0, x6
    LI(x6, -1)
    csrw pmpaddr0, x6

// Read back in TOR

    LI(x6, PMPREGION_TOR)
    csrw pmpcfg0, x6
    test_12:
        csrr x7, pmpaddr0
        and x7, x7, t3
        RVTEST_SIGUPD(x2, x5, x4, x7, test_12, test_12_str)

#endif

// Test Case 5: Writing checkerboard pattern(1010...) in pmpaddr0 when A = NAPOT and read back when A= {OFF,NAPOT,TOR}

// Write checkerboard in NAPOT

    LI(x6, PMPREGION_NAPOT)
    csrw pmpcfg0, x6
    LI(x6, CHECKERBOARD)
    csrw pmpaddr0, x6

// Read back in OFF

    LI(x6, PMPREGION_OFF)
    csrw pmpcfg0, x6
    test_13:
        csrr x7, pmpaddr0
        and x7, x7, t3
        RVTEST_SIGUPD(x2, x5, x4, x7, test_13, test_13_str)

// Write checkerboard in NAPOT

    LI(x6, PMPREGION_NAPOT)
    csrw pmpcfg0, x6
    LI(x6, CHECKERBOARD)
    csrw pmpaddr0, x6

// Read back in NAPOT

    LI(x6, PMPREGION_NAPOT)
    csrw pmpcfg0, x6
    test_14:
        csrr x7, pmpaddr0
        and x7, x7, t3
        RVTEST_SIGUPD(x2, x5, x4, x7, test_14, test_14_str)

#ifdef UDB_PMP_TOR_SUPPORTED

// Write checkerboard in NAPOT

    LI(x6, PMPREGION_NAPOT)
    csrw pmpcfg0, x6
    LI(x6, CHECKERBOARD)
    csrw pmpaddr0, x6

// Read back in TOR

    LI(x6, PMPREGION_TOR)
    csrw pmpcfg0, x6
    test_15:
        csrr x7, pmpaddr0
        and x7, x7, t3
        RVTEST_SIGUPD(x2, x5, x4, x7, test_15, test_15_str)

#endif

// Test Case 6: Writing checkerboard pattern(1010...) in pmpaddr0 when A = OFF and read back when A= {OFF,NAPOT,TOR}

// Write checkerboard in OFF

    LI(x6, PMPREGION_OFF)
    csrw pmpcfg0, x6
    LI(x6, CHECKERBOARD)
    csrw pmpaddr0, x6

// Read back in OFF

    LI(x6, PMPREGION_OFF)
    csrw pmpcfg0, x6
    test_16:
        csrr x7, pmpaddr0
        and x7, x7, t3
        RVTEST_SIGUPD(x2, x5, x4, x7, test_16, test_16_str)

// Write checkerboard in OFF

    LI(x6, PMPREGION_OFF)
    csrw pmpcfg0, x6
    LI(x6, CHECKERBOARD)
    csrw pmpaddr0, x6

// Read back in NAPOT

    LI(x6, PMPREGION_NAPOT)
    csrw pmpcfg0, x6
    test_17:
        csrr x7, pmpaddr0
        and x7, x7, t3
        RVTEST_SIGUPD(x2, x5, x4, x7, test_17, test_17_str)

#ifdef UDB_PMP_TOR_SUPPORTED

// Write checkerboard in OFF

    LI(x6, PMPREGION_OFF)
    csrw pmpcfg0, x6
    LI(x6, CHECKERBOARD)
    csrw pmpaddr0, x6

// Read back in TOR

    LI(x6, PMPREGION_TOR)
    csrw pmpcfg0, x6
    test_18:
        csrr x7, pmpaddr0
        and x7, x7, t3
        RVTEST_SIGUPD(x2, x5, x4, x7, test_18, test_18_str)

#endif

    RVTEST_GOTO_MMODE

RVTEST_CODE_END
RVTEST_DATA_BEGIN

// Test case strings for reporting
test_1_str: .string "\"write zeros with A=NAPOT, read back with A=OFF; cp: cp_grain\""
test_2_str: .string "\"write zeros with A=NAPOT, read back with A=NAPOT; cp: cp_grain\""
test_3_str: .string "\"write zeros with A=NAPOT, read back with A=TOR; cp: cp_grain\""
test_4_str: .string "\"write zeros with A=OFF, read back with A=OFF; cp: cp_grain\""
test_5_str: .string "\"write zeros with A=OFF, read back with A=NAPOT; cp: cp_grain\""
test_6_str: .string "\"write zeros with A=OFF, read back with A=TOR; cp: cp_grain\""
test_7_str: .string "\"write ones with A=NAPOT, read back with A=OFF; cp: cp_grain\""
test_8_str: .string "\"write ones with A=NAPOT, read back with A=NAPOT; cp: cp_grain\""
test_9_str: .string "\"write ones with A=NAPOT, read back with A=TOR; cp: cp_grain\""
test_10_str: .string "\"write ones with A=OFF, read back with A=OFF; cp: cp_grain\""
test_11_str: .string "\"write ones with A=OFF, read back with A=NAPOT; cp: cp_grain\""
test_12_str: .string "\"write ones with A=OFF, read back with A=TOR; cp: cp_grain\""
test_13_str: .string "\"write checkerboard with A=NAPOT, read back with A=OFF; cp: cp_grain\""
test_14_str: .string "\"write checkerboard with A=NAPOT, read back with A=NAPOT; cp: cp_grain\""
test_15_str: .string "\"write checkerboard with A=NAPOT, read back with A=TOR; cp: cp_grain\""
test_16_str: .string "\"write checkerboard with A=OFF, read back with A=OFF; cp: cp_grain\""
test_17_str: .string "\"write checkerboard with A=OFF, read back with A=NAPOT; cp: cp_grain\""
test_18_str: .string "\"write checkerboard with A=OFF, read back with A=TOR; cp: cp_grain\""

.p2align 12
.p2align (UDB_PMP_GRANULARITY)
TEST_FOR_EXECUTION_0:
    .rept (1 << (UDB_PMP_GRANULARITY - 2))              // one PMP granule of return-instruction fillers: places the region on the next granule boundary (= PMP_REGION_START at coverage grain 2), grain-aligned at larger grains
    jr ra
    .endr

TEST_FOR_EXECUTION:
    .rept (1<<(UDB_PMP_GRANULARITY))
    nop
    .endr

RETURN_INSTRUCTION:
    nop
    nop
    jr ra                                                        // Get back to the point from where TEST_FOR_EXECUTION was called.

RVTEST_DATA_END

// Signature region for self-checking
RVTEST_SIG_SETUP
