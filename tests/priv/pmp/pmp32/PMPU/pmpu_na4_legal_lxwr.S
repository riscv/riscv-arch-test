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
// Coverpoints : cp_cfg_A_na4 for PMPU is fully covered in this test file.
//
// Test Cases  : Checking XWR controls accesses in matching NA4 region. G=0 Only
//               Configuring PMP in M mode and then switching to U mode.
//               with pmpcfg_i.L = 1, pmpcfg_i.A=NA4, all legal pmpcfg_i.XWR,
//               reasonable address in pmpaddr: making {lw, sw, jalr} at that
//               address, that address - 4, just beyond top of the region.
//               Observing proper access faults for restricted regions, and
//               accesses beyond the region and below the region should succeed
//               because the bckground region is set to RWX.
// --------------------------------------------------------------------------------

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS:  ['S']
# params:
#   MXLEN: 32
#   NUM_PMP_ENTRIES: '>0'
#   PMP_NA4_SUPPORTED: true
# MARCH: rv32i_zicsr_zifencei
##### END_TEST_CONFIG #####

#define SIGUPD_COUNT 100
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

#define PMPREGION_LXWR_0000 ((((                        PMP_NA4  )&0xFF) << PMP1_CFG_SHIFT))
#define PMPREGION_LXWR_0001 ((((      PMP_R|            PMP_NA4  )&0xFF) << PMP0_CFG_SHIFT))
#define PMPREGION_LXWR_0011 ((((      PMP_R|PMP_W      |PMP_NA4  )&0xFF) << PMP3_CFG_SHIFT))
#define PMPREGION_LXWR_0100 ((((                    PMP_X|PMP_NA4  )&0xFF) << PMP2_CFG_SHIFT))
#define PMPREGION_LXWR_0101 ((((      PMP_R         |PMP_X|PMP_NA4  )&0xFF) << PMP1_CFG_SHIFT))
#define PMPREGION_LXWR_0111 ((((      PMP_R|PMP_W|PMP_X|PMP_NA4  )&0xFF) << PMP0_CFG_SHIFT))

#define REGIONSTART            TEST_FOR_EXECUTION        // RAM_BASE_ADDR + PROGRAM_SIZE


    RVTEST_PMP_SET_BACKGROUND x4

//                                            Verification Section
// Test Case: 1 : L -> 0 and No Permissions given to the PMP Region 5

    LA(x4, REGIONSTART)
    srl x4, x4, PMP_SHIFT
    csrw pmpaddr5, x4
    LI(x5, PMPREGION_LXWR_0000)
    csrw pmpcfg1, x5

    RVTEST_GOTO_LOWER_MODE    Umode        // SWITCH TO U-mode
    PMP_VERIFICATION_RWX_NA4_RV32    TEST_FOR_EXECUTION, test_1
    RVTEST_GOTO_MMODE

// Test Case: 2 : L -> 0 and R Permissions given to the PMP Region 4

    LA(x4, REGIONSTART)
    srl x4, x4, PMP_SHIFT
    csrw pmpaddr4, x4
    LI(x5, PMPREGION_LXWR_0001)
    csrw pmpcfg1, x5

    RVTEST_GOTO_LOWER_MODE    Umode        // SWITCH TO U-mode
    PMP_VERIFICATION_RWX_NA4_RV32    TEST_FOR_EXECUTION, test_2
    RVTEST_GOTO_MMODE

// Test Case: 3 : L -> 0 and WR Permissions given to the PMP Region 3

    LA(x4, REGIONSTART)
    srl x4, x4, PMP_SHIFT
    csrw pmpaddr3, x4
    LI(x5, PMPREGION_LXWR_0011)
    csrw pmpcfg0, x5

    RVTEST_GOTO_LOWER_MODE    Umode        // SWITCH TO U-mode
    PMP_VERIFICATION_RWX_NA4_RV32    TEST_FOR_EXECUTION, test_3
    RVTEST_GOTO_MMODE

// Test Case: 4 : L -> 0 and X Permissions given to the PMP Region 2

    LA(x4, REGIONSTART)
    srl x4, x4, PMP_SHIFT
    csrw pmpaddr2, x4
    LI(x5, PMPREGION_LXWR_0100)
    csrw pmpcfg0, x5

    RVTEST_GOTO_LOWER_MODE    Umode        // SWITCH TO U-mode
    PMP_VERIFICATION_RWX_NA4_RV32    TEST_FOR_EXECUTION, test_4
    RVTEST_GOTO_MMODE

// Test Case: 5 : L -> 0 and XR Permissions given to the PMP Region 1

    LA(x4, REGIONSTART)
    srl x4, x4, PMP_SHIFT
    csrw pmpaddr1, x4
    LI(x5, PMPREGION_LXWR_0101)
    csrw pmpcfg0, x5

    RVTEST_GOTO_LOWER_MODE    Umode        // SWITCH TO U-mode
    PMP_VERIFICATION_RWX_NA4_RV32    TEST_FOR_EXECUTION, test_5
    RVTEST_GOTO_MMODE

// Test Case: 6 : L -> 0 and XWR Permissions given to the PMP Region 0

    LA(x4, REGIONSTART)
    srl x4, x4, PMP_SHIFT
    csrw pmpaddr0, x4
    LI(x5, PMPREGION_LXWR_0111)
    csrw pmpcfg0, x5

    RVTEST_GOTO_LOWER_MODE    Umode        // SWITCH TO U-mode
    PMP_VERIFICATION_RWX_NA4_RV32    TEST_FOR_EXECUTION, test_6
exit:

RVTEST_CODE_END
RVTEST_DATA_BEGIN
.p2align 4

// Test case strings for reporting
test_1_str: .string "\"test: 1; cp: pmpm_cfg_A_off_all_jalr_address\""
test_2_str: .string "\"test: 2; cp: pmpm_cfg_A_off_all_jalr_address-4\""
test_3_str: .string "\"test: 3; cp: pmpm_cfg_A_off_all_jalr_address+4\""
test_4_str: .string "\"test: 4; cp: pmpm_cfg_A_off_all_sw_address\""
test_5_str: .string "\"test: 5; cp: pmpm_cfg_A_off_all_lw_address\""
test_6_str: .string "\"test: 6; cp: pmpm_cfg_A_off_all_sw_address-4\""
test_7_str: .string "\"test: 7; cp: pmpm_cfg_A_off_all_lw_address-4\""
test_8_str: .string "\"test: 8; cp: pmpm_cfg_A_off_all_sw_address+4\""
test_9_str: .string "\"test: 9; cp: pmpm_cfg_A_off_all_lw_address+4\""

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
