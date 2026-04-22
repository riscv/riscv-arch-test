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
// Coverpoints : cp_cfg_X and cp_cfg_RW from PMPU are partially covered in this
//                 test file.
//
// Test Cases  : Checking that X alone determines execute access and WR bits control
//               write/read access for every type of load and store. Configuring
//               PMP in M mode & then switching to U mode. For a standard region with
//               pmpcfg_i.L = 1, pmpcfg_i.A=NAPOT, all legal pmpcfg_i.XWR, making
//               {lw, sw, jalr} at that start of region.
// --------------------------------------------------------------------------------

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS:  ['I','U']
# params:
#   MXLEN: 32
#   NUM_PMP_ENTRIES: '>0'
# MARCH: rv32i_zicsr
##### END_TEST_CONFIG #####

#define TEST_FILE "pmpu_cfg_XWR.S"
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

    LI(a4, NOP)                                              // Value to write (NOP)
    // Store Access Check
    LA(a5, \ADDRESS)                                         // Address to be verified
    \TEST_CASE\()_2:
    sb a4, 0(a5)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_2, test_2_str)
    \TEST_CASE\()_3:
    sh a4, 0(a5)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_3, test_3_str)
    \TEST_CASE\()_4:
    sw a4, 0(a5)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_4, test_4_str)

    LA(a5, \ADDRESS)                                         // Address to be verified
    \TEST_CASE\()_5:
    lb a4, 0(a5)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_5, test_5_str)
    \TEST_CASE\()_6:
    lbu a4, 0(a5)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_6, test_6_str)
    \TEST_CASE\()_7:
    lh a4, 0(a5)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_7, test_7_str)
    \TEST_CASE\()_8:
    lhu a4, 0(a5)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_8, test_8_str)
    \TEST_CASE\()_9:
    lw a4, 0(a5)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_9, test_9_str)

.endm

main:
    // Loop to SET pmpcfg REGs to zero
    .set pmpcfgi, CSR_PMPCFG0
    .rept RVMODEL_NUM_PMPS/4
    csrw pmpcfgi , x0
    .set pmpcfgi, pmpcfgi+1
    .endr

    // Loop to SET pmpaddr REGs to zero
    .set pmpaddri, CSR_PMPADDR0
    .rept RVMODEL_NUM_PMPS
    csrw pmpaddri, x0
    .set pmpaddri, pmpaddri+1
    .endr

#define PMP_REGION_GLOBAL    ((((PMP_L|PMP_R|PMP_W|PMP_X|PMP_NAPOT)&0xFF) << PMP3_CFG_SHIFT))  // Background region with RWX enable.
#define PMPREGION_LXWR_1000 ((((PMP_L|                  PMP_NAPOT)&0xFF) << PMP1_CFG_SHIFT))
#define PMPREGION_LXWR_1001 ((((PMP_L|PMP_R|            PMP_NAPOT)&0xFF) << PMP0_CFG_SHIFT))
#define PMPREGION_LXWR_1011 ((((PMP_L|PMP_R|PMP_W       |PMP_NAPOT)&0xFF) << PMP3_CFG_SHIFT))
#define PMPREGION_LXWR_1100 ((((PMP_L|              PMP_X|PMP_NAPOT)&0xFF) << PMP2_CFG_SHIFT))
#define PMPREGION_LXWR_1101 ((((PMP_L|PMP_R         |PMP_X|PMP_NAPOT)&0xFF) << PMP1_CFG_SHIFT))
#define PMPREGION_LXWR_1111 ((((PMP_L|PMP_R|PMP_W|PMP_X|PMP_NAPOT)&0xFF) << PMP0_CFG_SHIFT))

#define PMPADDRESS_TOP_GLOBAL        -1                                                // All memory region                                    // Test section address
#define REGIONSTART            TEST_FOR_EXECUTION    // RAM_BASE_ADDR + PROGRAM_SIZE
#if RVMODEL_PMP_GRAIN != 0
    #define PMP_MASK            ~((1 << (RVMODEL_PMP_GRAIN - 1))-1)
    #define PMP_REGION_SIZE     (1 << (RVMODEL_PMP_GRAIN - 1)) - 1
#else
    #define PMP_MASK            ~0
    #define PMP_REGION_SIZE     0
#endif

#ifdef S_SUPPORTED
    csrw satp, zero                // Disable address translation.
#endif

    LA(x4, PMPADDRESS_TOP_GLOBAL)
    csrw     pmpaddr15, x4

    //Lock the Background region.
    LI(x4, PMP_REGION_GLOBAL)
    csrw pmpcfg3, x4


//                                            Verification Section
// Test Case: 1 : L -> 1 and No Permissions given to the PMP Region 5

    LA(x5, REGIONSTART)
    srl x5, x5, PMP_SHIFT
    andi x5, x5, PMP_MASK
    ori x5, x5, PMP_REGION_SIZE
    csrw pmpaddr5, x5
    LI(t1, PMPREGION_LXWR_1000)
    csrw pmpcfg1, t1

    RVTEST_GOTO_LOWER_MODE    Umode        // SWITCH TO U-mode
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_1
    RVTEST_GOTO_MMODE

// Test Case: 2 : L -> 1 and R Permissions given to the PMP Region 4

    LA(x5, REGIONSTART)
    srl x5, x5, PMP_SHIFT
    andi x5, x5, PMP_MASK
    ori x5, x5, PMP_REGION_SIZE
    csrw pmpaddr4, x5
    LI(t1, PMPREGION_LXWR_1001)
    csrw pmpcfg1, t1

    RVTEST_GOTO_LOWER_MODE    Umode        // SWITCH TO U-mode
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_2
    RVTEST_GOTO_MMODE

// Test Case: 3 : L -> 1 and WR Permissions given to the PMP Region 3

    LA(x5, REGIONSTART)
    srl x5, x5, PMP_SHIFT
    andi x5, x5, PMP_MASK
    ori x5, x5, PMP_REGION_SIZE
    csrw pmpaddr3, x5
    LI(t1, PMPREGION_LXWR_1011)
    csrw pmpcfg0, t1

    RVTEST_GOTO_LOWER_MODE    Umode        // SWITCH TO U-mode
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_3
    RVTEST_GOTO_MMODE

// Test Case: 4 : L -> 1 and X Permissions given to the PMP Region 2

    LA(x5, REGIONSTART)
    srl x5, x5, PMP_SHIFT
    andi x5, x5, PMP_MASK
    ori x5, x5, PMP_REGION_SIZE
    csrw pmpaddr2, x5
    LI(t1, PMPREGION_LXWR_1100)
    csrw pmpcfg0, t1

    RVTEST_GOTO_LOWER_MODE    Umode        // SWITCH TO U-mode
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_4
    RVTEST_GOTO_MMODE

// Test Case: 5 : L -> 1 and XR Permissions given to the PMP Region 1

    LA(x5, REGIONSTART)
    srl x5, x5, PMP_SHIFT
    andi x5, x5, PMP_MASK
    ori x5, x5, PMP_REGION_SIZE
    csrw pmpaddr1, x5
    LI(t1, PMPREGION_LXWR_1101)
    csrw pmpcfg0, t1

    RVTEST_GOTO_LOWER_MODE    Umode        // SWITCH TO U-mode
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_5
    RVTEST_GOTO_MMODE

// Test Case: 6 : L -> 1 and XWR Permissions given to the PMP Region 0

    LA(x5, REGIONSTART)
    srl x5, x5, PMP_SHIFT
    andi x5, x5, PMP_MASK
    ori x5, x5, PMP_REGION_SIZE
    csrw pmpaddr0, x5
    LI(t1, PMPREGION_LXWR_1111)
    csrw pmpcfg0, t1

    RVTEST_GOTO_LOWER_MODE    Umode        // SWITCH TO U-mode
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_6
    RVTEST_GOTO_MMODE

    j exit                                                        // Verification Complete, exit the test

exit:

RVTEST_CODE_END
RVTEST_DATA_BEGIN
.align 4

// Test case strings for reporting
test_1_str: .string "\"test: 1; cp: pmps_cfg_XWR.S_jalr\""
test_2_str: .string "\"test: 2; cp: pmps_cfg_XWR.S_sb\""
test_3_str: .string "\"test: 3; cp: pmps_cfg_XWR.S_sh\""
test_4_str: .string "\"test: 4; cp: pmps_cfg_XWR.S_sw\""
test_5_str: .string "\"test: 5; cp: pmps_cfg_XWR.S_lb\""
test_6_str: .string "\"test: 6; cp: pmps_cfg_XWR.S_lbu\""
test_7_str: .string "\"test: 7; cp: pmps_cfg_XWR.S_lh\""
test_8_str: .string "\"test: 8; cp: pmps_cfg_XWR.S_lhu\""
test_9_str: .string "\"test: 9; cp: pmps_cfg_XWR.S_lw\""

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
