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
// Coverpoints : cp_mprv for PMPS is partially covered in this file.
//
// Test Cases  : Checking L bit doesn't matter with MPRV setting to lower privilege
//                 mode. Configuring PMP in M-mode. Setting mstatus.MPRV = {0/1},
//                 mstatus.MPP = {11 / 01}. While staying in M-mode doing {lw/sw/jalr}
//                 with pmpcfg_i.L={0/1}, XWR = 000. Observing access faults for
//                 restricted execution regions even with L = 0 in effective S mode.
// --------------------------------------------------------------------------------

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS:  ['I','S']
# params:
#   MXLEN: 64
#   NUM_PMP_ENTRIES: '>0'
# MARCH: rv64i_zicsr
##### END_TEST_CONFIG #####

#define TEST_FILE "pmps_mprv_check-01.S"
#define SIGUPD_COUNT 100
#define rvtest_mtrap_routine
#define rvtest_strap_routine
#define RVTEST_PRIV_TEST
#define SKIP_MEPC

#include "riscv_arch_test.h"

RVTEST_BEGIN                            // Encoded Instruction of nop (64 bit case)

.macro VERIFICATION_X ADDRESS TEST_CASE      // {jalr, sw, lw} at start of region
    // Execution Access Check
    LA (a4, \ADDRESS)
    LI(x4, 0xACCE)                        // Store a value which is to be checked in trap handler
    LA(x1, 1f)                            // Store the return Address in x1
    \TEST_CASE\()_1:
    jalr ra, 0(a4)
    nop
1:
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_1, test_1_str)

.endm

.macro VERIFICATION_W ADDRESS TEST_CASE      // {jalr, sw, lw} at start of region

    // Store Access Check
    LA(a5, \ADDRESS)                                         // Address to be verified
    LI(a4, DOUBLE_NOP)                                              // Value to write (DOUBLE_NOP)
    \TEST_CASE\()_2:
    sw a4, 0(a5)                                             // Word store test
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_2, test_2_str)

.endm

.macro VERIFICATION_R ADDRESS TEST_CASE      // {jalr, sw, lw} at start of region

    LA(a5, \ADDRESS)
    LI(a4, DOUBLE_NOP)                                              // Value to write (DOUBLE_NOP)
    // Load Access Check
    \TEST_CASE\()_3:
    lw a4, 0(a5)                                             // Word load test
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_3, test_3_str)

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

#define PMP_REGION_GLOBAL      ((PMP_L|PMP_R|PMP_W|PMP_X|PMP_NAPOT)&0xFF)  // Background region with RWX enable.
#define PMPREGION_LXWR_1000   ((PMP_L|                  PMP_NAPOT)&0xFF) << PMP0_CFG_SHIFT
#define PMPREGION_LXWR_0000   ((                        PMP_NAPOT)&0xFF) << PMP0_CFG_SHIFT

#define MPRV                    (1 << 17)
#define S_MODE                    (1 << 11)
#define M_MODE                    (3 << 11)

#define PMPADDRESS_TOP_GLOBAL        -1                                                // All memory region
#define REGIONSTART            TEST_FOR_EXECUTION    // RAM_BASE_ADDR + PROGRAM_SIZE
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
    LI(x4, PMP_REGION_GLOBAL << PMP7_CFG_SHIFT)
    csrw pmpcfg2, x4

//-------------------------------------
    LA(x5, REGIONSTART)
    srl x5, x5, PMP_SHIFT
    andi x5, x5, PMP_MASK
    ori x5, x5, PMP_REGION_SIZE
    csrw pmpaddr0, x5

    LI(x4, PMPREGION_LXWR_0000)
    csrw pmpcfg0, x4
//-------------------------------------

//                                            Verification Section
// Test Case: 1 : mstatus.MPRV = 0, L = 0, mstatus.MPP = 01 and No Permissions given to the PMP Region 0

    li t0, (MPRV|M_MODE)        // Initialize mstatus.MPRV & mstatus.MPP
    csrc mstatus, t0

    li t0, (S_MODE)
    csrs mstatus, t0

    VERIFICATION_X    TEST_FOR_EXECUTION, test_1

    li t0, (S_MODE)
    csrs mstatus, t0

    VERIFICATION_W    TEST_FOR_EXECUTION, test_2

    li t0, (S_MODE)
    csrs mstatus, t0

    VERIFICATION_R    TEST_FOR_EXECUTION, test_3

// Test Case: 2 : mstatus.MPRV = 1, L = 0, mstatus.MPP = 01 and No Permissions given to the PMP Region 0

    li t0, (M_MODE|MPRV)        // Initialize mstatus.MPRV & mstatus.MPP
    csrc mstatus, t0

    li t0, (MPRV|S_MODE)
    csrs mstatus, t0

    VERIFICATION_X    TEST_FOR_EXECUTION, test_4

    li t0, (MPRV|S_MODE)
    csrs mstatus, t0

    VERIFICATION_W    TEST_FOR_EXECUTION, test_5

    li t0, (MPRV|S_MODE)
    csrs mstatus, t0

    VERIFICATION_R    TEST_FOR_EXECUTION, test_6

//-------------------------------------
    LA(x5, REGIONSTART)
    srl x5, x5, PMP_SHIFT
    andi x5, x5, PMP_MASK
    ori x5, x5, PMP_REGION_SIZE
    csrw pmpaddr0, x5

    LI(x4, PMPREGION_LXWR_1000)
    csrw pmpcfg0, x4
//-------------------------------------

// Test Case: 3 : mstatus.MPRV = 0, L = 1, mstatus.MPP = 01 and No Permissions given to the PMP Region 0

    li t0, (MPRV|M_MODE)        // Initialize mstatus.MPRV & mstatus.MPP
    csrc mstatus, t0

    li t0, (S_MODE)
    csrs mstatus, t0

    VERIFICATION_X    TEST_FOR_EXECUTION, test_7

    li t0, (S_MODE)
    csrs mstatus, t0

    VERIFICATION_W    TEST_FOR_EXECUTION, test_8

    li t0, (S_MODE)
    csrs mstatus, t0

    VERIFICATION_R    TEST_FOR_EXECUTION, test_9

// Test Case: 4 : mstatus.MPRV = 1, L = 1, mstatus.MPP = 01 and No Permissions given to the PMP Region 0

    li t0, (M_MODE|MPRV)        // Initialize mstatus.MPRV & mstatus.MPP
    csrc mstatus, t0

    li t0, (MPRV|S_MODE)
    csrs mstatus, t0

    VERIFICATION_X    TEST_FOR_EXECUTION, test_10

    li t0, (MPRV|S_MODE)
    csrs mstatus, t0

    VERIFICATION_W    TEST_FOR_EXECUTION, test_11

    li t0, (MPRV|S_MODE)
    csrs mstatus, t0

    VERIFICATION_R    TEST_FOR_EXECUTION, test_12

    j exit                                                        // Verification Complete, exit the test

exit:

RVTEST_CODE_END
RVTEST_DATA_BEGIN
.align 4

// Test case strings for reporting
test_1_str: .string "\"test: 1; cp: pmpm_cfg_A_off_all_jalr\""
test_2_str: .string "\"test: 2; cp: pmpm_cfg_A_off_all_sw\""
test_3_str: .string "\"test: 3; cp: pmpm_cfg_A_off_all_lw\""

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
