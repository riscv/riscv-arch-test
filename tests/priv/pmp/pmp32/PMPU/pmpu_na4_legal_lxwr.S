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
# REQUIRED_EXTENSIONS:  ['I','S']
# params:
#   MXLEN: 32
#   NUM_PMP_ENTRIES: '>0'
# MARCH: rv32i_zicsr
##### END_TEST_CONFIG #####

#define TEST_FILE "pmps_na4_legal_lxwr.S"
#define SIGUPD_COUNT 100
#define rvtest_mtrap_routine
#define RVTEST_PRIV_TEST
#define SKIP_MEPC

#include "riscv_arch_test.h"

RVTEST_BEGIN

.macro VERIFICATION_RWX ADDRESS TEST_CASE

    LI(x4, 0xACCE)                        // Store a value which is to be checked in trap handler
    // Execution Access Check
    LA (a4, \ADDRESS)
    LA(x1, 1f)                            // Store the return Address in x1
    \TEST_CASE\()_1:
    jalr ra, 0(a4)
    nop
1:
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_1, test_1_str)

    addi a4, a4, -4                     // REGIONSTART - 4
    LA(x1, 2f)                            // Store the return Address in x1
    \TEST_CASE\()_2:
    jalr ra, 0(a4)
    nop
2:
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_2, test_2_str)

    addi a4, a4, 8                      // REGIONSTART + 4
    LA(x1, 3f)                            // Store the return Address in x1
    \TEST_CASE\()_3:
    jalr ra, 0(a4)
    nop
3:
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_3, test_3_str)

    LI(a4, NOP)                                              // Value to write (NOP)
    // Load & Store Access Check
    LA(a5, \ADDRESS)                                         // Address to be verified

    \TEST_CASE\()_4:
    sw a4, 0(a5)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_4, test_4_str)

    \TEST_CASE\()_5:
    lw a4, 0(a5)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_5, test_5_str)                                  // Signature update

    addi a5, a5, -4                                         // REGIONSTART - 4
    \TEST_CASE\()_6:
    sw a4, 0(a5)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_6, test_6_str)

    \TEST_CASE\()_7:
    lw a4, 0(a5)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_7, test_7_str)

    addi a5, a5, 8                                          // REGIONSTART + 4                                            // Address to be verified
    \TEST_CASE\()_8:
    sw a4, 0(a5)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_8, test_8_str)

    \TEST_CASE\()_9:
    lw a4, 0(a5)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_9, test_9_str)

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

#define PMP_REGION_GLOBAL    ((((PMP_L|PMP_R|PMP_W|PMP_X|PMP_NAPOT)&0xFF) << PMP3_CFG_SHIFT))  // Background region with RWX enable.
#define PMPREGION_LXWR_0000 ((((                        PMP_NA4  )&0xFF) << PMP1_CFG_SHIFT))
#define PMPREGION_LXWR_0001 ((((      PMP_R|            PMP_NA4  )&0xFF) << PMP0_CFG_SHIFT))
#define PMPREGION_LXWR_0011 ((((      PMP_R|PMP_W      |PMP_NA4  )&0xFF) << PMP3_CFG_SHIFT))
#define PMPREGION_LXWR_0100 ((((                    PMP_X|PMP_NA4  )&0xFF) << PMP2_CFG_SHIFT))
#define PMPREGION_LXWR_0101 ((((      PMP_R         |PMP_X|PMP_NA4  )&0xFF) << PMP1_CFG_SHIFT))
#define PMPREGION_LXWR_0111 ((((      PMP_R|PMP_W|PMP_X|PMP_NA4  )&0xFF) << PMP0_CFG_SHIFT))

#define PMPADDRESS_TOP_GLOBAL        -1                                                // All memory region
#define REGIONSTART            TEST_FOR_EXECUTION        // RAM_BASE_ADDR + PROGRAM_SIZE

#ifdef rvtest_strap_routine
    csrw satp, zero                // Disable address translation.
#endif

    LA(x4, PMPADDRESS_TOP_GLOBAL)
    csrw     pmpaddr15, x4

    //Lock the Background region.
    LI(x4, PMP_REGION_GLOBAL)
    csrw pmpcfg3, x4

//                                            Verification Section
// Test Case: 1 : L -> 0 and No Permissions given to the PMP Region 5

    LA(x4, REGIONSTART)
    srl x4, x4, PMP_SHIFT
    csrw pmpaddr5, x4
    LI(x5, PMPREGION_LXWR_0000)
    csrw pmpcfg1, x5

    RVTEST_GOTO_LOWER_MODE    Umode        // SWITCH TO U-mode
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_1
    RVTEST_GOTO_MMODE

// Test Case: 2 : L -> 0 and R Permissions given to the PMP Region 4

    LA(x4, REGIONSTART)
    srl x4, x4, PMP_SHIFT
    csrw pmpaddr4, x4
    LI(x5, PMPREGION_LXWR_0001)
    csrw pmpcfg1, x5

    RVTEST_GOTO_LOWER_MODE    Umode        // SWITCH TO U-mode
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_2
    RVTEST_GOTO_MMODE

// Test Case: 3 : L -> 0 and WR Permissions given to the PMP Region 3

    LA(x4, REGIONSTART)
    srl x4, x4, PMP_SHIFT
    csrw pmpaddr3, x4
    LI(x5, PMPREGION_LXWR_0011)
    csrw pmpcfg0, x5

    RVTEST_GOTO_LOWER_MODE    Umode        // SWITCH TO U-mode
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_3
    RVTEST_GOTO_MMODE

// Test Case: 4 : L -> 0 and X Permissions given to the PMP Region 2

    LA(x4, REGIONSTART)
    srl x4, x4, PMP_SHIFT
    csrw pmpaddr2, x4
    LI(x5, PMPREGION_LXWR_0100)
    csrw pmpcfg0, x5

    RVTEST_GOTO_LOWER_MODE    Umode        // SWITCH TO U-mode
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_4
    RVTEST_GOTO_MMODE

// Test Case: 5 : L -> 0 and XR Permissions given to the PMP Region 1

    LA(x4, REGIONSTART)
    srl x4, x4, PMP_SHIFT
    csrw pmpaddr1, x4
    LI(x5, PMPREGION_LXWR_0101)
    csrw pmpcfg0, x5

    RVTEST_GOTO_LOWER_MODE    Umode        // SWITCH TO U-mode
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_5
    RVTEST_GOTO_MMODE

// Test Case: 6 : L -> 0 and XWR Permissions given to the PMP Region 0

    LA(x4, REGIONSTART)
    srl x4, x4, PMP_SHIFT
    csrw pmpaddr0, x4
    LI(x5, PMPREGION_LXWR_0111)
    csrw pmpcfg0, x5

    RVTEST_GOTO_LOWER_MODE    Umode        // SWITCH TO U-mode
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_6
    RVTEST_GOTO_MMODE

    j exit                                                        // Verification Complete, exit the test

exit:

RVTEST_CODE_END
RVTEST_DATA_BEGIN
.align 4

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

.align 12
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
