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
//                 pmpcfg_i.WR = 11, Observing proper access faults for restricted
//                 read/write regions.
// ---------------------------------------------------------------------------

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS:  ['Sm','Zicbom','Zicboz']
# params:
#   MXLEN: 64
#   NUM_PMP_ENTRIES: '>0'
# MARCH: rv64i_zicsr_zifencei_zicbom_zicboz
##### END_TEST_CONFIG #####

#define TEST_FILE "pmpzicbo_cbo_wr_01.S"
#define SIGUPD_COUNT 50
#define rvtest_mtrap_routine
#define RVTEST_PRIV_TEST


#include "riscv_arch_test.h"

RVTEST_BEGIN


main:
    // Loop to SET ALL pmpcfg REGs to zero
    .set pmpcfgi, CSR_PMPCFG0
    .rept UDB_NUM_PMP_ENTRIES/8
    csrw pmpcfgi , x0
    .set pmpcfgi, pmpcfgi+2
    .endr

    // Loop to SET ALL pmpaddr REGs to zero
    .set pmpaddri, CSR_PMPADDR0
    .rept UDB_NUM_PMP_ENTRIES
    csrw pmpaddri, x0
    .set pmpaddri, pmpaddri+1
    .endr


#define PMPCFG_0                         ((((PMP_L|PMP_R|PMP_W       |PMP_NAPOT)&0xFF)   << PMP0_CFG_SHIFT))

#define REGIONSTART                       TEST_FOR_EXECUTION_1
#if UDB_PMP_GRANULARITY > 12
    #define PMPZICBO_REGION_SHIFT         UDB_PMP_GRANULARITY
#else
    #define PMPZICBO_REGION_SHIFT         12
#endif
#define PMP_MASK                          ~((1 << (PMPZICBO_REGION_SHIFT - 3))-1)
#define PMP_REGION_SIZE                   ((1 << (PMPZICBO_REGION_SHIFT - 3)) - 1)

#define MENVCFG                            0xF0                                                             // menvcfg.CBIE, CBCFE, CBZE = 1



    RVTEST_PMP_SET_BACKGROUND x4

    li t0, MENVCFG
    csrrs zero, menvcfg, t0

//                                                Verification Section
// Test Case: 3 : {cbo.zero, cbo.flush, cbo.clean, cbo.inval} for XWR-011

    LA(x4, REGIONSTART)
    srl x4, x4, PMP_SHIFT
    LI(x6, PMP_MASK)
    and x4, x4, x6
    LI(x6, PMP_REGION_SIZE)
    or x4, x4, x6
    csrw pmpaddr0, x4

    LI(x4, PMPCFG_0)
    csrw pmpcfg0, x4

    PMP_VERIFICATION_CBO    TEST_FOR_EXECUTION_1, test_1

    j exit                                        // Verification Complete, exit the test
exit:
RVTEST_CODE_END

RVTEST_DATA_BEGIN

// Test case strings for reporting
test_1_str:  .string "\"test: 1;  cp: pmpzicbo_cbo_zero\""
test_2_str:  .string "\"test: 2;  cp: pmpzicbo_cbo_clean\""
test_3_str:  .string "\"test: 3;  cp: pmpzicbo_cbo_flush\""
test_4_str:  .string "\"test: 4;  cp: pmpzicbo_cbo_inval\""

.p2align 12
.p2align (UDB_PMP_GRANULARITY)
TEST_FOR_EXECUTION_1:
    .rept 1024
    nop
    .endr

.p2align (UDB_PMP_GRANULARITY)
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
