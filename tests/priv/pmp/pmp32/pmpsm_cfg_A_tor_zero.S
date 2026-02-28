// --------------------------------------------------------------------------------
// Title           : Comprehensive PMP (Physical Memory Protection) Verification
// Authors         : Umer Shahid, Allen Baum, David Harris
//                  Muhammad Abdullah, Hamza Ali, Muhammad Zain
//
// Description : This test verifies the functionality and enforcement of
//               Physical Memory Protection (PMP) configurations in RISC-V
//               systems. It checks that region 0 extends from 0 to pmpaddr0
//               in TOR mode.
//
// Notes       : - Ensure `rvmodel_macros.h` is configured to match your PMP grain
//                 and PMP region count before running this test.
//               - Adjust PMP configurations for specific hardware if required.
//
// Coverpoints:  cp_cfg_A_tor0 for PMPM is fully covered in this test file.
//
// Test Cases  : Checking region 0 extends from 0 to pmpaddr0 in TOR mode.
//                 Dropping the background region. With pmpcfg0.L=1, pmpcfg0.A=TOR,
//                 pmpcfg0.XWR=111, default TOR region: {lw, sw, jalr} to {0,
//                 pmpaddr0-4, pmpaddr0}.
//
// Dependencies: model_test.h, arch_test.h
// --------------------------------------------------------------------------------

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: ['I','Smpmp']
# params:
#   MXLEN: 32
# MARCH: rv32i_zicsr
# CONFIG_DEPENDENT: true
##### END_TEST_CONFIG #####

// Define the name of this test file for reporting and the size of the signature region
#define TEST_FILE "pmpsm_cfg_A_tor_zero.S"
#define SIGUPD_COUNT 50

// Enable trap handler
#define rvtest_mtrap_routine
#define RVTEST_PRIV_TEST

#define SKIP_MEPC
#define SKIP_MTVAL

// Include framework macros
#include "riscv_arch_test.h"

// Set up test environment and declare main entry point
RVTEST_BEGIN

#define NOP             0x13

.macro VERIFICATION_RWX ADDRESS, TEST_CASE

    LI(a4, NOP)                                              // Value to write (NOP)

    LA(a5, (\ADDRESS))                                         // Address to be verified
    \TEST_CASE\()_1:
    sw a4, 0(a5)                                             // word-level store test
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4,\TEST_CASE\()_1,test_1_str)               // Signature update

    LA(a5, (\ADDRESS-4))                                     // Address to be verified
    \TEST_CASE\()_2:
    sw a4, 0(a5)                                             // word-level store test
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4,\TEST_CASE\()_2,test_2_str)               // Signature update

    LI(x4, 0xACCE)
    li a5, 0
    LA(x1, 4f)                                               // Address to be verified
    sw a4, 0(a5)                                             // word-level store test
    nop
4:
    nop


    LA(a5, (\ADDRESS))                                         // Address to be verified
    \TEST_CASE\()_3:
    lw a4, 0(a5)                                             // Word load test
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4,\TEST_CASE\()_3,test_3_str)               // Signature update

    LA(a5, (\ADDRESS-4))                                         // Address to be verified
    \TEST_CASE\()_4:
    lw a4, 0(a5)                                             // Word load test
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4,\TEST_CASE\()_4,test_4_str)               // Signature update

    LI(x4, 0xACCE)
    LA(x1, 5f)
    li a5, 0                                                   // Address to be verified
    lw a4, 0(a5)                                             // word-level store test
    nop

5:
    nop


    LI(x4, 0xACCE)
    LA (a4, (\ADDRESS))
    LA(x1, 1f)                                                // Store the return Address in x1
    jalr ra, 0(a4)
    nop
1:
    nop

    LI(x4, 0xACCE)
    LA (a4, (\ADDRESS-4))
    LA(x1, 2f)                            // Store the return Address in x1
    jalr ra, 0(a4)
    nop
2:
    nop

    LI(x4, 0xACCE)
    li a5, 0
    LA(x1, 3f)                            // Store the return Address in x1
    jalr ra, 0(a5)
    nop
3:
    nop

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

#define PMP_REGION_GLOBAL           ((((PMP_L|PMP_R|PMP_W|PMP_X|PMP_NAPOT)&0xFF) << PMP3_CFG_SHIFT))  // Background region with RWX enable.
#define PMPREGION_TOR                 ((((PMP_L|PMP_R|PMP_W|PMP_X|PMP_TOR)&0xFF)   << PMP0_CFG_SHIFT))

#ifdef rvtest_strap_routine
    csrw satp, zero             // Disable address translation.
#endif

    LA(x4, -1)                       // All memory region
    csrw     pmpaddr15, x4

    LA(x4, TEST_FOR_EXECUTION)
    srl x4, x4, PMP_SHIFT
    csrw     pmpaddr0, x4

    //Lock the Background region.
    LI(x4, PMP_REGION_GLOBAL)
    csrw pmpcfg3, x4

//                                            Verification Section
// Test Case 1: Default TOR region with XWR permissions

    LI(x4, PMPREGION_TOR)
    csrw pmpcfg0, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_1

    RVTEST_GOTO_MMODE

    j exit                                                        // Verification Complete, exit the test

.align 13
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
test_1_str: .string "\"test: 1; cp: pmpm_cfg_A_tor_zero_store_access_at_pmpaddr0\""
test_2_str: .string "\"test: 2; cp: pmpm_cfg_A_tor_zero_store_access_at_pmpaddr0-4\""
test_3_str: .string "\"test: 3; cp: pmpm_cfg_A_tor_zero_load_access_at_pmpaddr0\""
test_4_str: .string "\"test: 4; cp: pmpm_cfg_A_tor_zero_load_access_at_pmpaddr0-4\""

RVTEST_DATA_END

// Signature region for self-checking
RVTEST_SIG_SETUP
