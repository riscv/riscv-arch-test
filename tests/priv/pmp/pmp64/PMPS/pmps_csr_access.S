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
// Coverpoints : cp_pmpaddr_access_u and cp_pmpcfg_access_u are fully covered in
//                 this test file.
//
// Test Cases  : Test pmpcfg and pmpaddr access from S-mode. Trying to write
//               all 64 pmpaddr and 16 pmpcfg registers. Should throw illegal
//               instruction faults because PMP CSRs are only accessible to
//               M-mode.
//
// --------------------------------------------------------------------------------

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS:  ['S']
# params:
#   MXLEN: 64
#   NUM_PMP_ENTRIES: '>0'
# MARCH: rv64i_zicsr
##### END_TEST_CONFIG #####

#define TEST_FILE "pmps_csr_access.S"
#define SIGUPD_COUNT 100
#define rvtest_mtrap_routine
#define rvtest_strap_routine
#define RVTEST_PRIV_TEST
#define SKIP_MEPC

#include "riscv_arch_test.h"

RVTEST_BEGIN

#define PMP_REGION_GLOBAL    ((((PMP_L|PMP_R|PMP_W|PMP_X|PMP_NAPOT)&0xFF) << PMP7_CFG_SHIFT))  // Background region with RWX enable.
#define PMPADDRESS_TOP_GLOBAL        -1                                                // All memory region

    csrw satp, zero                // Disable address translation.

    LA(x4, PMPADDRESS_TOP_GLOBAL)
    csrw     pmpaddr15, x4

    //Lock the Background region.
    LI(x4, PMP_REGION_GLOBAL)
    csrw pmpcfg2, x4

main:

// Trying to access PMP CSRs in S-mode by writing all 1s.

    // Value to write in PMP CSRs in S-mode
    LA(x4, -1)

    .set pmpaddri, CSR_PMPADDR0
    .rept 64
    RVTEST_GOTO_LOWER_MODE    Smode        // SWITCH TO S-mode
    99:
    RVTEST_SIGUPD_CSR_WRITE(pmpaddri, x4, 99b, test_1_str)
    nop
    RVTEST_GOTO_MMODE
    .set pmpaddri, pmpaddri+1
    .endr

    .set pmpcfgi, CSR_PMPCFG0
    .rept 16
    RVTEST_GOTO_LOWER_MODE    Smode        // SWITCH TO S-mode
    99:
    RVTEST_SIGUPD_CSR_WRITE(pmpcfgi, x4, 99b, test_2_str)
    nop
    RVTEST_GOTO_MMODE
    .set pmpcfgi, pmpcfgi+1
    .endr

    j exit                                                        // Verification Complete, exit the test

.align 10
.align (RVMODEL_PMP_GRAIN+2)
RETURN_INSTRUCTION:
    nop
    nop
    jr ra                                                        // Get back to the point from where TEST_FOR_EXECUTION was called.

exit:

RVTEST_CODE_END
RVTEST_DATA_BEGIN
.align 4

// Test case strings for reporting
test_1_str: .string "\"test: 1; cp: cp_pmpaddr_access_s\""
test_2_str: .string "\"test: 2; cp: cp_pmpcfg_access_s\""

RVTEST_DATA_END

// Signature region for self-checking
RVTEST_SIG_SETUP
