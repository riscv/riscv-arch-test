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
// Coverpoints : cp_cfg_RW for PMPZaamo is fully covered in this test file.
//
// Test Cases  : Checking that WR bits control write/read access for every type
//               of amo. Attempt all accesses with pmpcfg_i.L=1, all legal
//               pmpcfg_i.XWR. Observing proper access faults for restricted
//               read/write regions
// --------------------------------------------------------------------------------

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS:  ['Zaamo','Sm']
# params:
#   MXLEN: 64
#   NUM_PMP_ENTRIES: '>0'
# MARCH: rv64i_zicsr_zaamo
##### END_TEST_CONFIG #####

#define TEST_FILE "pmpzaamo_cfg_wr.S"
#define SIGUPD_COUNT 120
#define rvtest_mtrap_routine
#define RVTEST_PRIV_TEST
#define SKIP_MEPC

#include "riscv_arch_test.h"

RVTEST_BEGIN

.macro VERIFICATION_RWX ADDRESS TEST_CASE

    LI(a6, DOUBLE_NOP)
    LA(a5, \ADDRESS)                                         // Address to be verified

    \TEST_CASE\()_1:
    amoadd.w a4, a6, (a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_1, test_1_str)                                   // Signature update


    \TEST_CASE\()_2:
    amoadd.d a4, a6, (a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_2, test_2_str)                                   // Signature update


    \TEST_CASE\()_3:
    amoand.w a4, a6, (a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_3, test_3_str)                                   // Signature update


    \TEST_CASE\()_4:
    amoand.d a4, a6, (a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_4, test_4_str)                                   // Signature update


    \TEST_CASE\()_5:
    amoor.w a4, a6, (a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_5, test_5_str)                                   // Signature update


    \TEST_CASE\()_6:
    amoor.d a4, a6, (a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_6, test_6_str)                                   // Signature update


    \TEST_CASE\()_7:
    amoxor.w a4, a6, (a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_7, test_7_str)                                   // Signature update


    \TEST_CASE\()_8:
    amoxor.d a4, a6, (a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_8, test_8_str)                                   // Signature update


    \TEST_CASE\()_9:
    amomax.w a4, a6, (a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_9, test_9_str)                                   // Signature update


    \TEST_CASE\()_10:
    amomax.d a4, a6, (a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_10, test_10_str)                                   // Signature update


    \TEST_CASE\()_11:
    amomaxu.w a4, a6, (a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_11, test_11_str)                                   // Signature update


    \TEST_CASE\()_12:
    amomaxu.d a4, a6, (a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_12, test_12_str)                                   // Signature update


    \TEST_CASE\()_13:
    amomin.w a4, a6, (a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_13, test_13_str)                                   // Signature update


    \TEST_CASE\()_14:
    amomin.d a4, a6, (a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_14, test_14_str)                                   // Signature update


    \TEST_CASE\()_15:
    amominu.w a4, a6, (a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_15, test_15_str)                                   // Signature update


    \TEST_CASE\()_16:
    amominu.d a4, a6, (a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_16, test_16_str)                                   // Signature update


    \TEST_CASE\()_17:
    amoswap.w a4, a6, (a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_17, test_17_str)                                   // Signature update


    \TEST_CASE\()_18:
    amoswap.d a4, a6, (a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_18, test_18_str)                                   // Signature update


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
test_1_str:  .string "\"test: 1;  cp: pmpzaamo_cfg_wr_amoadd_w\""
test_2_str:  .string "\"test: 2;  cp: pmpzaamo_cfg_wr_amoadd_d\""

test_3_str:  .string "\"test: 3;  cp: pmpzaamo_cfg_wr_amoand_w\""
test_4_str:  .string "\"test: 4;  cp: pmpzaamo_cfg_wr_amoand_d\""

test_5_str:  .string "\"test: 5;  cp: pmpzaamo_cfg_wr_amoor_w\""
test_6_str:  .string "\"test: 6;  cp: pmpzaamo_cfg_wr_amoor_d\""

test_7_str:  .string "\"test: 7;  cp: pmpzaamo_cfg_wr_amoxor_w\""
test_8_str:  .string "\"test: 8;  cp: pmpzaamo_cfg_wr_amoxor_d\""

test_9_str:  .string "\"test: 9;  cp: pmpzaamo_cfg_wr_amomax_w\""
test_10_str: .string "\"test: 10; cp: pmpzaamo_cfg_wr_amomax_d\""

test_11_str: .string "\"test: 11; cp: pmpzaamo_cfg_wr_amomaxu_w\""
test_12_str: .string "\"test: 12; cp: pmpzaamo_cfg_wr_amomaxu_d\""

test_13_str: .string "\"test: 13; cp: pmpzaamo_cfg_wr_amomin_w\""
test_14_str: .string "\"test: 14; cp: pmpzaamo_cfg_wr_amomin_d\""

test_15_str: .string "\"test: 15; cp: pmpzaamo_cfg_wr_amominu_w\""
test_16_str: .string "\"test: 16; cp: pmpzaamo_cfg_wr_amominu_d\""

test_17_str: .string "\"test: 17; cp: pmpzaamo_cfg_wr_amoswap_w\""
test_18_str: .string "\"test: 18; cp: pmpzaamo_cfg_wr_amoswap_d\""

.align 12
.align (RVMODEL_PMP_GRAIN+2)
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
