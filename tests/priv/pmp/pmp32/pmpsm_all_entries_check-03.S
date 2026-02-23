// --------------------------------------------------------------------------------
// Title        : Comprehensive PMP (Physical Memory Protection) Verification
// Authors      : Umer Shahid, Allen Baum, David Harris
//                Muhammad Abdullah, Hamza Ali, Muhammad Zain
//
// Description : This test verifies the functionality and enforcement of
//               Physical Memory Protection (PMP) configurations in RISC-V
//               systems. It specifically tests the Read, Write, and Execute
//               permissions for a designated memory region, ensuring that
//               the PMP settings are correctly applied and that the system
//               behaves as expected when accessing this region.
//
// Notes       : - Ensure `model_test.h` is configured to match your PMP grain
//                 and PMP region count before running this test.
//               - Adjust PMP configurations for specific hardware if required.
//
// Coverpoints : cp_pmp64 for PMPM is partially covered in this test file.
//
// Test Cases  : Checking all (64-PMP_writable_regs) PMP registers affect load/store
//               access. Just basic checks since bottom PMP_writable_regs have been
//               tested thoroughly. 64 Regions Only, With pmpcfg.L=1, pmpcfg.XWR=101,
//               attempt to lw and sw to each standard region. Read should succeed and
//               write should fail, proving all PMP entries are usable.
//
// Dependencies: model_test.h, arch_test.h
// --------------------------------------------------------------------------------

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: ['I','S','Smpmp']
# MARCH: rv32i_zicsr
# CONFIG_DEPENDENT: true
##### END_TEST_CONFIG #####

// Define the name of this test file for reporting and the size of the signature region
#define TEST_FILE "pmpm_all_entries_check-03.S"
#define SIGUPD_COUNT 50

// Enable trap handler
#define rvtest_mtrap_routine
#define rvtest_strap_routine

#define SKIP_MEPC

// Include framework macros
#include "riscv_arch_test.h"

// Set up test environment and declare main entry point
RVTEST_BEGIN

#ifndef RVMODEL_PMP_GRAIN
    #define RVMODEL_PMP_GRAIN 4
#endif

#ifndef RVMODEL_NUM_PMPS
    #define RVMODEL_NUM_PMPS 64
#endif

#if RVMODEL_PMP_GRAIN != 0
  #define g   (1 << (RVMODEL_PMP_GRAIN + 2))
#else
  #define g   (1 << (RVMODEL_PMP_GRAIN + 3))
#endif

#define NOP         0x13

.macro VERIFICATION_RWX ADDRESS

    LA(a5, \ADDRESS)                                        // Address to be ve
    sw a4, 0(a5)
    nop
    lw a4, 0(a5)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, test_1_str)

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

#define PMP_REGION_GLOBAL   ((PMP_L|PMP_R|PMP_W|PMP_X|PMP_NAPOT)&0xFF) << PMP3_CFG_SHIFT // Background region with RWX enable.
#define PMP_REGION_31       ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP3_CFG_SHIFT
#define PMP_REGION_30       ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP2_CFG_SHIFT
#define PMP_REGION_29       ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP1_CFG_SHIFT
#define PMP_REGION_28       ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP0_CFG_SHIFT
#define PMP_REGION_27       ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP3_CFG_SHIFT
#define PMP_REGION_26       ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP2_CFG_SHIFT
#define PMP_REGION_25       ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP1_CFG_SHIFT
#define PMP_REGION_24       ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP0_CFG_SHIFT
#define PMP_REGION_23       ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP3_CFG_SHIFT
#define PMP_REGION_22       ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP2_CFG_SHIFT
#define PMP_REGION_21       ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP1_CFG_SHIFT
#define PMP_REGION_20       ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP0_CFG_SHIFT
#define PMP_REGION_19       ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP3_CFG_SHIFT
#define PMP_REGION_18       ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP2_CFG_SHIFT
#define PMP_REGION_17       ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP1_CFG_SHIFT
#define PMP_REGION_16       ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP0_CFG_SHIFT

#define PMPADDRESS_TOP_GLOBAL       -1                                              // All memory region
#define REGIONSTART         0x80002000      // RAM_BASE_ADDR + PROGRAM_SIZE
#define PMP_MASK            ~((1 << (RVMODEL_PMP_GRAIN - 1))-1)
#define PMP_REGION_SIZE     ((1 << (RVMODEL_PMP_GRAIN - 1))-1)

#if RVMODEL_PMP_GRAIN != 0
  #define STANDARD_REGION   (((REGIONSTART >> PMP_SHIFT) & PMP_MASK) | PMP_REGION_SIZE)
#else
  #define STANDARD_REGION   (REGIONSTART >> PMP_SHIFT)
#endif

#ifdef rvtest_strap_routine
    csrw satp, zero                // Disable address translation.
#endif

    LA(x4, PMPADDRESS_TOP_GLOBAL)
    csrw    pmpaddr63, x4

    //Lock the Background region.
    LI(x4, (PMP_REGION_GLOBAL))
    csrw pmpcfg15, x4

//                                          Verification Section
// Test Case: 1 : L -> 1 and XR Permissions given to the PMP Region 31

    LI(x5, STANDARD_REGION)
    csrw pmpaddr31, x5

    LI(x4, PMP_REGION_31)
    csrw pmpcfg7, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION

// Test Case: 2 : L -> 1 and XR Permissions given to the PMP Region 30

    LI(x5, STANDARD_REGION)
    csrw pmpaddr30, x5

    LI(x4, PMP_REGION_30)
    csrw pmpcfg7, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION

// Test Case: 3 : L -> 1 and XR Permissions given to the PMP Region 29

    LI(x5, STANDARD_REGION)
    csrw pmpaddr29, x5

    LI(x4, PMP_REGION_29)
    csrw pmpcfg7, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION

// Test Case: 4 : L -> 1 and XR Permissions given to the PMP Region 28

    LI(x5, STANDARD_REGION)
    csrw pmpaddr28, x5

    LI(x4, PMP_REGION_28)
    csrw pmpcfg7, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION

// Test Case: 5 : L -> 1 and XR Permissions given to the PMP Region 27

    LI(x5, STANDARD_REGION)
    csrw pmpaddr27, x5

    LI(x4, PMP_REGION_27)
    csrw pmpcfg6, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION

// Test Case: 6 : L -> 1 and XR Permissions given to the PMP Region 26

    LI(x5, STANDARD_REGION)
    csrw pmpaddr26, x5

    LI(x4, PMP_REGION_26)
    csrw pmpcfg6, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION

// Test Case: 7 : L -> 1 and XR Permissions given to the PMP Region 25

    LI(x5, STANDARD_REGION)
    csrw pmpaddr25, x5

    LI(x4, PMP_REGION_25)
    csrw pmpcfg6, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION

// Test Case: 8 : L -> 1 and XR Permissions given to the PMP Region 24

    LI(x5, STANDARD_REGION)
    csrw pmpaddr24, x5

    LI(x4, PMP_REGION_24)
    csrw pmpcfg6, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION

// Test Case: 9 : L -> 1 and XR Permissions given to the PMP Region 23

    LI(x5, STANDARD_REGION)
    csrw pmpaddr23, x5

    LI(x4, PMP_REGION_23)
    csrw pmpcfg5, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION

// Test Case: 10 : L -> 1 and XR Permissions given to the PMP Region 22

    LI(x5, STANDARD_REGION)
    csrw pmpaddr22, x5

    LI(x4, PMP_REGION_22)
    csrw pmpcfg5, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION

// Test Case: 11 : L -> 1 and XR Permissions given to the PMP Region 21

    LI(x5, STANDARD_REGION)
    csrw pmpaddr21, x5

    LI(x4, PMP_REGION_21)
    csrw pmpcfg5, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION

// Test Case: 12 : L -> 1 and XR Permissions given to the PMP Region 20

    LI(x5, STANDARD_REGION)
    csrw pmpaddr20, x5

    LI(x4, PMP_REGION_20)
    csrw pmpcfg5, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION

// Test Case: 13 : L -> 1 and XR Permissions given to the PMP Region 19

    LI(x5, STANDARD_REGION)
    csrw pmpaddr19, x5

    LI(x4, PMP_REGION_19)
    csrw pmpcfg4, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION

// Test Case: 14 : L -> 1 and XR Permissions given to the PMP Region 18

    LI(x5, STANDARD_REGION)
    csrw pmpaddr18, x5

    LI(x4, PMP_REGION_18)
    csrw pmpcfg4, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION

// Test Case: 15 : L -> 1 and XR Permissions given to the PMP Region 17

    LI(x5, STANDARD_REGION)
    csrw pmpaddr17, x5

    LI(x4, PMP_REGION_17)
    csrw pmpcfg4, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION

// Test Case: 16 : L -> 1 and XR Permissions given to the PMP Region 16

    LI(x5, STANDARD_REGION)
    csrw pmpaddr16, x5

    LI(x4, PMP_REGION_16)
    csrw pmpcfg4, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION

    li a4, 0xbeefcafe                                           // Clean Test exit verification signature.
    RVTEST_SIGUPD(x2, x5, x4, a4, test_2_str)                                   // Signature update
    j exit                                                      // Verification Complete, exit the test

.align 13
.align (RVMODEL_PMP_GRAIN+2)
TEST_FOR_EXECUTION:
    .rept (1<<(RVMODEL_PMP_GRAIN+2))
    nop
    .endr

RETURN_INSTRUCTION:
    nop
    nop
    jr ra                                                       // Get back to the point from where TEST_FOR_EXECUTION was called.

exit:

RVTEST_CODE_END

RVTEST_DATA_BEGIN
.align 4

// Test case strings for reporting
canary_mismatch: .string "Testcase signature canary mismatch!"
test_1_str: .string "\"test: 1; cp: cp_pmpm64_lw\""
test_2_str: .string "\"test: 2; cp: cp_pmpm64\""

RVTEST_DATA_END

// Signature region for self-checking
RVTEST_SIG_SETUP
