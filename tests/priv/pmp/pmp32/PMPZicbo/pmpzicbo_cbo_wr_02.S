// ---------------------------------------------------------------------------
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
// Coverpoints : cp_cbo for PMPZicbo is partially covered in this test file.
//
// Test Cases  : Checking that WR bits control access for cbo.*. Attempting all
//                 {cbo.zero, cbo.flush, cbo.clean, cbo.inval} with pmpcfg_i.L=1,
//                 pmpcfg_i.WR = 01, Observing proper access faults for restricted
//                 read/write regions.
// ---------------------------------------------------------------------------

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS:  ['Sm','Zicbom','Zicboz']
# params:
#   MXLEN: 32
#   NUM_PMP_ENTRIES: '>0'
# MARCH: rv32i_zicsr_zicbom_zicboz
##### END_TEST_CONFIG #####

#define TEST_FILE "pmpzicbo_cbo_wr_02.S"
#define SIGUPD_COUNT 50
#define rvtest_mtrap_routine
#define RVTEST_PRIV_TEST
#define SKIP_MEPC

#include "riscv_arch_test.h"

RVTEST_BEGIN

.macro VERIFICATION_RWX ADDRESS TEST_CASE

    // Address must be aligned to the cache block
    LA(a4, \ADDRESS)

    \TEST_CASE\()_1:
    cbo.zero  (a4)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_1, test_1_str)

    \TEST_CASE\()_2:
    cbo.clean (a4)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_2, test_2_str)

    \TEST_CASE\()_3:
    cbo.flush (a4)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_3, test_3_str)

    \TEST_CASE\()_4:
    cbo.inval (a4)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_4, test_4_str)


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

#define PMP_REGION_GLOBAL                ((((PMP_L|PMP_R|PMP_W|PMP_X|PMP_NAPOT)&0xFF) << PMP3_CFG_SHIFT))  // Background region with RWX enable.
#define PMPCFG_1                         ((((PMP_L|PMP_R               |PMP_TOR)&0xFF)   << PMP1_CFG_SHIFT))
#define PMPCFG_0                         ((((PMP_L|PMP_R|PMP_W|PMP_X|PMP_TOR)&0xFF)   << PMP0_CFG_SHIFT))

#define MENVCFG                            0xF0                                                             // menvcfg.CBIE, CBCFE, CBZE = 1
#define PMPADDRESS_TOP_GLOBAL            -1            // All memory region

#ifdef rvtest_strap_routine
    csrw satp, zero                // Disable address translation.
#endif

    LA(x4, PMPADDRESS_TOP_GLOBAL)
    csrw     pmpaddr15, x4

    //Lock the Background region.
    LI(x4, PMP_REGION_GLOBAL)
    csrw pmpcfg3, x4

    li t0, MENVCFG
    csrrs zero, menvcfg, t0

//                                                Verification Section
// Test Case: 2 : {cbo.zero, cbo.flush, cbo.clean, cbo.inval} for XWR-001

    LA(x4, TEST_FOR_EXECUTION_1)
    srl x4, x4, PMP_SHIFT
    csrw pmpaddr0, x4

    LA(x4, TEST_FOR_EXECUTION_2)
    srl x4, x4, PMP_SHIFT
    csrw pmpaddr1, x4

    LI(x4, PMPCFG_1|PMPCFG_0)
    csrw pmpcfg0, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION_1, test_1

    j exit                                        // Verification Complete, exit the test
exit:
RVTEST_CODE_END

RVTEST_DATA_BEGIN

// Test case strings for reporting
test_1_str:  .string "\"test: 1;  cp: pmpzicbo_cbo_zero\""
test_2_str:  .string "\"test: 2;  cp: pmpzicbo_cbo_clean\""
test_3_str:  .string "\"test: 3;  cp: pmpzicbo_cbo_flush\""
test_4_str:  .string "\"test: 4;  cp: pmpzicbo_cbo_inval\""

.align 13
.align (RVMODEL_PMP_GRAIN+2)
TEST_FOR_EXECUTION_1:
    .rept 1024
    nop
    .endr

TEST_FOR_EXECUTION_2:
    .rept 1024
    nop
    .endr

RETURN_INSTRUCTION:
    nop
    nop
    jr ra                                                        // Get back to the point from where TEST_FOR_EXECUTION was called.


RVTEST_DATA_END

// Signature region for self-checking
RVTEST_SIG_SETUP
