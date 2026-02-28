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
// Notes       : - Ensure `rvmodel_macros.h` is configured to match your PMP grain
//                 and PMP region count before running this test.
//               - Adjust PMP configurations for specific hardware if required.
//
// Coverpoints : cp_cfg_L_modify for PMPM is partially covered in this test file.
//
// Test Cases  : Checking that pmpcfg and pmpaddr are unwritable when L = 1.
//               With pmpcfg_i.L ={0/1}, pmpcfg_i.A = OFF, pmpcfg_i.XWR = 111,
//               pmpaddr_i = 0x100, trying to change pmpcfg_i to 000000000,
//               and to change pmpaddr_i to 0s, and reading these back.
//               When L = 1, should be unchanged because of lock.
//               When L = 0, changeable.
//
//               Checking that pmpcfg and pmpaddr of previous region are unwritable
//               when L = 1. With pmpcfg_i.L={0/1}, pmpcfg_i.A=OFF, pmpcfg_i.XWR=111,
//               pmpaddr_i = 0x100, pmpcfg_i-1.L=0 trying to change pmpcfg_i-1 to
//               00000111, and to change pmpaddr_i-1 to 1s and reading these back.
//               pmpaddr_i-1 should be unchanged because of lock iff pmpcfg_i.A = TOR,
//               otherwise change. pmpcfg_i-1 is changeable independent of pmpcfg_i.A.
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
#define TEST_FILE "pmpsm_cfg_L_modify_off.S"
#define SIGUPD_COUNT 50

// Enable trap handler
#define rvtest_mtrap_routine
#define RVTEST_PRIV_TEST

#define SKIP_MEPC

// Include framework macros
#include "riscv_arch_test.h"

// Set up test environment and declare main entry point
RVTEST_BEGIN

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

#define PMP_REGION_GLOBAL   ((PMP_L|PMP_R|PMP_W|PMP_X|PMP_NAPOT)&0xFF)  // Background region with RWX enable.
#define PMPADDRESS_TOP_GLOBAL       -1                                              // All memory region

#ifdef rvtest_strap_routine
    csrw satp, zero                // Disable address translation.
#endif

    LA(x4, PMPADDRESS_TOP_GLOBAL)
    csrw    pmpaddr15, x4

    //Lock the Background region.
    LI(x4, (PMP_REGION_GLOBAL << PMP3_CFG_SHIFT))
    csrw pmpcfg3, x4

//                                          Verification Section
// Test Case 1 : Setting region 1 to be OFF with L->0, XWR->111 and pmpaddr->0x100

    addi x4, x0, 0x100
    csrw pmpaddr1, x4

    LI(x4, ((PMP_R|PMP_W|PMP_X)&0xFF) << PMP1_CFG_SHIFT)
    csrw pmpcfg0, x4

    // Now trying to change pmp0cfg0 to 000000111, and to change pmpaddr0 to 1s.

    addi x5, x4, 7
    csrw pmpcfg0, x5
    addi x4, x0,-1
    tc_1:
    csrw pmpaddr0, x4
    RVTEST_SIGUPD(x2, x5, x4, a4,tc_1,test_1_str)

    // Now trying to change pmp1cfg0 to 000000000, and to change pmpaddr1 to 0s.

    csrw pmpaddr1, x0
    tc_2:
    csrw pmpcfg0, x0
    RVTEST_SIGUPD(x2, x5, x4, a4,tc_2,test_2_str)

//--- Re-initialize the CSRs. ---
    csrw pmpaddr0, x0
    csrw pmpcfg0, x0
//-------------------------------

// Test Case 2 : Setting region 1 to be OFF with L->1, XWR->111 and pmpaddr->0x100

    addi x4, x0, 0x100
    csrw pmpaddr1, x4

    LI(x4, ((PMP_L|PMP_R|PMP_W|PMP_X)&0xFF) << PMP1_CFG_SHIFT)
    csrw pmpcfg0, x4

    // Now trying to change pmp0cfg0 to 000000111, and to change pmpaddr0 to 1s.

    addi x5, x4, 7
    tc_3:
    csrw pmpcfg0, x5
    RVTEST_SIGUPD(x2, x5, x4, a4,tc_3,test_3_str)
    addi x4, x0,-1
    csrw pmpaddr0, x4

    // Now trying to change pmp1cfg0 to 000000000, and to change pmpaddr1 to 0s.

    csrw pmpaddr1, x0
    tc_4:
    csrw pmpcfg0, x0
    RVTEST_SIGUPD(x2, x5, x4, a4,tc_4,test_4_str)

// --------------------------------------------------------------------------------

    j exit                                                      // Verification Complete, exit the test

.align 10
.align (RVMODEL_PMP_GRAIN+2)

exit:

RVTEST_CODE_END

RVTEST_DATA_BEGIN
.align 4

// Test case strings for reporting
canary_mismatch: .string "Testcase signature canary mismatch!"
test_1_str: .string "\"test: 1; cp: cp_cfg_L_modify\""
test_2_str: .string "\"test: 2; cp: cp_cfg_L_modify\""
test_3_str: .string "\"test: 3; cp: cp_cfg_L_modify\""
test_4_str: .string "\"test: 4; cp: cp_cfg_L_modify\""

RVTEST_DATA_END

// Signature region for self-checking
RVTEST_SIG_SETUP
