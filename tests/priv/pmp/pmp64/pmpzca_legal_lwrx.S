// ---------------------------------------------------------------------------
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
// Coverpoints : cp_cfg_RW for PMPZca are fully covered in this test file.
//
// Test Cases  : Check that WR bits control write/read access for every type of
//                 load and store. Attempt all types of reads and writes with
//                 pmpcfg_i.L=1, all legal pmpcfg_i.XWR. Observe proper access
//                 faults for restricted read/write regions
//
// Dependencies: model_test.h, arch_test.h
// ---------------------------------------------------------------------------

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: ['I','C','Smpmp']
#   MXLEN: 64
# MARCH: rv64ic_zicsr
# CONFIG_DEPENDENT: true
##### END_TEST_CONFIG #####

// Define the name of this test file for reporting and the size of the signature region
#define TEST_FILE "pmpzca_legal_lxwr.S"
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

#ifndef NUM_PMP_ENTRIES
    #define NUM_PMP_ENTRIES 16
#endif

#define NOP         0x00010001

.macro VERIFICATION_RWX ADDRESS

    LI(x4, 0xACCE)                        // Store a value which is to be checked in trap handler
    LA (x15, \ADDRESS)
    LA(x1, 1f)                            // Store the return Address in x4
    c.jalr x15
    c.nop
    c.nop
1:
    c.nop
    c.nop

    LI(x15, NOP)                                              // Value to write (NOP)
    // Store Access Check
    LA(x8, \ADDRESS)                                         // Address to be verified
    c.sw x15, 0(x8)
    c.nop
    c.nop
    c.nop
    c.nop
    c.lw x15, 0(x8)
    c.nop
    c.nop
    c.nop
    c.nop

    mv t0, sp
    addi sp, x8, 0
    c.swsp x15, 0(sp)
    c.nop
    c.nop
    c.nop
    c.nop
    c.nop
    c.nop
    c.nop
    c.nop
    c.lwsp x15, 0(sp)
    c.nop
    c.nop
    mv sp, t0

    c.nop
    c.nop
    c.nop
    c.nop
    c.nop
    c.nop
    c.nop

.endm

main:
    // Loop to SET ALL pmpcfg REGs to zero
    .set pmpcfgi, CSR_PMPCFG0
    .rept NUM_PMP_ENTRIES/8
    csrw pmpcfgi , x0
    .set pmpcfgi, pmpcfgi+2
    .endr

    // Loop to SET ALL pmpaddr REGs to zero
    .set pmpaddri, CSR_PMPADDR0
    .rept NUM_PMP_ENTRIES
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
#define REGIONSTART            0x80002000    // RAM_BASE_ADDR + PROGRAM_SIZE
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
    csrw     pmpaddr15, x4

    //Lock the Background region.
    LI(x4, PMP_REGION_GLOBAL)
    csrw pmpcfg2, x4

//                                            Verification Section
// Test Case: 1 : L -> No Permissions given to the PMP Region 5

    LA(x5, STANDARD_REGION)
    csrw pmpaddr5, x5

    LI(x4, PMPREGION_LXWR_1000)
    csrw pmpcfg0, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION

    li a4, 0xdeadbeef
    RVTEST_SIGUPD(x2, x5, x4, a4, test_1_str)

// Test Case: 2 : L -> R Permission given to the PMP Region 4

    LA(x5, STANDARD_REGION)
    csrw pmpaddr4, x5

    LI(x4, PMPREGION_LXWR_1001)
    csrw pmpcfg0, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION

    li a4, 0xdeadbeef
    RVTEST_SIGUPD(x2, x5, x4, a4, test_2_str)

// Test Case: 3 : L ->  WR Permissions given to the PMP Region 3

    LA(x5, STANDARD_REGION)
    csrw pmpaddr3, x5

    LI(x4, PMPREGION_LXWR_1011)
    csrw pmpcfg0, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION

    li a4, 0xdeadbeef
    RVTEST_SIGUPD(x2, x5, x4, a4, test_3_str)

// Test Case: 4 : L ->  X Permissions given to the PMP Region 2

    LA(x5, STANDARD_REGION)
    csrw pmpaddr2, x5

    LI(x4, PMPREGION_LXWR_1100)
    csrw pmpcfg0, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION

    li a4, 0xdeadbeef
    RVTEST_SIGUPD(x2, x5, x4, a4, test_4_str)

// Test Case: 5 : L ->  XR Permissions given to the PMP Region 1

    LA(x5, STANDARD_REGION)
    csrw pmpaddr1, x5

    LI(x4, PMPREGION_LXWR_1101)
    csrw pmpcfg0, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION

    li a4, 0xdeadbeef
    RVTEST_SIGUPD(x2, x5, x4, a4, test_5_str)

// Test Case: 6 : L ->  XWR Permissions given to the PMP Region 0

    LA(x5, STANDARD_REGION)
    csrw pmpaddr0, x5

    LI(x4, PMPREGION_LXWR_1111)
    csrw pmpcfg0, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION

    li a4, 0xdeadbeef
    RVTEST_SIGUPD(x2, x5, x4, a4, test_6_str)

    j exit                                                        // Verification Complete, exit the test

.align 13
.align (RVMODEL_PMP_GRAIN+2)
TEST_FOR_EXECUTION:
    .rept (1<<RVMODEL_PMP_GRAIN+2)
    c.nop
    c.nop
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
test_1_str: .string "\"test: 1; cp: pmpzca_legal_lxwr_no_permission\""
test_2_str: .string "\"test: 1; cp: pmpzca_legal_lxwr_read_permission\""
test_3_str: .string "\"test: 1; cp: pmpzca_legal_lxwr_read_write_permission\""
test_4_str: .string "\"test: 1; cp: pmpzca_legal_lxwr_executre_permission\""
test_5_str: .string "\"test: 1; cp: pmpzca_legal_lxwr_execute_read_permission\""
test_6_str: .string "\"test: 1; cp: pmpzca_legal_lxwr_all_permission\""

RVTEST_DATA_END

// Signature region for self-checking
RVTEST_SIG_SETUP
