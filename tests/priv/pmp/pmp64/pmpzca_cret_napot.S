// ---------------------------------------------------------------------------
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
// Notes       : - Ensure `rvmodel_macros.h` is configured to match your PMP grain
//                 and PMP region count before running this test.
//               - Adjust PMP configurations for specific hardware if required.
//
// Coverpoints : cp_cret_napot for PMPZca is fully covered in this test file.
//
// Test Cases  : Check that 16-bit fetches adjacent to a NAPOT PMP boundary succeed.
//               Set up a standard NAPOT PMP region with L=1, XWR = 111. Place four
//               c.ret = c.jr ra statements just below, at bottom, at top, and just
//               above PMP region, half of which are on 16-bit boundaries.
//               Attempt jalr to each c.ret.
//
// Dependencies: model_test.h, arch_test.h
// ---------------------------------------------------------------------------
##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: ['I','Zca','S','Smpmp']
# params:
#   MXLEN: 64
# MARCH: rv64ic_zicsr
# CONFIG_DEPENDENT: true
##### END_TEST_CONFIG #####

// Define the name of this test file for reporting and the size of the signature region
#define TEST_FILE "pmpzca_cret_napot.S"
#define SIGUPD_COUNT 50

// Enable trap handler
#define rvtest_mtrap_routine
#define RVTEST_PRIV_TEST
#define rvtest_strap_routine

#define SKIP_MEPC

// Include framework macros
#include "riscv_arch_test.h"

// Set up test environment and declare main entry point
RVTEST_BEGIN

.macro VERIFICATION_RWX ADDRESS, TEST_CASE
    \TEST_CASE\()_1:
    LA(x15, \ADDRESS)               // Address to be verified
    c.jalr x15
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_1, test_1_str)
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

#define PMP_REGION_GLOBAL   ((((PMP_L|PMP_R|PMP_W|PMP_X|PMP_NAPOT)&0xFF) << PMP7_CFG_SHIFT))  // Background region with RWX enable.
#define PMP0CFG             ((((PMP_L|PMP_R|PMP_W|PMP_X|PMP_NAPOT)&0xFF) << PMP0_CFG_SHIFT))

#define PMPADDRESS_TOP_GLOBAL       -1                                              // All memory region
#define REGIONSTART         0x80002000

#define PMP_MASK            ~((1 << (RVMODEL_PMP_GRAIN - 1))-1)
#define PMP_REGION_SIZE     ((1 << (RVMODEL_PMP_GRAIN - 1))-1)

#if RVMODEL_PMP_GRAIN != 0
  #define STANDARD_REGION   (((REGIONSTART >> PMP_SHIFT) & PMP_MASK) | PMP_REGION_SIZE)
#else
  #define STANDARD_REGION   (REGIONSTART >> PMP_SHIFT)
#endif

#ifdef rvtest_strap_routine
    csrw satp, zero                // Disable address translation.
#endif

    LA(x4, PMPADDRESS_TOP_GLOBAL)
    csrw    pmpaddr15, x4

    //Lock the Background region.
    LI(x4, PMP_REGION_GLOBAL)
    csrw pmpcfg2, x4

//                                          Verification Section
// Test Case: NAPOT Region with L->1 and XWR->111

    LI(x5, STANDARD_REGION)
    csrw pmpaddr0, x5

    LA(x4, PMP0CFG)
    csrw pmpcfg0, x4

     //Test case1
    VERIFICATION_RWX TEST_FOR_EXECUTION_0, test1

    //Test case2
    VERIFICATION_RWX TEST_FOR_EXECUTION_1, test2

    //Test case3
    VERIFICATION_RWX TEST_FOR_EXECUTION_2, test3

    //Test case4
    VERIFICATION_RWX TEST_FOR_EXECUTION_3, test4

    j exit                                                      // Verification Complete, exit the test

.align 12
.align (RVMODEL_PMP_GRAIN+2)
.skip (0x1000 -2)
TEST_FOR_EXECUTION_0:
    ret                                                         // Compressed return just before the start of region

TEST_FOR_EXECUTION_1:
    ret                                                         // Compressed return inside the region
    .rept (((1<<(RVMODEL_PMP_GRAIN+2)) -4 ) /2)                     // (size of region - size of 2 returns) / size of nop
    nop
    .endr

TEST_FOR_EXECUTION_2:
    ret                                                         // Compressed return at the top of the region

TEST_FOR_EXECUTION_3:
    ret                                                         // Compressed return just above the region
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
test_1_str: .string "\"test: 1; cp: pmpzca_cret_napot_execute\""

RVTEST_DATA_END

// Signature region for self-checking
RVTEST_SIG_SETUP
