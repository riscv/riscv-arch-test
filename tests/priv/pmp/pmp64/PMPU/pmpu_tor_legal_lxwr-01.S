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
// Coverpoints : cp_cfg_A_tor for PMPU is partially covered in this test file.
//
// Test Cases  : Configuring PMP in M mode and then switching to U mode.
//               Checking XWR controls accesses in matching TOR region. With
//               pmpcfg_i.L =1, pmpcfg_i.A = TOR, all legal pmpcfg_i.XWR,
//               default TOR region, address-g in pmpaddr_i-1: making {lw,sw,jalr}
//               address, address-4, address-g, address-g-4.  Observing proper
//               access faults for restricted regions.
// --------------------------------------------------------------------------------
##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS:  ['U']
# params:
#   MXLEN: 64
#   NUM_PMP_ENTRIES: '>0'
#   PMP_NAPOT_SUPPORTED: true
#   PMP_TOR_SUPPORTED: true
# MARCH: rv64i_zicsr_zifencei
##### END_TEST_CONFIG #####

#define TEST_FILE "pmpu_tor_legal_lxwr.S"
#define SIGUPD_COUNT 150
#define rvtest_mtrap_routine
#define RVTEST_PRIV_TEST


#include "riscv_arch_test.h"

RVTEST_BEGIN

#define g    (1<<(UDB_PMP_GRANULARITY))


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

#define PMP_REGION_GLOBAL    ((((PMP_L|PMP_R|PMP_W|PMP_X|PMP_NAPOT)&0xFF) << PMP7_CFG_SHIFT))  // Background region with RWX enable.
#define PMPREGION_LXWR_0000 ((((                        PMP_TOR  )&0xFF) << PMP3_CFG_SHIFT))
#define PMPREGION_LXWR_0001 ((((      PMP_R|            PMP_TOR  )&0xFF) << PMP1_CFG_SHIFT))
#define PMPREGION_LXWR_0011 ((((      PMP_R|PMP_W       |PMP_TOR  )&0xFF) << PMP7_CFG_SHIFT))
#define PMPREGION_LXWR_0100 ((((                    PMP_X|PMP_TOR  )&0xFF) << PMP5_CFG_SHIFT))
#define PMPREGION_LXWR_0101 ((((      PMP_R         |PMP_X|PMP_TOR  )&0xFF) << PMP3_CFG_SHIFT))
#define PMPREGION_LXWR_0111 ((((      PMP_R|PMP_W|PMP_X|PMP_TOR  )&0xFF) << PMP1_CFG_SHIFT))

#define PMPADDRESS_TOP_GLOBAL        -1                                                // All memory region
#define REGIONSTART            TEST_FOR_EXECUTION        // RAM_BASE_ADDR + PROGRAM_SIZE

#ifdef S_SUPPORTED
    csrw satp, zero                // Disable address translation.
#endif

    LA(x4, PMPADDRESS_TOP_GLOBAL)
    csrw     pmpaddr15, x4

    //Lock the Background region.
    LI(x4, PMP_REGION_GLOBAL)
    csrw pmpcfg2, x4

//                                            Verification Section
// Test Case: 1 : L -> 0 and No Permissions given to the PMP Region 11

    LA(x6, REGIONSTART)
    li t0, g
    add x6, x6, t0
    srl x6, x6, PMP_SHIFT
    csrw pmpaddr11, x6
    LA(x5, REGIONSTART)
    srl x5, x5, PMP_SHIFT
    csrw pmpaddr10, x5
    LI(x4, PMPREGION_LXWR_0000)
    csrw pmpcfg2, x4

    RVTEST_GOTO_LOWER_MODE    Umode        // SWITCH TO U-mode
    PMP_VERIFICATION_RWX_LEGAL    TEST_FOR_EXECUTION, test_1
    RVTEST_GOTO_MMODE

// Test Case: 2 : L -> 0 and R Permissions given to the PMP Region 9

    LA(x6, REGIONSTART)
    li t0, g
    add x6, x6, t0
    srl x6, x6, PMP_SHIFT
    csrw pmpaddr9, x6
    LA(x5, REGIONSTART)
    srl x5, x5, PMP_SHIFT
    csrw pmpaddr8, x5
    LI(x4, PMPREGION_LXWR_0001)
    csrw pmpcfg2, x4

    RVTEST_GOTO_LOWER_MODE    Umode        // SWITCH TO U-mode
    PMP_VERIFICATION_RWX_LEGAL    TEST_FOR_EXECUTION, test_2
    RVTEST_GOTO_MMODE

// Test Case: 3 : L -> 0 and WR Permissions given to the PMP Region 7

    LA(x6, REGIONSTART)
    li t0, g
    add x6, x6, t0
    srl x6, x6, PMP_SHIFT
    csrw pmpaddr7, x6
    LA(x5, REGIONSTART)
    srl x5, x5, PMP_SHIFT
    csrw pmpaddr6, x5
    LI(x4, PMPREGION_LXWR_0011)
    csrw pmpcfg0, x4

    RVTEST_GOTO_LOWER_MODE    Umode        // SWITCH TO U-mode
    PMP_VERIFICATION_RWX_LEGAL    TEST_FOR_EXECUTION, test_3
    RVTEST_GOTO_MMODE

    j exit                                                        // Verification Complete, exit the test

exit:

RVTEST_CODE_END

RVTEST_DATA_BEGIN
.p2align 4

// Test case strings for reporting
test_1_str:  .string "\"test: 1; cp: cp_cfg_A_tor_jalr_address\""
test_2_str:  .string "\"test: 2; cp: cp_cfg_A_tor_jalr_address-4\""
test_3_str:  .string "\"test: 3; cp: cp_cfg_A_tor_jalr_address+4\""
test_4_str:  .string "\"test: 4; cp: cp_cfg_A_tor_jalr_address+g-4\""
test_5_str:  .string "\"test: 5; cp: cp_cfg_A_tor_jalr_address+g\""

test_6_str:  .string "\"test: 6; cp: cp_cfg_A_tor_sw_address\""
test_7_str:  .string "\"test: 7; cp: cp_cfg_A_tor_sw_address-4\""
test_8_str:  .string "\"test: 8; cp: cp_cfg_A_tor_sw_address+4\""
test_9_str:  .string "\"test: 9; cp: cp_cfg_A_tor_sw_address+g-4\""
test_10_str: .string "\"test: 10; cp: cp_cfg_A_tor_sw_address+g\""

test_11_str: .string "\"test: 11; cp: cp_cfg_A_tor_lw_address\""
test_12_str: .string "\"test: 12; cp: cp_cfg_A_tor_lw_address-4\""
test_13_str: .string "\"test: 13; cp: cp_cfg_A_tor_lw_address+4\""
test_14_str: .string "\"test: 14; cp: cp_cfg_A_tor_lw_address+g-4\""
test_15_str: .string "\"test: 15; cp: cp_cfg_A_tor_lw_address+g\""

.p2align 12
.p2align (UDB_PMP_GRANULARITY)
TEST_FOR_EXECUTION_0:
    .rept ((1<<(UDB_PMP_GRANULARITY))>>2)
    jr ra
    .endr

.p2align (UDB_PMP_GRANULARITY)
TEST_FOR_EXECUTION:
    .rept ((1<<(UDB_PMP_GRANULARITY))>>2)
    jr ra
    .endr

RETURN_INSTRUCTION:
    nop
    nop
    jr ra                                                        // Get back to the point from where TEST_FOR_EXECUTION was called.


RVTEST_DATA_END

// Signature region for self-checking
RVTEST_SIG_SETUP
