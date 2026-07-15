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
// Coverpoints : cp_cfg_A_off for PMPS is fully covered in this test file.
//
// Test Cases  : Checking that A=OFF never matches a region. Configuring
//                 PMP in M and switching to S mode. For pmpaddr with all 1s
//                 pmpcfg.L=0, pmpcfg.A=OFF, pmpcfg.XWR=000. Fetching, reading
//                 and writing from that region. Should succeed because region
//                 is off even though inaccessible.
// --------------------------------------------------------------------------------

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS:  ['S']
# params:
#   MXLEN: 32
#   NUM_PMP_ENTRIES: '>0'
# MARCH: rv32i_zicsr_zifencei
##### END_TEST_CONFIG #####

#define TEST_FILE "pmps_cfg_A_all.S"
#define SIGUPD_COUNT 50
#define rvtest_mtrap_routine
#define rvtest_strap_routine
#define RVTEST_PRIV_TEST


#include "riscv_arch_test.h"

RVTEST_BEGIN


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


#define PMP_REGION_GLOBAL    ((PMP_L|PMP_R|PMP_W|PMP_X|PMP_NAPOT)&0xFF)      // Background region with RWX enable.
#define PMPADDRESS_TOP_GLOBAL        -1                                        // All memory region

    csrw satp, zero                // Disable address translation.


    LA(x4, PMPADDRESS_TOP_GLOBAL)
    csrw     pmpaddr15, x4

    //Lock the Background region.
    LI(x4, (PMP_REGION_GLOBAL<<24))
    csrw pmpcfg3, x4

    LA(x4, -1)
    // Putting all 1s in pmpaddr0
    csrw pmpaddr0, x4

//                                            Verification Section
// Test Case: 1 -- No Permissions given to the PMP Region 0

    csrw pmpcfg0, x0        // pmp0cfg0.L = 0, pmp0cfg0.A = OFF and pmp0cfg0.WXR = 000

    RVTEST_GOTO_LOWER_MODE    Smode        // SWITCH TO S-mode
    PMP_VERIFICATION_RWX    TEST_FOR_EXECUTION, test_1
    RVTEST_GOTO_MMODE

    j exit                                                        // Verification Complete, exit the test


exit:

RVTEST_CODE_END
RVTEST_DATA_BEGIN

// Test case strings for reporting
test_1_str: .string "\"test: 1; cp: pmps_cfg_A_off_all_jalr\""
test_2_str: .string "\"test: 2; cp: pmps_cfg_A_off_all_sw\""
test_3_str: .string "\"test: 3; cp: pmps_cfg_A_off_all_lw\""

.p2align 12
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
