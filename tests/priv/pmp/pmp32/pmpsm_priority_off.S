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
// Coverpoints :  cp_priority_off for PMPM is fully covered in this file.
//
// Test Cases  :  Testing that an OFF region does not match, and the first matching
//                region takes priority.
//                pmp0cfg0.L=1, pmpcfg0.A=OFF, pmpcfg0.XWR=000, pmpaddr0 = REGIONSTART
//                pmp1cfg0.L=1, pmpcfg1.A=TOR, pmpcfg1.XWR=101, pmpaddr1 = REGIONSTART
//                pmp2cfg0.L=1, pmpcfg2.A=OFF, pmpcfg2.XWR=000, pmpaddr2 = REGIONSTART
//                pmp3cfg0.L=1, pmpcfg3.A=TOR, pmpcfg3.XWR=111, pmpaddr3 = REGIONSTART
//                {lw, sw, jalr} to some address at REGIONSTART. It should succeed on
//                X and R but not W because it hits region 1.
//
// Dependencies: model_test.h, arch_test.h
// --------------------------------------------------------------------------------

#define SKIP_MEPC
##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: ['I','S','Smpmp']
# MARCH: rv${XLEN}i_zicsr
# CONFIG_DEPENDENT: true
##### END_TEST_CONFIG #####

// Define the name of this test file for reporting and the size of the signature region
#define TEST_FILE "pmpm_priority_off.S"
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
#define g   (1 << (RVMODEL_PMP_GRAIN + 2))

.macro VERIFICATION_RWX ADDRESS

    LI(x3, 0xACCE)                      // Store a value which is to be checked in trap handler
    // Execution Access Check
    LA (a4, \ADDRESS)
    LA(x4, 1f)                          // Store the return Address in x4
    jalr ra, 0(a4)
    nop
    nop
1:
    nop
    nop

    LI(a4, NOP)                                             // Value to write (NOP)
    // Store Access Check
    LA(a5, \ADDRESS)                                        // Address to be verified
    sw a4, 0(a5)
    nop
    nop

    LA(a5, \ADDRESS)                                        // Address to be verified
    lw a4, 0(a5)
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

#define PMP_REGION_GLOBAL   ((((PMP_L|PMP_R|PMP_W|PMP_X|PMP_NAPOT)&0xFF) << PMP3_CFG_SHIFT))  // Background region with RWX enable.
#define PMPREGION0_LXWR_1000 ((((PMP_L                            )&0xFF) << PMP0_CFG_SHIFT))
#define PMPREGION1_LXWR_1101 ((((PMP_L|PMP_R|      PMP_X|PMP_TOR  )&0xFF) << PMP1_CFG_SHIFT))
#define PMPREGION2_LXWR_1000 ((((PMP_L                            )&0xFF) << PMP2_CFG_SHIFT))
#define PMPREGION3_LXWR_1111 ((((PMP_L|PMP_R|PMP_W|PMP_X|PMP_TOR  )&0xFF) << PMP3_CFG_SHIFT))

#ifdef rvtest_strap_routine
    csrw satp, zero                // Disable address translation.
#endif

    LA(x4, -1)
    csrw    pmpaddr15, x4

    //Lock the Background region.
    LI(x4, PMP_REGION_GLOBAL)
    csrw pmpcfg3, x4

    LA(x4, TEST_FOR_EXECUTION)
    addi x5, x4, g
    srl x4, x4, PMP_SHIFT
    csrw pmpaddr0, x4
    csrw pmpaddr2, x4

    srl x5, x5, PMP_SHIFT
    csrw pmpaddr1, x5
    csrw pmpaddr3, x5

//                                          Verification Section
// Test Case: 1 : OFF region does not match, and the first matching region takes priority.

    // Setting pmpcfg0.L = 1, pmpcfg0.A = {TOR,OFF,TOR,OFF}, pmpcfg0.XWR = {111,000,101,000}
    LI(x4, PMPREGION3_LXWR_1111|PMPREGION2_LXWR_1000|PMPREGION1_LXWR_1101|PMPREGION0_LXWR_1000)
    csrw pmpcfg0, x4

    VERIFICATION_RWX   (TEST_FOR_EXECUTION)

    li a4, 0xbeefcafe                                           // Clean Test exit verification signature.
     RVTEST_SIGUPD(x2, x5, x4, a4, test_2_str)                                      // Signature update
    j exit                                                      // Verification Complete, exit the test

.align 13
.align (RVMODEL_PMP_GRAIN+2)
TEST_FOR_EXECUTION:     // Largest Region of size 7*g
    .rept (1<<(RVMODEL_PMP_GRAIN+2))
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
test_1_str: .string "\"test: 1; cp: pmpm_priority_off_lw\""
test_2_str: .string "\"test: 2; cp: pmpm_priority_off\""

RVTEST_DATA_END

// Signature region for self-checking
RVTEST_SIG_SETUP
