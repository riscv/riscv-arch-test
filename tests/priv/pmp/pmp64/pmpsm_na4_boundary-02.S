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
// Notes       : - Ensure `model_test.h` is configured to match your PMP grain
//                 and PMP region count before running this test.
//               - Adjust PMP configurations for specific hardware if required.
//
// Coverpoints :  cp_na4_boundary for PMPM is partially covered in this test file.
//
// Test Cases  :  Checking doubleword access crossing NA4 boundary fails. With
//                  pmpcfg_i.L = 1, pmpcfg_i.A = NA4, pmpcfg_i.XWR = 111, and
//                  pmpaddr_i = {upper half of doubleword}. Performing {ld,sd}
//                  on doubleword. Should access fault because doubleword access
//                  crosses boundary of word.
//
// Dependencies: model_test.h, arch_test.h
// --------------------------------------------------------------------------------

#define SKIP_MEPC
##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: ['I','S','Smpmp']
# params:
#   MXLEN: 64
# MARCH: rv64i_zicsr
# CONFIG_DEPENDENT: true
##### END_TEST_CONFIG #####

// Define the name of this test file for reporting and the size of the signature region
#define TEST_FILE "pmpsm_na4_boundary-02.S"
#define SIGUPD_COUNT 50

// Enable trap handler
#define rvtest_mtrap_routine
#define rvtest_strap_routine

// Include framework macros
#include "riscv_arch_test.h"

// Set up test environment and declare main entry point
RVTEST_BEGIN

#ifndef RVMODEL_PMP_GRAIN
    #define RVMODEL_PMP_GRAIN 0
#endif

#ifndef RVMODEL_NUM_PMPS
    #define RVMODEL_NUM_PMPS 16
#endif

#define NOP     (0x13<<32)+0x13
#define g   (1 << (RVMODEL_PMP_GRAIN + 2))

.macro VERIFICATION_RWX ADDRESS

    LI(a4, NOP)                                              // Value to write (NOP)

    LA(a5, \ADDRESS)                                         // Address to be verified
    sd a4, 0(a5)                                             // Doubleword-level store test
    nop
    ld a4, 0(a5)                                             // Doubleword-level load test
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, test_1_str)                                  // Signature update

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
#define PMPREGION_LXWR      ((((PMP_L|PMP_R|PMP_W|PMP_X|PMP_NA4)  &0xFF)   << PMP1_CFG_SHIFT))

#define PMPADDRESS_TOP_GLOBAL        -1                                                // All memory region
#define REGIONSTART            0x80002000        // RAM_BASE_ADDR + PROGRAM_SIZE
#define NA4_REGION          ((REGIONSTART+g)    >> PMP_SHIFT)

#ifdef rvtest_strap_routine
    csrw satp, zero                // Disable address translation.
#endif

    LA(x4, PMPADDRESS_TOP_GLOBAL)
    csrw     pmpaddr15, x4

    //Lock the Background region.
    LI(x4, PMP_REGION_GLOBAL)
    csrw pmpcfg2, x4

    LA(x4, NA4_REGION)
    csrw pmpaddr1, x4

//                                            Verification Section
// Test Case: 1 -- LXWR Permissions given to the na4 Region and accessing double word.

    LI(x4, PMPREGION_LXWR)
    csrw pmpcfg0, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION

    li a4, 0xbeefcafe                                            // Clean Test exit verification signature.
    RVTEST_SIGUPD(x2, x5, x4, a4, test_2_str)                                      // Signature update
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
test_1_str: .string "\"test: 1; cp: cp_na4_boundary_ld\""
test_2_str: .string "\"test: 2; cp: cp_na4_boundary\""

RVTEST_DATA_END

// Signature region for self-checking
RVTEST_SIG_SETUP
