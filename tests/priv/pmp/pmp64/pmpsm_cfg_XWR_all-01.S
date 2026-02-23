// --------------------------------------------------------------------------------
// Title           : Comprehensive PMP (Physical Memory Protection) Verification
// Authors         : Umer Shahid, Allen Baum, David Harris
//                  Muhammad Abdullah, Hamza Ali, Muhammad Zain
//
// Description : This test verifies the functionality and enforcement of
//               Physical Memory Protection (PMP) configurations in RISC-V
//               systems. It specifically tests the Read, Write, and Execute
//               permissions for a designated memory region, ensuring that
//               the PMP settings are correctly applied and that the system
//               behaves as expected when accessing this region.
//
// Notes       : - Ensure `model_test.h` is configured to match your PMP grain
//                 and PMP region count before running this test.
//               - Adjust PMP configurations for specific hardware if required.
//
// Coverpoints : cp_cfg_X0_all, cp_cfg_X1_all, cp_cfg_RW00_all, cp_cfg_RW10_all
//                 and cp_cfg_RW11_all for PMPM is partially covered in this file.
//
// Test Cases  : Rolling legal XWR starting from region with lowest priority i.e.,
//               region 14 to region with highest priority i.e., region 0 such
//               that each of the writable registers gets each of the 6 legal
//               combinations at least once.
//
// Dependencies: model_test.h, arch_test.h
// --------------------------------------------------------------------------------

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: ['I','S','Smpmp']
# MARCH: rv64i_zicsr
# CONFIG_DEPENDENT: true
##### END_TEST_CONFIG #####

// Define the name of this test file for reporting and the size of the signature region
#define TEST_FILE "pmpm_cfg_XWR_all-01.S"
#define SIGUPD_COUNT 50

// Enable trap handler
#define rvtest_mtrap_routine
#define rvtest_strap_routine

#define SKIP_MEPC

// Include framework macros
#include "riscv_arch_test.h"

// Set up test environment and declare main entry point
RVTEST_BEGIN

#ifndef RVMODEL_PMP_GRAIN
    #define RVMODEL_PMP_GRAIN 0
#endif

#ifndef RVMODEL_NUM_PMPS
    #define RVMODEL_NUM_PMPS 16
#endif

#define NOP         (0x13<<32)+0x13

.macro VERIFICATION_RWX ADDRESS
    // Execution Access Check
    LA (a4, \ADDRESS)
    LI(x4, 0xACCE)                        // Store a value which is to be checked in trap handler
    LA(x4, 1f)                            // Store the return Address in x4
    jalr ra, 0(a4)
    nop
1:
    nop

    // Store Access Check
    LA(a5, \ADDRESS)                                         // Address to be verified
    LI(a4, NOP)                                              // Value to write (NOP)
    sb a4, 0(a5)                                             // Byte-level store test
    nop
    sh a4, 0(a5)                                             // Half-word store test
    nop
    sw a4, 0(a5)                                             // Word store test
    nop
    sd a4, 0(a5)                                             // Word store test
    nop

    // Load Access Check
    lb a4, 0(a5)                                             // Byte-level load test
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, test_1_str)                                   // Signature update
    lbu a4, 0(a5)                                             // Byte-level load test
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, test_2_str)                                  // Signature update
    lh a4, 0(a5)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, test_3_str)                                   // Signature update
    lhu a4, 0(a5)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, test_4_str)                                  // Signature update
    lw a4, 0(a5)                                             // Word load test
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, test_5_str)                                   // Signature update
    lwu a4, 0(a5)                                             // Word load test
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, test_6_str)                                   // Signature update
    ld a4, 0(a5)                                             // Doubleword load test
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, test_7_str)                                   // Signature update

.endm

main:
    // Loop to SET ALL pmpcfg REGs to zero
    .set pmpcfgi, CSR_PMPCFG0
    .rept RVMODEL_NUM_PMPS/8
    csrw pmpcfgi , x0
    .set pmpcfgi, pmpcfgi+2
    .endr

    // Loop to SET ALL pmpaddr REGs to zero
    .set pmpaddri, CSR_PMPADDR0
    .rept RVMODEL_NUM_PMPS
    csrw pmpaddri, x0
    .set pmpaddri, pmpaddri+1
    .endr

#define PMP_REGION_GLOBAL    ((PMP_L|PMP_R|PMP_W|PMP_X|PMP_NAPOT)&0xFF)  // Background region with RWX enable.
#define PMPREGION_XWR_000   ((PMP_L|                  PMP_NAPOT)&0xFF)
#define PMPREGION_XWR_100   ((PMP_L|            PMP_X|PMP_NAPOT)&0xFF)
#define PMPREGION_XWR_001   ((PMP_L|PMP_R|            PMP_NAPOT)&0xFF)
#define PMPREGION_XWR_101   ((PMP_L|PMP_R|      PMP_X|PMP_NAPOT)&0xFF)
#define PMPREGION_XWR_011   ((PMP_L|PMP_R|PMP_W      |PMP_NAPOT)&0xFF)
#define PMPREGION_XWR_111   ((PMP_L|PMP_R|PMP_W|PMP_X|PMP_NAPOT)&0xFF)


#define PMPADDRESS_TOP_GLOBAL        -1                                                // All memory region
#define PMPADDRESS            TEST_FOR_EXECUTION                              // Test section address
#define PMP_REGION_SIZE     (1 << (RVMODEL_PMP_GRAIN - 1)-1)
#define PMP_MASK            ~(1 << (RVMODEL_PMP_GRAIN - 1)-1)

#ifdef rvtest_strap_routine
    csrw satp, zero                // Disable address translation.
#endif

    LA(x4, PMPADDRESS_TOP_GLOBAL)
    csrw     pmpaddr15, x4

    //Lock the Background region.
    LI(x4, (PMP_REGION_GLOBAL << PMP7_CFG_SHIFT))
    csrw pmpcfg2, x4

    LA(x4, PMPADDRESS)
    srl x4, x4, PMP_SHIFT

.if RVMODEL_PMP_GRAIN != 0
    li t0, PMP_MASK
    and x4, x4, t0
    li t0, PMP_REGION_SIZE
    or x4, x4, t0
.endif

    .set pmpaddri, CSR_PMPADDR0
    .rept RVMODEL_NUM_PMPS
    csrw pmpaddri, x4
    .set pmpaddri, pmpaddri+1
    .endr

//                                            Verification Section
// Test Case: 1 -- No Permissions given to the PMP Region 14

    LI(x4, (PMPREGION_XWR_000 << PMP6_CFG_SHIFT))
    csrw pmpcfg2, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION

    RVTEST_GOTO_MMODE

// Test Case: 2 -- X Permissions given to the PMP Region 13

    LI(x4, (PMPREGION_XWR_100 << PMP5_CFG_SHIFT))
    csrw pmpcfg2, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION

    RVTEST_GOTO_MMODE

// Test Case: 3 -- R Permissions given to the PMP Region 12

    LI(x4, (PMPREGION_XWR_001 << PMP4_CFG_SHIFT))
    csrw pmpcfg2, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION

    RVTEST_GOTO_MMODE

// Test Case: 4 -- XR Permissions given to the PMP Region 11

    LI(x4, (PMPREGION_XWR_101 << PMP3_CFG_SHIFT))
    csrw pmpcfg2, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION

    RVTEST_GOTO_MMODE

// Test Case: 5 -- WR Permissions given to the PMP Region 10

    LI(x4, (PMPREGION_XWR_011 << PMP2_CFG_SHIFT))
    csrw pmpcfg2, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION

    RVTEST_GOTO_MMODE

// Test Case: 6 -- XWR Permissions given to the PMP Region 9

    LI(x4, (PMPREGION_XWR_111 << PMP1_CFG_SHIFT))
    csrw pmpcfg2, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION

    RVTEST_GOTO_MMODE

// Test Case: 7 -- No Permissions given to the PMP Region 8

    LI(x4, (PMPREGION_XWR_000 << PMP0_CFG_SHIFT))
    csrw pmpcfg2, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION

    RVTEST_GOTO_MMODE

// Test Case: 8 -- X Permissions given to the PMP Region 7

    LI(x4, (PMPREGION_XWR_100 << PMP7_CFG_SHIFT))
    csrw pmpcfg0, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION

    RVTEST_GOTO_MMODE

// Test Case: 9 -- R Permissions given to the PMP Region 6

    LI(x4, (PMPREGION_XWR_001 << PMP6_CFG_SHIFT))
    csrw pmpcfg0, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION

    RVTEST_GOTO_MMODE

// Test Case: 10 -- XR Permissions given to the PMP Region 5

    LI(x4, (PMPREGION_XWR_101 << PMP5_CFG_SHIFT))
    csrw pmpcfg0, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION

    RVTEST_GOTO_MMODE

// Test Case: 11 -- XR Permissions given to the PMP Region 4

    LI(x4, (PMPREGION_XWR_011 << PMP4_CFG_SHIFT))
    csrw pmpcfg0, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION

    RVTEST_GOTO_MMODE

// Test Case: 12 -- XWR Permissions given to the PMP Region 3

    LI(x4, (PMPREGION_XWR_111 << PMP3_CFG_SHIFT))
    csrw pmpcfg0, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION

    RVTEST_GOTO_MMODE

// Test Case: 13 -- No Permissions given to the PMP Region 2

    LI(x4, (PMPREGION_XWR_000 << PMP2_CFG_SHIFT))
    csrw pmpcfg0, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION

    RVTEST_GOTO_MMODE

// Test Case: 14 -- X Permissions given to the PMP Region 1

    LI(x4, (PMPREGION_XWR_100 << PMP1_CFG_SHIFT))
    csrw pmpcfg0, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION

    RVTEST_GOTO_MMODE

// Test Case: 15 -- R Permissions given to the PMP Region 0

    LI(x4, (PMPREGION_XWR_001 << PMP0_CFG_SHIFT))
    csrw pmpcfg0, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION

    RVTEST_GOTO_MMODE

    li a4, 0xbeefcafe                                            // Clean Test exit verification signature.
    RVTEST_SIGUPD(x2, x5, x4, a4, test_8_str)                                       // Signature update
    j exit                                                        // Verification Complete, exit the test

.align 12
.align (RVMODEL_PMP_GRAIN+2)
TEST_FOR_EXECUTION:
    .rept (1<<(RVMODEL_PMP_GRAIN+2))
    nop
    .endr

RETURN_INSTRUCTION:
    nop
    nop
    jr ra                                                        // Get back to the point from where TEST_FOR_EXECUTION was called.

exit:

RVTEST_CODE_END

RVTEST_DATA_BEGIN
.align 4

// Test case strings for reporting
canary_mismatch: .string "Testcase signature canary mismatch!"
test_1_str: .string "\"test: 1; cp: pmpm_cfg_XWR_all_lb\""
test_2_str: .string "\"test: 2; cp: pmpm_cfg_XWR_all_lbu\""
test_3_str: .string "\"test: 3; cp: pmpm_cfg_XWR_all_lh\""
test_4_str: .string "\"test: 4; cp: pmpm_cfg_XWR_all_lhu\""
test_5_str: .string "\"test: 5; cp: pmpm_cfg_XWR_all_lw\""
test_6_str: .string "\"test: 6; cp: pmpm_cfg_XWR_all_lwu\""
test_7_str: .string "\"test: 7; cp: pmpm_cfg_XWR_all_ld\""
test_8_str: .string "\"test: 8; cp: pmpm_cfg_XWR_all\""

RVTEST_DATA_END

// Signature region for self-checking
RVTEST_SIG_SETUP
