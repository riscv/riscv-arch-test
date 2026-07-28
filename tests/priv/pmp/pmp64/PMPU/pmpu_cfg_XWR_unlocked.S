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
//               PMP in M mode and then switching to U mode. For a standard region with
//               pmpcfg_i.L = 1, pmpcfg_i.A=NAPOT, all legal pmpcfg_i.XWR, making
//               {lw, sw, jalr} at that start of region.
// --------------------------------------------------------------------------------

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS:  ['U']
# params:
#   MXLEN: 64
#   NUM_PMP_ENTRIES: '>0'
# MARCH: rv64i_zicsr_zifencei
##### END_TEST_CONFIG #####

#define SIGUPD_COUNT 100
#define RVTEST_PRIV_TEST


#include "riscv_arch_test.h"

RVTEST_BEGIN                                // Encoded Instruction of nop (64 bit case)

.macro VERIFICATION_RWX ADDRESS TEST_CASE

    // Execution Access Check
    LA (a4, \ADDRESS)
    LA(x1, 1f)                            // Store the return Address in x1
    RVTEST_FENCEI                              // sync I-cache: a prior store may have updated this executable region
    \TEST_CASE\()_1:
    jalr ra, 0(a4)
    nop
1:
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_1, test_1_str)

    LI(a4, DOUBLE_NOP)                                              // Value to write (DOUBLE_NOP)
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
    \TEST_CASE\()_5:
    sd a4, 0(a5)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_5, test_5_str)

    LA(a5, \ADDRESS)                                         // Address to be verified
    \TEST_CASE\()_6:
    lb a4, 0(a5)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_6, test_6_str)
    \TEST_CASE\()_7:
    lbu a4, 0(a5)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_7, test_7_str)
    \TEST_CASE\()_8:
    lh a4, 0(a5)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_8, test_8_str)
    \TEST_CASE\()_9:
    lhu a4, 0(a5)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_9, test_9_str)
    \TEST_CASE\()_10:
    lw a4, 0(a5)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_10, test_10_str)
    \TEST_CASE\()_11:
    lwu a4, 0(a5)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_11, test_11_str)
    \TEST_CASE\()_12:
    ld a4, 0(a5)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_12, test_12_str)

.endm

main:
    // Loop to SET pmpcfg REGs to zero
    .set pmpcfgi, CSR_PMPCFG0
    .rept UDB_NUM_PMP_ENTRIES/8
    csrw pmpcfgi , x0
    .set pmpcfgi, pmpcfgi+2
    .endr

    // Loop to SET pmpaddr REGs to zero
    .set pmpaddri, CSR_PMPADDR0
    .rept UDB_NUM_PMP_ENTRIES
    csrw pmpaddri, x0
    .set pmpaddri, pmpaddri+1
    .endr

#define PMPREGION_LXWR_0000 ((((                  PMP_NAPOT)&0xFF) << PMP5_CFG_SHIFT))
#define PMPREGION_LXWR_0001 ((((PMP_R|            PMP_NAPOT)&0xFF) << PMP4_CFG_SHIFT))
#define PMPREGION_LXWR_0011 ((((PMP_R|PMP_W       |PMP_NAPOT)&0xFF) << PMP3_CFG_SHIFT))
#define PMPREGION_LXWR_0100 ((((               PMP_X|PMP_NAPOT)&0xFF) << PMP2_CFG_SHIFT))
#define PMPREGION_LXWR_0101 ((((PMP_R         |PMP_X|PMP_NAPOT)&0xFF) << PMP1_CFG_SHIFT))
#define PMPREGION_LXWR_0111 ((((PMP_R|PMP_W|PMP_X|PMP_NAPOT)&0xFF) << PMP0_CFG_SHIFT))

#define REGIONSTART            TEST_FOR_EXECUTION    // RAM_BASE_ADDR + PROGRAM_SIZE
#if UDB_PMP_GRANULARITY != 2
    #define PMP_MASK            ~((1 << (UDB_PMP_GRANULARITY-3))-1)
    #define PMP_REGION_SIZE     (1 << (UDB_PMP_GRANULARITY-3)) - 1
#else
    #define PMP_MASK            ~0
    #define PMP_REGION_SIZE     0
#endif


    RVTEST_PMP_SET_BACKGROUND x4

//                                            Verification Section
// Test Case: 1 : L -> 0 and No Permissions given to the PMP Region 5

    LA(x5, REGIONSTART)
    srl x5, x5, PMP_SHIFT
    LI(x6, PMP_MASK)
    and x5, x5, x6
    LI(x6, PMP_REGION_SIZE)
    or x5, x5, x6
    csrw pmpaddr5, x5
    LI(t1, PMPREGION_LXWR_0000)
    csrw pmpcfg0, t1

    RVTEST_GOTO_LOWER_MODE    Umode        // SWITCH TO U-mode
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_1
    RVTEST_GOTO_MMODE

// Test Case: 2 : L -> 0 and R Permissions given to the PMP Region 4

    LA(x5, REGIONSTART)
    srl x5, x5, PMP_SHIFT
    LI(x6, PMP_MASK)
    and x5, x5, x6
    LI(x6, PMP_REGION_SIZE)
    or x5, x5, x6
    csrw pmpaddr4, x5
    LI(t1, PMPREGION_LXWR_0001)
    csrw pmpcfg0, t1

    RVTEST_GOTO_LOWER_MODE    Umode        // SWITCH TO U-mode
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_2
    RVTEST_GOTO_MMODE

// Test Case: 3 : L -> 0 and WR Permissions given to the PMP Region 3

    LA(x5, REGIONSTART)
    srl x5, x5, PMP_SHIFT
    LI(x6, PMP_MASK)
    and x5, x5, x6
    LI(x6, PMP_REGION_SIZE)
    or x5, x5, x6
    csrw pmpaddr3, x5
    LI(t1, PMPREGION_LXWR_0011)
    csrw pmpcfg0, t1

    RVTEST_GOTO_LOWER_MODE    Umode        // SWITCH TO U-mode
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_3
    RVTEST_GOTO_MMODE

// Test Case: 4 : L -> 0 and X Permissions given to the PMP Region 2

    LA(x5, REGIONSTART)
    srl x5, x5, PMP_SHIFT
    LI(x6, PMP_MASK)
    and x5, x5, x6
    LI(x6, PMP_REGION_SIZE)
    or x5, x5, x6
    csrw pmpaddr2, x5
    LI(t1, PMPREGION_LXWR_0100)
    csrw pmpcfg0, t1

    RVTEST_GOTO_LOWER_MODE    Umode        // SWITCH TO U-mode
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_4
    RVTEST_GOTO_MMODE

// Test Case: 5 : L -> 0 and XR Permissions given to the PMP Region 1

    LA(x5, REGIONSTART)
    srl x5, x5, PMP_SHIFT
    LI(x6, PMP_MASK)
    and x5, x5, x6
    LI(x6, PMP_REGION_SIZE)
    or x5, x5, x6
    csrw pmpaddr1, x5
    LI(t1, PMPREGION_LXWR_0101)
    csrw pmpcfg0, t1

    RVTEST_GOTO_LOWER_MODE    Umode        // SWITCH TO U-mode
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_5
    RVTEST_GOTO_MMODE

// Test Case: 6 : L -> 0 and XWR Permissions given to the PMP Region 0

    LA(x5, REGIONSTART)
    srl x5, x5, PMP_SHIFT
    LI(x6, PMP_MASK)
    and x5, x5, x6
    LI(x6, PMP_REGION_SIZE)
    or x5, x5, x6
    csrw pmpaddr0, x5
    LI(t1, PMPREGION_LXWR_0111)
    csrw pmpcfg0, t1

    RVTEST_GOTO_LOWER_MODE    Umode        // SWITCH TO U-mode
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_6
    RVTEST_GOTO_MMODE

    j exit                                                        // Verification Complete, exit the test

exit:

RVTEST_CODE_END
RVTEST_DATA_BEGIN
.p2align 4

// Test case strings for reporting
test_1_str: .string "\"test: 1; cp: pmpu_cfg_XWR_unlocked.S_jalr\""
test_2_str: .string "\"test: 2; cp: pmpu_cfg_XWR_unlocked.S_sb\""
test_3_str: .string "\"test: 3; cp: pmpu_cfg_XWR_unlocked.S_sh\""
test_4_str: .string "\"test: 4; cp: pmpu_cfg_XWR_unlocked.S_sw\""
test_5_str: .string "\"test: 5; cp: pmpu_cfg_XWR_unlocked.S_sd\""
test_6_str: .string "\"test: 6; cp: pmpu_cfg_XWR_unlocked.S_lb\""
test_7_str: .string "\"test: 7; cp: pmpu_cfg_XWR_unlocked.S_lbu\""
test_8_str: .string "\"test: 8; cp: pmpu_cfg_XWR_unlocked.S_lh\""
test_9_str: .string "\"test: 9; cp: pmpu_cfg_XWR_unlocked.S_lhu\""
test_10_str: .string "\"test: 10; cp: pmpu_cfg_XWR_unlocked.S_lw\""
test_11_str: .string "\"test: 11; cp: pmpu_cfg_XWR_unlocked.S_lwu\""
test_12_str: .string "\"test: 12; cp: pmpu_cfg_XWR_unlocked.S_ld\""

.p2align 12
.p2align (UDB_PMP_GRANULARITY)
TEST_FOR_EXECUTION_0:
    .rept (1 << (UDB_PMP_GRANULARITY - 2))              // one PMP granule of return-instruction fillers: places the region on the next granule boundary (= PMP_REGION_START at coverage grain 2), grain-aligned at larger grains
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
