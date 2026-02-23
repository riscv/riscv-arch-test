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
// Coverpoints: cp_grain for PMPM is fully covered in this test file.
//
// Test case  : Checking that low bits read as 0/1s depending on grain and address
//                matching mode. Set up pmpcfg0.L = 0, pmpcfg.A = {OFF/NAPOT}, write
//                pmpaddr0 = {all 0s / all 1s / checkerboard}. Change pmpcfg.A to
//                {OFF/TOR/NAPOT} and read back pmpaddr0. Bottom G-1 bits always read
//                as 1s in NAPOT. Bottom G bits read as 0s in TOR/OFF.
//
// Dependencies: model_test.h, arch_test.h
// --------------------------------------------------------------------------------

#define SKIP_MEPC
##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: ['I','S','Smpmp']
# MARCH: rv64i_zicsr
# CONFIG_DEPENDENT: true
##### END_TEST_CONFIG #####

// Define the name of this test file for reporting and the size of the signature region
#define TEST_FILE "pmpm_grain.S"
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

#define NOP             0x13

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

#define PMP_REGION_GLOBAL    ((((PMP_L|PMP_R|PMP_W|PMP_X|PMP_NAPOT) &0xFF) << PMP7_CFG_SHIFT))  // Background region with RWX enable.
#define PMPREGION_OFF          ((((     PMP_R|PMP_W|PMP_X)               &0xFF) << PMP0_CFG_SHIFT))
#define PMPREGION_NAPOT     ((((     PMP_R|PMP_W|PMP_X |PMP_NAPOT) &0xFF) << PMP0_CFG_SHIFT))
#define PMPREGION_TOR          ((((     PMP_R|PMP_W|PMP_X |PMP_TOR)   &0xFF) << PMP0_CFG_SHIFT))

#define PMPADDRESS_TOP_GLOBAL        -1                                                // All memory region
#define REGIONSTART            0x80002000        // RAM_BASE_ADDR + PROGRAM_SIZE
#define PMP_ADDRESS            (REGIONSTART >> PMP_SHIFT)
#define CHECKERBOARD        0xAAAAAAAAAAAAAAAA

#ifdef rvtest_strap_routine
    csrw satp, zero                // Disable address translation.
#endif

    LA(x4, PMPADDRESS_TOP_GLOBAL)
    csrw     pmpaddr15, x4

    //Lock the Background region
    LI(x4, PMP_REGION_GLOBAL)
    csrw pmpcfg2, x4

    LA(x4, PMP_ADDRESS)
    csrw     pmpaddr0, x4
                                                //Verification Section
// Test Case 1: Writing all 0s in pmpaddr0 when A = NAPOT and read back when A= {OFF,NAPOT,TOR}

// Write all 0s in NAPOT

    LI(x6, PMPREGION_NAPOT)
    csrw pmpcfg0, x6
    li x6, 0
    csrw pmpaddr0, x6

// Read back in OFF

    LI(x6, PMPREGION_OFF)
    csrw pmpcfg0, x6
    csrr x7, pmpaddr0

// Write all 0s in NAPOT

    LI(x6, PMPREGION_NAPOT)
    csrw pmpcfg0, x6
    li x6, 0
    csrw pmpaddr0, x6

// Read back in NAPOT

    LI(x6, PMPREGION_NAPOT)
    csrw pmpcfg0, x6
    csrr x7, pmpaddr0

// Write all 0s in NAPOT

    LI(x6, PMPREGION_NAPOT)
    csrw pmpcfg0, x6
    li x6, 0
    csrw pmpaddr0, x6

// Read back in TOR

    LI(x6, PMPREGION_TOR)
    csrw pmpcfg0, x6
    csrr x7, pmpaddr0

// Test Case 2: Writing all 0s in pmpaddr0 when A = OFF and read back when A= {OFF,NAPOT,TOR}

// Write all 0s in OFF

    LI(x6, PMPREGION_OFF)
    csrw pmpcfg0, x6
    li x6, 0
    csrw pmpaddr0, x6

// Read back in OFF

    LI(x6, PMPREGION_OFF)
    csrw pmpcfg0, x6
    csrr x7, pmpaddr0

// Write all 0s in OFF

    LI(x6, PMPREGION_OFF)
    csrw pmpcfg0, x6
    li x6, 0
    csrw pmpaddr0, x6

// Read back in NAPOT

    LI(x6, PMPREGION_NAPOT)
    csrw pmpcfg0, x6
    csrr x7, pmpaddr0

// Write all 0s in OFF

    LI(x6, PMPREGION_OFF)
    csrw pmpcfg0, x6
    li x6, 0
    csrw pmpaddr0, x6

// Read back in TOR

    LI(x6, PMPREGION_TOR)
    csrw pmpcfg0, x6
    csrr x7, pmpaddr0

// Test Case 3: Writing all 1s in pmpaddr0 when A = NAPOT and read back when A= {OFF,NAPOT,TOR}

// Write all 1s in NAPOT

    LI(x6, PMPREGION_NAPOT)
    csrw pmpcfg0, x6
    li x6, -1
    csrw pmpaddr0, x6

// Read back in OFF

    LI(x6, PMPREGION_OFF)
    csrw pmpcfg0, x6
    csrr x7, pmpaddr0

// Write all 1s in NAPOT

    LI(x6, PMPREGION_NAPOT)
    csrw pmpcfg0, x6
    li x6, -1
    csrw pmpaddr0, x6

// Read back in NAPOT

    LI(x6, PMPREGION_NAPOT)
    csrw pmpcfg0, x6
    csrr x7, pmpaddr0

// Write all 1s in NAPOT

    LI(x6, PMPREGION_NAPOT)
    csrw pmpcfg0, x6
    li x6, -1
    csrw pmpaddr0, x6

// Read back in TOR

    LI(x6, PMPREGION_TOR)
    csrw pmpcfg0, x6
    csrr x7, pmpaddr0

// Test Case 4: Writing all 1s in pmpaddr0 when A = OFF and read back when A= {OFF,NAPOT,TOR}

// Write all 1s in OFF

    LI(x6, PMPREGION_OFF)
    csrw pmpcfg0, x6
    li x6, -1
    csrw pmpaddr0, x6

// Read back in OFF

    LI(x6, PMPREGION_OFF)
    csrw pmpcfg0, x6
    csrr x7, pmpaddr0

// Write all 1s in OFF

    LI(x6, PMPREGION_OFF)
    csrw pmpcfg0, x6
    li x6, -1
    csrw pmpaddr0, x6

// Read back in NAPOT

    LI(x6, PMPREGION_NAPOT)
    csrw pmpcfg0, x6
    csrr x7, pmpaddr0

// Write all 1s in OFF

    LI(x6, PMPREGION_OFF)
    csrw pmpcfg0, x6
    li x6, -1
    csrw pmpaddr0, x6

// Read back in TOR

    LI(x6, PMPREGION_TOR)
    csrw pmpcfg0, x6
    csrr x7, pmpaddr0

// Test Case 5: Writing checkerboard pattern(1010...) in pmpaddr0 when A = NAPOT and read back when A= {OFF,NAPOT,TOR}

// Write checkerboard in NAPOT

    LI(x6, PMPREGION_NAPOT)
    csrw pmpcfg0, x6
    LI(x6, CHECKERBOARD)
    csrw pmpaddr0, x6

// Read back in OFF

    LI(x6, PMPREGION_OFF)
    csrw pmpcfg0, x6
    csrr x7, pmpaddr0

// Write checkerboard in NAPOT

    LI(x6, PMPREGION_NAPOT)
    csrw pmpcfg0, x6
    LI(x6, CHECKERBOARD)
    csrw pmpaddr0, x6

// Read back in NAPOT

    LI(x6, PMPREGION_NAPOT)
    csrw pmpcfg0, x6
    csrr x7, pmpaddr0

// Write checkerboard in NAPOT

    LI(x6, PMPREGION_NAPOT)
    csrw pmpcfg0, x6
    LI(x6, CHECKERBOARD)
    csrw pmpaddr0, x6

// Read back in TOR

    LI(x6, PMPREGION_TOR)
    csrw pmpcfg0, x6
    csrr x7, pmpaddr0

// Test Case 6: Writing checkerboard pattern(1010...) in pmpaddr0 when A = OFF and read back when A= {OFF,NAPOT,TOR}

// Write checkerboard in OFF

    LI(x6, PMPREGION_OFF)
    csrw pmpcfg0, x6
    LI(x6, CHECKERBOARD)
    csrw pmpaddr0, x6

// Read back in OFF

    LI(x6, PMPREGION_OFF)
    csrw pmpcfg0, x6
    csrr x7, pmpaddr0

// Write checkerboard in OFF

    LI(x6, PMPREGION_OFF)
    csrw pmpcfg0, x6
    LI(x6, CHECKERBOARD)
    csrw pmpaddr0, x6

// Read back in NAPOT

    LI(x6, PMPREGION_NAPOT)
    csrw pmpcfg0, x6
    csrr x7, pmpaddr0

// Write checkerboard in OFF

    LI(x6, PMPREGION_OFF)
    csrw pmpcfg0, x6
    LI(x6, CHECKERBOARD)
    csrw pmpaddr0, x6

// Read back in TOR

    LI(x6, PMPREGION_TOR)
    csrw pmpcfg0, x6
    csrr x7, pmpaddr0

    RVTEST_GOTO_MMODE

    li a4, 0xbeefcafe                                            // Clean Test exit verification signature.
    RVTEST_SIGUPD(x2, x5, x4, a4, test_1_str)                                       // Signature update
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
test_1_str: .string "\"test: 1; cp: cp_pmp_grain\""

RVTEST_DATA_END

// Signature region for self-checking
RVTEST_SIG_SETUP
