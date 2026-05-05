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
// Coverpoints : cp_cfg_RW for PMPZalrsc is fully covered in this test file.
//
// Test Cases  : Checking that WR bits control write/read access for every type
//               of load and store. Attempt {lr.w,sc.w} with pmpcfg_i.L=1, all
//               legal pmpcfg_i.XWR. Observing proper access faults for restricted
//               read/write regions.
//
// --------------------------------------------------------------------------------

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS:  ['Zalrsc','Sm']
# params:
#   MXLEN: 64
#   NUM_PMP_ENTRIES: '>0'
# MARCH: rv64i_zicsr_zalrsc
##### END_TEST_CONFIG #####

#define TEST_FILE "pmpzalrsc_cfg_wrS"
#define SIGUPD_COUNT 100
#define rvtest_mtrap_routine
#define RVTEST_PRIV_TEST
#define SKIP_MEPC

#include "riscv_arch_test.h"

RVTEST_BEGIN

.macro VERIFICATION_RWX ADDRESS  TEST_CASE

    LA(a5, \ADDRESS)                                         // Address to be verified

    \TEST_CASE\()_1:
    lr.w a2, (a5)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a2, \TEST_CASE\()_1, test_1_str)


    \TEST_CASE\()_2:
    sc.w a2, a2, (a5)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a2, \TEST_CASE\()_2, test_2_str)

    LA(a5, \ADDRESS)                                         // Address to be verified

    \TEST_CASE\()_3:
    lr.d a2, (a5)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a2, \TEST_CASE\()_3, test_3_str)


    \TEST_CASE\()_4:
    sc.d a2, a2, (a5)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a2, \TEST_CASE\()_4, test_4_str)


.endm

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

#define PMP_REGION_GLOBAL    ((((PMP_L|PMP_R|PMP_W|PMP_X|PMP_NAPOT)&0xFF) << PMP7_CFG_SHIFT))  // Background region with RWX enable.
#define PMPREGION_LXWR_1000 ((((PMP_L|                  PMP_NAPOT)&0xFF) << PMP5_CFG_SHIFT))
#define PMPREGION_LXWR_1001 ((((PMP_L|PMP_R|            PMP_NAPOT)&0xFF) << PMP4_CFG_SHIFT))
#define PMPREGION_LXWR_1011 ((((PMP_L|PMP_R|PMP_W       |PMP_NAPOT)&0xFF) << PMP3_CFG_SHIFT))
#define PMPREGION_LXWR_1100 ((((PMP_L|              PMP_X|PMP_NAPOT)&0xFF) << PMP2_CFG_SHIFT))
#define PMPREGION_LXWR_1101 ((((PMP_L|PMP_R         |PMP_X|PMP_NAPOT)&0xFF) << PMP1_CFG_SHIFT))
#define PMPREGION_LXWR_1111 ((((PMP_L|PMP_R|PMP_W|PMP_X|PMP_NAPOT)&0xFF) << PMP0_CFG_SHIFT))

#define PMPADDRESS_TOP_GLOBAL        -1                                                // All memory region
#define REGIONSTART            TEST_FOR_EXECUTION
#if RVMODEL_PMP_GRAIN != 0
    #define PMP_MASK            ~((1 << (RVMODEL_PMP_GRAIN - 1))-1)
    #define PMP_REGION_SIZE     (1 << (RVMODEL_PMP_GRAIN - 1)) - 1
#else
    #define PMP_MASK            ~0
    #define PMP_REGION_SIZE     0
#endif

#ifdef rvtest_strap_routine
    csrw satp, zero                // Disable address translation.
#endif

    LA(x4, PMPADDRESS_TOP_GLOBAL)
    csrw     pmpaddr15, x4

    //Lock the Background region.
    LI(x4, PMP_REGION_GLOBAL)
    csrw pmpcfg2, x4

//                                            Verification Section
// Test Case: 1 : L -> 1 and No Permissions given to the PMP Region 5

    LA(x5, REGIONSTART)
    srl x5, x5, PMP_SHIFT
    andi x5, x5, PMP_MASK
    ori x5, x5, PMP_REGION_SIZE
    csrw pmpaddr5, x5

    LI(x4, PMPREGION_LXWR_1000)
    csrw pmpcfg0, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_1

// Test Case: 2 : L -> 1 and R Permissions given to the PMP Region 4

    LA(x5, REGIONSTART)
    srl x5, x5, PMP_SHIFT
    andi x5, x5, PMP_MASK
    ori x5, x5, PMP_REGION_SIZE
    csrw pmpaddr4, x5

    LI(x4, PMPREGION_LXWR_1001)
    csrw pmpcfg0, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_2

// Test Case: 3 : L -> 1 and WR Permissions given to the PMP Region 3

    LA(x5, REGIONSTART)
    srl x5, x5, PMP_SHIFT
    andi x5, x5, PMP_MASK
    ori x5, x5, PMP_REGION_SIZE
    csrw pmpaddr3, x5

    LI(x4, PMPREGION_LXWR_1011)
    csrw pmpcfg0, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_3

// Test Case: 4 : L -> 1 and X Permissions given to the PMP Region 2

    LA(x5, REGIONSTART)
    srl x5, x5, PMP_SHIFT
    andi x5, x5, PMP_MASK
    ori x5, x5, PMP_REGION_SIZE
    csrw pmpaddr2, x5

    LI(x4, PMPREGION_LXWR_1100)
    csrw pmpcfg0, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_4

// Test Case: 5 : L -> 1 and XR Permissions given to the PMP Region 1

    LA(x5, REGIONSTART)
    srl x5, x5, PMP_SHIFT
    andi x5, x5, PMP_MASK
    ori x5, x5, PMP_REGION_SIZE
    csrw pmpaddr1, x5

    LI(x4, PMPREGION_LXWR_1101)
    csrw pmpcfg0, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_5

// Test Case: 6 : L -> 1 and XWR Permissions given to the PMP Region 0

    LA(x5, REGIONSTART)
    srl x5, x5, PMP_SHIFT
    andi x5, x5, PMP_MASK
    ori x5, x5, PMP_REGION_SIZE
    csrw pmpaddr0, x5

    LI(x4, PMPREGION_LXWR_1111)
    csrw pmpcfg0, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_6


    j exit                                                        // Verification Complete, exit the test
exit:

RVTEST_CODE_END

RVTEST_DATA_BEGIN
.align 4

// Test case strings for reporting
test_1_str:  .string "\"test: 1;  cp: pmpzalrc_cfg_wr_lr_w\""
test_2_str:  .string "\"test: 2;  cp: pmpzalrc_cfg_wr_sc_w\""
test_3_str:  .string "\"test: 3;  cp: pmpzalrc_cfg_wr_lr_f\""
test_4_str:  .string "\"test: 4;  cp: pmpzalrc_cfg_wr_sc_d\""

.align 12
.align (RVMODEL_PMP_GRAIN+2)
TEST_FOR_EXECUTION_0:
    jr ra

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
