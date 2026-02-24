// --------------------------------------------------------------------------------
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
// Notes       : - Ensure `model_test.h` is configured to match your PMP grain
//                 and PMP region count before running this test.
//               - Adjust PMP configurations for specific hardware if required.
//
// Coverpoints :  cp_misaligned_na4 for PMPM is fully covered in this test file.
//
// Test Cases  :  Checking that misaligned read/write that crosses an NA4 PMP
//                boundary fails. We Set up standard NA4 region with L = {0/1},
//                XWR=111 and attempt misaligned {lw, lh, lhu, sw, sh} stradding
//                each offset partially in start and end of region.
//
// Dependencies: model_test.h, arch_test.h
// --------------------------------------------------------------------------------

#define SKIP_MEPC
##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: ['I','S','Smpmp']
# params:
#   MXLEN: 32
# MARCH: rv32i_zicsr
# CONFIG_DEPENDENT: true
##### END_TEST_CONFIG #####

// Define the name of this test file for reporting and the size of the signature region
#define TEST_FILE "pmpm_mislaigned_na4.S"
#define SIGUPD_COUNT 50

// Enable trap handler
#define rvtest_mtrap_routine
#define rvtest_strap_routine

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

#define g               4

#define NOP             0x13

.macro VERIFICATION_RWX ADDRESS

    LI(a4, NOP)                                             // Value to write (NOP)
    // Store Access Check straddling start
    LA(a5, (\ADDRESS-1))                                    // Address to be verified
    sw a4, 0(a5)                                            // word-level store test
    nop
    nop
    sh a4, 0(a5)                                            // Half-word store test
    nop
    nop

    // Store Access Check straddling end
    LA(a5, (\ADDRESS+4-1))                                  // Address to be verified
    sw a4, 0(a5)                                            // word-level store test
    nop
    nop
    sh a4, 0(a5)                                            // Half-word store test
    nop
    nop

     // Load Access Check straddling start
    LA(a5, (\ADDRESS-1))                                    // Address to be verified
    lh a4, 0(a5)                                            // Half-word load test
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, test_1_str)                                   // Signature update
    lhu a4, 0(a5)                                           // Half-word load test
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, test_2_str)                                   // Signature update
    lw a4, 0(a5)                                            // Word load test
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, test_3_str)                                   // Signature update

    // Load Access Check straddling end
    LA(a5, (\ADDRESS+g-1))                                  // Address to be verified
    lh a4, 0(a5)                                            // Half-word load test
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, test_4_str)                                   // Signature update
    lhu a4, 0(a5)                                           // Half-word load test
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, test_5_str)                                   // Signature update
    lw a4, 0(a5)                                            // Word load test
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, test_6_str)                               // Signature update

.endm

main:
    // Loop to SET ALL pmpcfg REGs to zero
    .set pmpcfgi, CSR_PMPCFG0
    .rept RVMODEL_NUM_PMPS/4
    csrw pmpcfgi , x0
    .set pmpcfgi, pmpcfgi+1
    .endr

    // Loop to SET ALL pmpaddr REGs to zero
    .set pmpaddri, CSR_PMPADDR0
    .rept RVMODEL_NUM_PMPS
    csrw pmpaddri, x0
    .set pmpaddri, pmpaddri+1
    .endr


#define PMP_REGION_GLOBAL   ((((PMP_L|PMP_R|PMP_W|PMP_X|PMP_NAPOT)&0xFF)   << PMP3_CFG_SHIFT))  // Background region with RWX enable.
#define PMPREGION_LXWR      ((((PMP_L|PMP_R|PMP_W|PMP_X|PMP_NA4)  &0xFF)   << PMP0_CFG_SHIFT))
#define PMPREGION_XWR       ((((      PMP_R|PMP_W|PMP_X|PMP_NA4)  &0xFF)   << PMP0_CFG_SHIFT))

#define PMPADDRESS_TOP_GLOBAL       -1                                              // All memory region
#define REGIONSTART         0x80002000      // RAM_BASE_ADDR + PROGRAM_SIZE
#define NA4_REGION          (REGIONSTART >> PMP_SHIFT)

#ifdef rvtest_strap_routine
    csrw satp, zero                // Disable address translation.
#endif

    LA(x4, PMPADDRESS_TOP_GLOBAL)
    csrw    pmpaddr15, x4

    //Lock the Background region.
    LI(x4, PMP_REGION_GLOBAL)
    csrw pmpcfg3, x4

    LA(x4, NA4_REGION)
    csrw    pmpaddr0, x4

//                                          Verification Section
// Test Case: 1 -- XWR Permissions given to the PMP Region.

    LI(x4, PMPREGION_XWR)
    csrw pmpcfg0, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION

// Test Case: 2 -- LXWR Permissions given to the PMP Region.

    LI(x4, PMPREGION_LXWR)
    csrw pmpcfg0, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION

    RVTEST_GOTO_MMODE

    li a4, 0xbeefcafe                                           // Clean Test exit verification signature.
    RVTEST_SIGUPD(x2, x5, x4, a4, test_7_str)                                   // Signature update
    j exit                                                      // Verification Complete, exit the test

.align 13
.align (RVMODEL_PMP_GRAIN+2)
TEST_FOR_EXECUTION:
    nop

RETURN_INSTRUCTION:
    nop
    nop
    jr ra                                                       // Get back to the point from where TEST_FOR_EXECUTION was called.

exit:

RVTEST_CODE_END

RVTEST_DATA_BEGIN
.align 4

// Test case strings for reporting
canary_mismatch: .string "Testcase signature canary mismatch!"
test_1_str: .string "\"test: 1; cp: pmpm_mislaigned_na4_lh_address-1\""
test_2_str: .string "\"test: 2; cp: pmpm_mislaigned_na4_lhu_address-1\""
test_3_str: .string "\"test: 3; cp: pmpm_mislaigned_na4__lw_address-1\""
test_4_str: .string "\"test: 4; cp: pmpm_mislaigned_na4_lh_address+g-1\""
test_5_str: .string "\"test: 5; cp: pmpm_mislaigned_na4_lhu_address+g-1\""
test_6_str: .string "\"test: 6; cp: pmpm_mislaigned_na4__lw_address+g-1\""
test_7_str: .string "\"test: 7; cp: pmpm_mislaigned_na4\""

RVTEST_DATA_END

// Signature region for self-checking
RVTEST_SIG_SETUP
