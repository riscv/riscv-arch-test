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
// Notes       : - Ensure `rvmodel_macros.h` is configured to match your PMP grain
//                 and PMP region count before running this test.
//               - Adjust PMP configurations for specific hardware if required.
//
// Coverpoints :  cp_misaligned_tor_wrap for PMPM is covered in this test file.
//
// Test Cases  :  Checking doubleword starting before and ending after 4-byte TOR
//                region fails. With pmpcfg_i.L={0/1},pmpcfg_i.A=TOR,pmpcfg_i.XWR=111,
//                4-byte region. Performing {ld, sd} on doubleword that starts 2 bytes
//                before region and ends after 2 bytes of region. Should misaligned or
//                access fault because doubleword access crosses boundary of word.
//
// Dependencies: model_test.h, arch_test.h
// --------------------------------------------------------------------------------

#define SKIP_MEPC
##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: ['I','Smpmp']
# params:
#   MXLEN: 64
# MARCH: rv64i_zicsr
# CONFIG_DEPENDENT: true
##### END_TEST_CONFIG #####

// Define the name of this test file for reporting and the size of the signature region
#define TEST_FILE "pmpsm_mislaigned_tor_wrap.S"
#define SIGUPD_COUNT 50

// Enable trap handler
#define rvtest_mtrap_routine
#define RVTEST_PRIV_TEST

// Include framework macros
#include "riscv_arch_test.h"

// Set up test environment and declare main entry point
RVTEST_BEGIN

#define NOP     (0x13<<32)+0x13
#define g   (1 << (RVMODEL_PMP_GRAIN + 2))

.macro VERIFICATION_RWX ADDRESS TEST_CASE

    LI(a4, NOP)                                              // Value to write (NOP)

    LA(a5, (\ADDRESS-2))                                     // Address to be verified
    \TEST_CASE\()_1:
    sd a4, 0(a5)                                             // Doubleword-level store test
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_1, test_1_str)

    \TEST_CASE\()_2:
    ld a4, 0(a5)                                             // Doubleword-level load test
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_2, test_2_str)

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

#define PMP_REGION_GLOBAL    ((((PMP_L|PMP_R|PMP_W|PMP_X|PMP_NAPOT)&0xFF)   << PMP7_CFG_SHIFT))  // Background region with RWX enable.
#define DEFAULT_TOR_REGION  ((((PMP_L|PMP_R|PMP_W|PMP_X        )  &0xFF)   << PMP0_CFG_SHIFT))
#define PMPREGION_LXWR      ((((PMP_L|PMP_R|PMP_W|PMP_X|PMP_TOR)  &0xFF)   << PMP1_CFG_SHIFT))
#define PMPREGION_XWR       ((((      PMP_R|PMP_W|PMP_X|PMP_TOR)  &0xFF)   << PMP1_CFG_SHIFT))

#define PMPADDRESS_TOP_GLOBAL        -1                                                // All memory region
#define REGIONSTART            0x80002000        // RAM_BASE_ADDR + PROGRAM_SIZE
#define LOWER_BOUND         ((REGIONSTART)   >> PMP_SHIFT)
#define UPPER_BOUND         ((REGIONSTART+g) >> PMP_SHIFT)

#ifdef rvtest_strap_routine
    csrw satp, zero                // Disable address translation.
#endif

    LA(x4, PMPADDRESS_TOP_GLOBAL)
    csrw     pmpaddr15, x4

    //Lock the Background region.
    LI(x4, PMP_REGION_GLOBAL)
    csrw pmpcfg2, x4

    LA(x4, LOWER_BOUND)
    csrw     pmpaddr0, x4

    LA(x4, UPPER_BOUND)
    csrw     pmpaddr1, x4

//                                            Verification Section
// Test Case: 1 -- XWR Permissions given to the PMP Region.

    LI(x4, PMPREGION_XWR|DEFAULT_TOR_REGION)
    csrw pmpcfg0, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION,test_1

// Test Case: 2 -- LXWR Permissions given to the PMP Region.

    LI(x4, PMPREGION_LXWR|DEFAULT_TOR_REGION)
    csrw pmpcfg0, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION,test_2

    RVTEST_GOTO_MMODE

    j exit                                                        // Verification Complete, exit the test

.align 13
.align (RVMODEL_PMP_GRAIN+2)
TEST_FOR_EXECUTION:
    .rept (1<<(RVMODEL_PMP_GRAIN+2))
    nop
    .endr

RETURN_INSTRUCTION:
    nop
    nop
    jr ra                                                        // Get back to the point from where TEST_FOR_EXECUTION was called.

exit:

RVTEST_CODE_END

RVTEST_DATA_BEGIN
.align 4

// Test case strings for reporting
canary_mismatch: .string "Testcase signature canary mismatch!"
test_1_str: .string "\"test: 1; cp: pmpm_mislaigned_na4_wrap_sd\""
test_2_str: .string "\"test: 1; cp: pmpm_mislaigned_na4_wrap_ld\""

RVTEST_DATA_END

// Signature region for self-checking
RVTEST_SIG_SETUP
