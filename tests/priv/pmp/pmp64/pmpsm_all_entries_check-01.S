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
// Notes       : - Ensure `rvmodel_macros.h` is configured to match your PMP grain
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
# REQUIRED_EXTENSIONS: ['I','Smpmp']
# params:
#   MXLEN: 64
# MARCH: rv64i_zicsr
# CONFIG_DEPENDENT: true
##### END_TEST_CONFIG #####

// Define the name of this test file for reporting and the size of the signature region
#define TEST_FILE "pmpsm_all_entries_check-01.S"
#define SIGUPD_COUNT 50

// Enable trap handler
#define rvtest_mtrap_routine
#define RVTEST_PRIV_TEST

#define SKIP_MEPC

// Include framework macros
#include "riscv_arch_test.h"

// Set up test environment and declare main entry point
RVTEST_BEGIN

#if RVMODEL_PMP_GRAIN != 0
  #define g   (1 << (RVMODEL_PMP_GRAIN + 2))
#else
  #define g   (1 << (RVMODEL_PMP_GRAIN + 3))
#endif

#define NOP         0x13

.macro VERIFICATION_RWX ADDRESS, TEST_CASE

    LA(a5, \ADDRESS)                                        // Address to be ve
    \TEST_CASE\()_1:
    sw a4, 0(a5)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4,\TEST_CASE\()_1,test_2_str)
    \TEST_CASE\()_2:
    lw a4, 0(a5)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4,\TEST_CASE\()_2,test_1_str)

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

#define PMP_REGION_GLOBAL    ((PMP_L|PMP_R|PMP_W|PMP_X|PMP_NAPOT)&0xFF) << PMP7_CFG_SHIFT // Background region with RWX enable.
#define PMP_REGION_62       ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP6_CFG_SHIFT
#define PMP_REGION_61       ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP5_CFG_SHIFT
#define PMP_REGION_60       ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP4_CFG_SHIFT
#define PMP_REGION_59       ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP3_CFG_SHIFT
#define PMP_REGION_58       ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP2_CFG_SHIFT
#define PMP_REGION_57       ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP1_CFG_SHIFT
#define PMP_REGION_56       ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP0_CFG_SHIFT
#define PMP_REGION_55       ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP7_CFG_SHIFT
#define PMP_REGION_54       ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP6_CFG_SHIFT
#define PMP_REGION_53       ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP5_CFG_SHIFT
#define PMP_REGION_52       ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP4_CFG_SHIFT
#define PMP_REGION_51       ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP3_CFG_SHIFT
#define PMP_REGION_50       ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP2_CFG_SHIFT
#define PMP_REGION_49       ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP1_CFG_SHIFT
#define PMP_REGION_48       ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP0_CFG_SHIFT

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
    csrw pmpcfg14, x4

//                                            Verification Section
// Test Case: 1 : L -> 1 and XR Permissions given to the PMP Region 62

    LI(x5, STANDARD_REGION)
    csrw pmpaddr62, x5

    LI(x4, PMP_REGION_62)
    csrw pmpcfg14, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_1

// Test Case: 2 : L -> 1 and XR Permissions given to the PMP Region 61

    LI(x5, STANDARD_REGION)
    csrw pmpaddr61, x5

    LI(x4, PMP_REGION_61)
    csrw pmpcfg14, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_2

// Test Case: 3 : L -> 1 and XR Permissions given to the PMP Region 60

    LI(x5, STANDARD_REGION)
    csrw pmpaddr60, x5

    LI(x4, PMP_REGION_60)
    csrw pmpcfg14, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_3

// Test Case: 4 : L -> 1 and XR Permissions given to the PMP Region 59

    LI(x5, STANDARD_REGION)
    csrw pmpaddr59, x5

    LI(x4, PMP_REGION_59)
    csrw pmpcfg14, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_4

// Test Case: 5 : L -> 1 and XR Permissions given to the PMP Region 58

    LI(x5, STANDARD_REGION)
    csrw pmpaddr58, x5

    LI(x4, PMP_REGION_58)
    csrw pmpcfg14, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_5

// Test Case: 6 : L -> 1 and XR Permissions given to the PMP Region 57

    LI(x5, STANDARD_REGION)
    csrw pmpaddr57, x5

    LI(x4, PMP_REGION_57)
    csrw pmpcfg14, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_6

// Test Case: 7 : L -> 1 and XR Permissions given to the PMP Region 56

    LI(x5, STANDARD_REGION)
    csrw pmpaddr56, x5

    LI(x4, PMP_REGION_56)
    csrw pmpcfg14, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_7

// Test Case: 8 : L -> 1 and XR Permissions given to the PMP Region 55

    LI(x5, STANDARD_REGION)
    csrw pmpaddr55, x5

    LI(x4, PMP_REGION_55)
    csrw pmpcfg12, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_8

// Test Case: 9 : L -> 1 and XR Permissions given to the PMP Region 54

    LI(x5, STANDARD_REGION)
    csrw pmpaddr54, x5

    LI(x4, PMP_REGION_54)
    csrw pmpcfg12, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_9

// Test Case: 10 : L -> 1 and XR Permissions given to the PMP Region 53

    LI(x5, STANDARD_REGION)
    csrw pmpaddr53, x5

    LI(x4, PMP_REGION_53)
    csrw pmpcfg12, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_10

// Test Case: 11 : L -> 1 and XR Permissions given to the PMP Region 52

    LI(x5, STANDARD_REGION)
    csrw pmpaddr52, x5

    LI(x4, PMP_REGION_52)
    csrw pmpcfg12, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_11

// Test Case: 12 : L -> 1 and XR Permissions given to the PMP Region 51

    LI(x5, STANDARD_REGION)
    csrw pmpaddr51, x5

    LI(x4, PMP_REGION_51)
    csrw pmpcfg12, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_12

// Test Case: 13 : L -> 1 and XR Permissions given to the PMP Region 50

    LI(x5, STANDARD_REGION)
    csrw pmpaddr50, x5

    LI(x4, PMP_REGION_50)
    csrw pmpcfg12, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_13

// Test Case: 14 : L -> 1 and XR Permissions given to the PMP Region 49

    LI(x5, STANDARD_REGION)
    csrw pmpaddr49, x5

    LI(x4, PMP_REGION_49)
    csrw pmpcfg12, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_14

// Test Case: 15 : L -> 1 and XR Permissions given to the PMP Region 48

    LI(x5, STANDARD_REGION)
    csrw pmpaddr48, x5

    LI(x4, PMP_REGION_48)
    csrw pmpcfg12, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_15

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
test_2_str: .string "\"test: 2; cp: cp_pmpm64_sw\""

RVTEST_DATA_END

// Signature region for self-checking
RVTEST_SIG_SETUP
