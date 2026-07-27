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
// Coverpoints : cp_mprv for PMPU is partially covered in this file.
//
// Test Cases  : Checking L bit doesn't matter with MPRV setting to lower privilege
//                 mode. Configuring PMP in M-mode. Setting mstatus.MPRV = {0/1},
//                 mstatus.MPP = {11 / 00}. While staying in M-mode doing {lw/sw/jalr}
//                 with pmpcfg_i.L={0/1}, XWR = 111. Observing access faults for
//                 restricted execution regions even with L = 0 in effective U mode.
// --------------------------------------------------------------------------------

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS:  ['U']
# params:
#   MXLEN: 32
#   NUM_PMP_ENTRIES: '>0'
# MARCH: rv32i_zicsr_zifencei
##### END_TEST_CONFIG #####

#define SIGUPD_COUNT 50
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

#define PMPREGION_LXWR_1111   ((PMP_L|PMP_R|PMP_W|PMP_X|PMP_NAPOT)&0xFF) << PMP0_CFG_SHIFT
#define PMPREGION_LXWR_0111   ((      PMP_R|PMP_W|PMP_X|PMP_NAPOT)&0xFF) << PMP0_CFG_SHIFT

#define MPRV                    (1 << 17)
#define MPP                        (3 << 11)

#define REGIONSTART            TEST_FOR_EXECUTION    // RAM_BASE_ADDR + PROGRAM_SIZE
#if UDB_PMP_GRANULARITY != 2
    #define PMP_MASK            ~((1 << (UDB_PMP_GRANULARITY - 3))-1)
    #define PMP_REGION_SIZE     (1 << (UDB_PMP_GRANULARITY - 3)) - 1
#else
    #define PMP_MASK            ~0
    #define PMP_REGION_SIZE     0
#endif


    RVTEST_PMP_SET_BACKGROUND x4

//-------------------------------------
    LA(x5, REGIONSTART)
    srl x5, x5, PMP_SHIFT
    LI(x6, PMP_MASK)
    and x5, x5, x6
    LI(x6, PMP_REGION_SIZE)
    or x5, x5, x6
    csrw pmpaddr0, x5

    LI(x4, PMPREGION_LXWR_0111)
    csrw pmpcfg0, x4
//-------------------------------------

//                                            Verification Section
// Test Case: 1 : mstatus.MPRV = 0, L = 0, mstatus.MPP = 00 and XWR Permissions given to the PMP Region 0

    li t0, (MPP|MPRV)        // Initialize mstatus.MPRV & mstatus.MPP
    csrc mstatus, t0

    PMP_VERIFICATION_RWX    TEST_FOR_EXECUTION, test_1

// Test Case: 2 : mstatus.MPRV = 1, L = 0, mstatus.MPP = 00 and XWR Permissions given to the PMP Region 0

    li t0, (MPP|MPRV)        // Initialize mstatus.MPRV & mstatus.MPP
    csrc mstatus, t0

    li t0, (MPRV)
    csrs mstatus, t0

    PMP_VERIFICATION_RWX    TEST_FOR_EXECUTION, test_2

//-------------------------------------
    LA(x5, REGIONSTART)
    srl x5, x5, PMP_SHIFT
    LI(x6, PMP_MASK)
    and x5, x5, x6
    LI(x6, PMP_REGION_SIZE)
    or x5, x5, x6
    csrw pmpaddr0, x5

    LI(x4, PMPREGION_LXWR_1111)
    csrw pmpcfg0, x4
//-------------------------------------

// Test Case: 3 : mstatus.MPRV = 0, L = 1, mstatus.MPP = 00 and XWR Permissions given to the PMP Region 0

    li t0, (MPP|MPRV)        // Initialize mstatus.MPRV & mstatus.MPP
    csrc mstatus, t0

    PMP_VERIFICATION_RWX    TEST_FOR_EXECUTION, test_3

// Test Case: 4 : mstatus.MPRV = 1, L = 1, mstatus.MPP = 00 and XWR Permissions given to the PMP Region 0

    li t0, (MPP|MPRV)        // Initialize mstatus.MPRV & mstatus.MPP
    csrc mstatus, t0

    li t0, (MPRV)
    csrs mstatus, t0

    PMP_VERIFICATION_RWX    TEST_FOR_EXECUTION, test_4

    j exit                                                        // Verification Complete, exit the test

exit:

RVTEST_CODE_END

RVTEST_DATA_BEGIN
.p2align 4

// Test case strings for reporting
test_1_str: .string "\"test: 1; cp: pmpm_cfg_A_off_all_jalr\""
test_2_str: .string "\"test: 2; cp: pmpm_cfg_A_off_all_sw\""
test_3_str: .string "\"test: 3; cp: pmpm_cfg_A_off_all_lw\""

.p2align 12
.p2align (UDB_PMP_GRANULARITY)
TEST_FOR_EXECUTION_0:
    .rept PMP_NAPOT_REGION_PAD_WORDS  // NAPOT-safe fillers: places the region at PMP_NAPOT_REGION_START (matches cp_mprv_*'s standard_region requirement)
    jr ra
    .endr

.p2align (UDB_PMP_GRANULARITY)
TEST_FOR_EXECUTION:
    .rept (1<<(UDB_PMP_GRANULARITY))
    nop
    .endr

RETURN_INSTRUCTION:
    nop
    nop
    jr ra                                                        // Get back to the point from where TEST_FOR_EXECUTION was called.


RVTEST_DATA_END

// Signature region for self-checking
RVTEST_SIG_SETUP
