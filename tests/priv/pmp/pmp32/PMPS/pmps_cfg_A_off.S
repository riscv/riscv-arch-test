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
# MARCH: rv32i_zicsr
##### END_TEST_CONFIG #####

#define TEST_FILE "pmps_cfg_A_all.S"
#define SIGUPD_COUNT 50
#define rvtest_mtrap_routine
#define rvtest_strap_routine
#define RVTEST_PRIV_TEST
#define SKIP_MEPC

#include "riscv_arch_test.h"

RVTEST_BEGIN

.macro VERIFICATION_RWX ADDRESS TEST_CASE      // {jalr, sw, lw} at start of region
    // Execution Access Check
    LA (a4, \ADDRESS)
    LI(x4, 0xACCE)                        // Store a value which is to be checked in trap handler
    LA(x1, 1f)                            // Store the return Address in x1
    \TEST_CASE\()_1:
    jalr ra, 0(a4)
    nop
1:
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_1, test_1_str)

    // Store Access Check
    LA(a5, \ADDRESS)                                         // Address to be verified
    LI(a4, NOP)                                              // Value to write (NOP)
    \TEST_CASE\()_2:
    sw a4, 0(a5)                                             // Word store test
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_2, test_2_str)

    // Load Access Check
    \TEST_CASE\()_3:
    lw a4, 0(a5)                                             // Word load test
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_3, test_3_str)

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
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_1
    RVTEST_GOTO_MMODE

    j exit                                                        // Verification Complete, exit the test


exit:

RVTEST_CODE_END
RVTEST_DATA_BEGIN

// Test case strings for reporting
test_1_str: .string "\"test: 1; cp: pmps_cfg_A_off_all_jalr\""
test_2_str: .string "\"test: 2; cp: pmps_cfg_A_off_all_sw\""
test_3_str: .string "\"test: 3; cp: pmps_cfg_A_off_all_lw\""

.align 13
TEST_FOR_EXECUTION:
    .rept (1<<(RVMODEL_PMP_GRAIN+2))
    nop
    .endr

RETURN_INSTRUCTION:
    nop
    nop
    jr ra                                                        // Get back to the point from where TEST_FOR_EXECUTION was called.


RVTEST_DATA_END

// Signature region for self-checking
RVTEST_SIG_SETUP
