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
// Coverpoints : cp_cfg_A_tor_all for PMPM is fully covered in this test file.
//
// Test Cases  : Checking A = TOR works in each region. Preconfigure all
//               (PMP_writable_regs-1) PMP regions in with pmpcfg.L = 1,
//               pmpcfg.A = TOR, pmpcfg.XWR=00(i%2), starting with default
//               TOR region and moving up by g*i (each region getting larger by g).
//               Attempt lw at at start of region.  Odd regions should allow lw,
//               and all others should trap.
//
// Dependencies: model_test.h, arch_test.h
// --------------------------------------------------------------------------------

#define SKIP_MEPC
##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: ['I','S','Smpmp']
# MARCH: rv32i_zicsr
# CONFIG_DEPENDENT: true
##### END_TEST_CONFIG #####

// Define the name of this test file for reporting and the size of the signature region
#define TEST_FILE "pmpm_cfg_napot_all.S"
#define SIGUPD_COUNT 50

// Enable trap handler
#define rvtest_mtrap_routine
#define rvtest_strap_routine

// Include framework macros
#include "riscv_arch_test.h"

// Set up test environment and declare main entry point
RVTEST_BEGIN

#ifndef RVMODEL_PMP_GRAIN
    #define RVMODEL_PMP_GRAIN 4
#endif

#ifndef RVMODEL_NUM_PMPS
    #define RVMODEL_NUM_PMPS 16
#endif

#define NOP         0x13

.macro VERIFICATION_RWX ADDRESS

    LA(a5, \ADDRESS)                                        // Address to be ve
    lw a4, 0(a5)                                            // Word load test
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, test_1_str)                                   // Signature update

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

#define PMP_REGION_GLOBAL   (((PMP_L|PMP_R|PMP_W|PMP_X|PMP_NAPOT)&0xFF) << PMP3_CFG_SHIFT)  // Background region with RWX enable.
#define DEFAULT_TOR_REGION  (((PMP_L|PMP_R|PMP_W|PMP_X|PMP_TOR)&0xFF) << PMP0_CFG_SHIFT)
#define PMPREGION0_XWR_000  (((PMP_L|                  PMP_TOR)&0xFF) << PMP0_CFG_SHIFT)
#define PMPREGION1_XWR_001  (((PMP_L|PMP_R|            PMP_TOR)&0xFF) << PMP1_CFG_SHIFT)
#define PMPREGION2_XWR_000  (((PMP_L|                  PMP_TOR)&0xFF) << PMP2_CFG_SHIFT)
#define PMPREGION3_XWR_001  (((PMP_L|PMP_R|            PMP_TOR)&0xFF) << PMP3_CFG_SHIFT)

#ifdef rvtest_strap_routine
    csrw satp, zero                // Disable address translation.
#endif

    LA(x4, -1)
    csrw    pmpaddr15, x4

    //Lock the Background region.
    LI(x4, (PMP_REGION_GLOBAL))
    csrw pmpcfg3, x4

    LA(x4, TEST_FOR_EXECUTION_0)
    srl x4, x4, PMP_SHIFT
    csrw pmpaddr0, x4

    LA(x4, (TEST_FOR_EXECUTION_1))
    srl x4, x4, PMP_SHIFT
    csrw pmpaddr1, x4

    LA(x4, (TEST_FOR_EXECUTION_2))
    srl x4, x4, PMP_SHIFT
    csrw pmpaddr2, x4

    LA(x4, (TEST_FOR_EXECUTION_3))
    srl x4, x4, PMP_SHIFT
    csrw pmpaddr3, x4

    LA(x4, (TEST_FOR_EXECUTION_4))
    srl x4, x4, PMP_SHIFT
    csrw pmpaddr4, x4

    LA(x4, (TEST_FOR_EXECUTION_5))
    srl x4, x4, PMP_SHIFT
    csrw pmpaddr5, x4

    LA(x4, (TEST_FOR_EXECUTION_6))
    srl x4, x4, PMP_SHIFT
    csrw pmpaddr6, x4

    LA(x4, (TEST_FOR_EXECUTION_7))
    srl x4, x4, PMP_SHIFT
    csrw pmpaddr7, x4

    LA(x4, (TEST_FOR_EXECUTION_8))
    srl x4, x4, PMP_SHIFT
    csrw pmpaddr8, x4

    LA(x4, (TEST_FOR_EXECUTION_9))
    srl x4, x4, PMP_SHIFT
    csrw pmpaddr9, x4

    LA(x4, (TEST_FOR_EXECUTION_10))
    srl x4, x4, PMP_SHIFT
    csrw pmpaddr10, x4

    LA(x4, (TEST_FOR_EXECUTION_11))
    srl x4, x4, PMP_SHIFT
    csrw pmpaddr11, x4

    LA(x4, (TEST_FOR_EXECUTION_12))
    srl x4, x4, PMP_SHIFT
    csrw pmpaddr12, x4

    LA(x4, (TEST_FOR_EXECUTION_13))
    srl x4, x4, PMP_SHIFT
    csrw pmpaddr13, x4

    LA(x4, (TEST_FOR_EXECUTION_14))
    srl x4, x4, PMP_SHIFT
    csrw pmpaddr14, x4

//                                          Verification Section
// Test Case: 1 : Preconfigure all (PMP_writable_regs-1) PMP regions in with pmpcfg.L = 1, pmpcfg.A = TOR, pmpcfg.XWR=00(i%2)

    LI(x4, (PMPREGION3_XWR_001|PMPREGION2_XWR_000|PMPREGION1_XWR_001|DEFAULT_TOR_REGION))
    csrw pmpcfg0, x4
    LI(x4, (PMPREGION3_XWR_001|PMPREGION2_XWR_000|PMPREGION1_XWR_001|PMPREGION0_XWR_000))
    csrw pmpcfg1, x4
    LI(x4, (PMPREGION3_XWR_001|PMPREGION2_XWR_000|PMPREGION1_XWR_001|PMPREGION0_XWR_000))
    csrw pmpcfg2, x4
    LI(x4, (PMPREGION2_XWR_000|PMPREGION1_XWR_001|PMPREGION0_XWR_000))
    csrw pmpcfg3, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION_0
    VERIFICATION_RWX    TEST_FOR_EXECUTION_1
    VERIFICATION_RWX    TEST_FOR_EXECUTION_2
    VERIFICATION_RWX    TEST_FOR_EXECUTION_3
    VERIFICATION_RWX    TEST_FOR_EXECUTION_4
    VERIFICATION_RWX    TEST_FOR_EXECUTION_5
    VERIFICATION_RWX    TEST_FOR_EXECUTION_6
    VERIFICATION_RWX    TEST_FOR_EXECUTION_7
    VERIFICATION_RWX    TEST_FOR_EXECUTION_8
    VERIFICATION_RWX    TEST_FOR_EXECUTION_9
    VERIFICATION_RWX    TEST_FOR_EXECUTION_10
    VERIFICATION_RWX    TEST_FOR_EXECUTION_11
    VERIFICATION_RWX    TEST_FOR_EXECUTION_12
    VERIFICATION_RWX    TEST_FOR_EXECUTION_13

    li a4, 0xbeefcafe                                           // Clean Test exit verification signature.
    RVTEST_SIGUPD(x2, x5, x4, a4, test_2_str)                                   // Signature update
    j exit                                                      // Verification Complete, exit the test

.align 13
.align (RVMODEL_PMP_GRAIN+2)
TEST_FOR_EXECUTION_0:                       // Adding nops in TOR Region from 0x80001000 to 0x80001000 + g
    .rept (1<<(RVMODEL_PMP_GRAIN+2))
    nop
    .endr

TEST_FOR_EXECUTION_1:                       // Adding nops in TOR Region from 0x80001000 + g to 0x80001000 + 3g
    .rept (2*(1<<(RVMODEL_PMP_GRAIN+2)))
    nop
    .endr

TEST_FOR_EXECUTION_2:                       // Adding nops in TOR Region from 0x80001000 + 3g to 0x80001000 + 6g
    .rept (3*(1<<(RVMODEL_PMP_GRAIN+2)))
    nop
    .endr

TEST_FOR_EXECUTION_3:                       // Adding nops in TOR Region from 0x80001000 + 6g to 0x80001000 + 10g
    .rept (4*(1<<(RVMODEL_PMP_GRAIN+2)))
    nop
    .endr

TEST_FOR_EXECUTION_4:                       // Adding nops in TOR Region from 0x80001000 + 10g to 0x80001000 + 15g
    .rept (5*(1<<(RVMODEL_PMP_GRAIN+2)))
    nop
    .endr

TEST_FOR_EXECUTION_5:                       // Adding nops in TOR Region from 0x80001000 + 15g to 0x80001000 + 21g
    .rept (6*(1<<(RVMODEL_PMP_GRAIN+2)))
    nop
    .endr

TEST_FOR_EXECUTION_6:                       // Adding nops in TOR Region from 0x80001000 + 21g to 0x80001000 + 28g
    .rept (7*(1<<(RVMODEL_PMP_GRAIN+2)))
    nop
    .endr

TEST_FOR_EXECUTION_7:                       // Adding nops in TOR Region from 0x80001000 + 28g to 0x80001000 + 36g
    .rept (8*(1<<(RVMODEL_PMP_GRAIN+2)))
    nop
    .endr

TEST_FOR_EXECUTION_8:                       // Adding nops in TOR Region from 0x80001000 + 36g to 0x80001000 + 45g
    .rept (9*(1<<(RVMODEL_PMP_GRAIN+2)))
    nop
    .endr

TEST_FOR_EXECUTION_9:                       // Adding nops in TOR Region from 0x80001000 + 45g to 0x80001000 + 55g
    .rept (10*(1<<(RVMODEL_PMP_GRAIN+2)))
    nop
    .endr

TEST_FOR_EXECUTION_10:                      // Adding nops in TOR Region from 0x80001000 + 55g to 0x80001000 + 66g
    .rept (11*(1<<(RVMODEL_PMP_GRAIN+2)))
    nop
    .endr

TEST_FOR_EXECUTION_11:                      // Adding nops in TOR Region from 0x80001000 + 66g to 0x80001000 + 78g
    .rept (12*(1<<(RVMODEL_PMP_GRAIN+2)))
    nop
    .endr

TEST_FOR_EXECUTION_12:                      // Adding nops in TOR Region from 0x80001000 + 78g to 0x80001000 + 91g
    .rept (13*(1<<(RVMODEL_PMP_GRAIN+2)))
    nop
    .endr

TEST_FOR_EXECUTION_13:                      // Adding nops in TOR Region from 0x80001000 + 91g to 0x80001000 + 105g
    .rept (14*(1<<(RVMODEL_PMP_GRAIN+2)))
    nop
    .endr

TEST_FOR_EXECUTION_14:                      // Adding nops in TOR Region from 0x80001000 + 105g to 0x80001000 + 120g
    .rept (15*(1<<(RVMODEL_PMP_GRAIN+2)))
    nop
    .endr

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
test_1_str: .string "\"test: 1; cp: pmpm_cfg_tor_all_lw\""
test_2_str: .string "\"test: 2; cp: pmpm_cfg_tor_all\""

RVTEST_DATA_END

// Signature region for self-checking
RVTEST_SIG_SETUP
