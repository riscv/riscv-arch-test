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
// Coverpoints : cp_cfg_X and cp_cfg_RW from PMPS are partially covered in this
//                 test file. cp_cfg_A_napot is fully covered.
//
// Test Cases  : Checking XWR controls accesses in matching NAPOT region. Configuring
//               PMP in M mode and then switching to S mode. For a standard region with
//               pmpcfg_i.L = {0/1}, pmpcfg_i.A=NAPOT, all legal pmpcfg_i.XWR, making
//               {lw, sw, jalr} at that start of region, start - 4, start + 4, highest
//               word in region, just beyond top of the region. Observing proper access
//               faults for restricted regions, and accesses beyond and below the region
//               should succeed because of background region with RWX permissions.
// --------------------------------------------------------------------------------

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS:  ['S']
# params:
#   MXLEN: 64
#   NUM_PMP_ENTRIES: '>0'
#   PMP_NAPOT_SUPPORTED: true
# MARCH: rv64i_zicsr_zifencei
##### END_TEST_CONFIG #####

#define TEST_FILE "pmps_napot_legal_lxwr.S"
#define SIGUPD_COUNT 150
#define rvtest_mtrap_routine
#define rvtest_strap_routine
#define RVTEST_PRIV_TEST


#include "riscv_arch_test.h"

RVTEST_BEGIN

#if UDB_PMP_GRANULARITY != 2
  #define g   (1 << (UDB_PMP_GRANULARITY))
#else
  #define g   (1 << (UDB_PMP_GRANULARITY + 1))
#endif

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

#define PMPREGION_LXWR_1000 ((((                        PMP_NAPOT)&0xFF) << PMP5_CFG_SHIFT))
#define PMPREGION_LXWR_1001 ((((      PMP_R|            PMP_NAPOT)&0xFF) << PMP4_CFG_SHIFT))
#define PMPREGION_LXWR_1011 ((((      PMP_R|PMP_W       |PMP_NAPOT)&0xFF) << PMP3_CFG_SHIFT))
#define PMPREGION_LXWR_1100 ((((                    PMP_X|PMP_NAPOT)&0xFF) << PMP2_CFG_SHIFT))
#define PMPREGION_LXWR_1101 ((((      PMP_R         |PMP_X|PMP_NAPOT)&0xFF) << PMP1_CFG_SHIFT))
#define PMPREGION_LXWR_1111 ((((      PMP_R|PMP_W|PMP_X|PMP_NAPOT)&0xFF) << PMP0_CFG_SHIFT))

#define REGIONSTART            TEST_FOR_EXECUTION    // RAM_BASE_ADDR + PROGRAM_SIZE
#if UDB_PMP_GRANULARITY != 2
    #define PMP_MASK            ~((1 << (UDB_PMP_GRANULARITY - 3))-1)
    #define PMP_REGION_SIZE     (1 << (UDB_PMP_GRANULARITY - 3)) - 1
#else
    #define PMP_MASK            ~0
    #define PMP_REGION_SIZE     0
#endif

    RVTEST_PMP_SET_BACKGROUND x4

//                                            Verification Section
// Test Case: 4 : L -> 1 and X Permissions given to the PMP Region 2

    LA(x5, REGIONSTART)
    srl x5, x5, PMP_SHIFT
    LI(x6, PMP_MASK)
    and x5, x5, x6
    LI(x6, PMP_REGION_SIZE)
    or x5, x5, x6
    csrw pmpaddr2, x5
    LI(t1, PMPREGION_LXWR_1011|PMPREGION_LXWR_1100)
    csrw pmpcfg0, t1

    RVTEST_GOTO_LOWER_MODE    Smode        // SWITCH TO S-mode
    PMP_VERIFICATION_RWX_NAPOT    TEST_FOR_EXECUTION, test_4
    RVTEST_GOTO_MMODE

// Test Case: 5 : L -> 1 and XR Permissions given to the PMP Region 1

    LA(x5, REGIONSTART)
    srl x5, x5, PMP_SHIFT
    LI(x6, PMP_MASK)
    and x5, x5, x6
    LI(x6, PMP_REGION_SIZE)
    or x5, x5, x6
    csrw pmpaddr1, x5
    LI(t1, PMPREGION_LXWR_1011|PMPREGION_LXWR_1100|PMPREGION_LXWR_1101)
    csrw pmpcfg0, t1

    RVTEST_GOTO_LOWER_MODE    Smode        // SWITCH TO S-mode
    PMP_VERIFICATION_RWX_NAPOT    TEST_FOR_EXECUTION, test_5
    RVTEST_GOTO_MMODE

// Test Case: 6 : L -> 1 and XWR Permissions given to the PMP Region 0

    LA(x5, REGIONSTART)
    srl x5, x5, PMP_SHIFT
    LI(x6, PMP_MASK)
    and x5, x5, x6
    LI(x6, PMP_REGION_SIZE)
    or x5, x5, x6
    csrw pmpaddr0, x5
    LI(t1, PMPREGION_LXWR_1011|PMPREGION_LXWR_1100|PMPREGION_LXWR_1101|PMPREGION_LXWR_1111)
    csrw pmpcfg0, t1

    RVTEST_GOTO_LOWER_MODE    Smode        // SWITCH TO S-mode
    PMP_VERIFICATION_RWX_NAPOT    TEST_FOR_EXECUTION, test_6
    RVTEST_GOTO_MMODE

    j exit                                                        // Verification Complete, exit the test

exit:

RVTEST_CODE_END

RVTEST_DATA_BEGIN
.p2align 4

// Test case strings for reporting
test_1_str:  .string "\"test: 1;  cp: pmps_napot_legal_lwxr_sb_address\""
test_2_str:  .string "\"test: 2;  cp: pmps_napot_legal_lwxr_sh_address\""
test_3_str:  .string "\"test: 3;  cp: pmps_napot_legal_lwxr_sw_address\""
test_4_str:  .string "\"test: 4;  cp: pmps_napot_legal_lwxr_sw_address-4\""
test_5_str:  .string "\"test: 5;  cp: pmps_napot_legal_lwxr_sw_address+4\""
test_6_str:  .string "\"test: 6;  cp: pmps_napot_legal_lwxr_sw_address+g-4\""
test_7_str:  .string "\"test: 7;  cp: pmps_napot_legal_lwxr_sw_address+g\""
test_8_str:  .string "\"test: 8;  cp: pmps_napot_legal_lwxr_lb_address\""
test_9_str:  .string "\"test: 9;  cp: pmps_napot_legal_lwxr_lbu_address\""
test_10_str: .string "\"test: 10; cp: pmps_napot_legal_lwxr_lh_address\""
test_11_str: .string "\"test: 11; cp: pmps_napot_legal_lwxr_lhu_address\""
test_12_str: .string "\"test: 12; cp: pmps_napot_legal_lwxr_lw_address\""
test_13_str: .string "\"test: 13; cp: pmps_napot_legal_lwxr_lw_address-4\""
test_14_str: .string "\"test: 14; cp: pmps_napot_legal_lwxr_lw_address+4\""
test_15_str: .string "\"test: 15; cp: pmps_napot_legal_lwxr_lw_address+g-4\""
test_16_str: .string "\"test: 16; cp: pmps_napot_legal_lwxr_lw_address+g\""
test_17_str: .string "\"test: 17; cp: pmps_napot_legal_lwxr_jalr_address\""
test_18_str: .string "\"test: 18; cp: pmps_napot_legal_lwxr_jalr_address-4\""
test_19_str: .string "\"test: 19; cp: pmps_napot_legal_lwxr_jalr_address+4\""
test_20_str: .string "\"test: 20; cp: pmps_napot_legal_lwxr_jalr_address+g-4\""
test_21_str: .string "\"test: 21; cp: pmps_napot_legal_lwxr_jalr_address+g\""
test_22_str:  .string "\"test: 22;  cp: pmps_napot_legal_lwxr_sd_address\""
test_23_str:  .string "\"test: 23;  cp: pmps_napot_legal_lwxr_ld_address\""
test_24_str:  .string "\"test: 24;  cp: pmpu_napot_legal_lwxr_lwu_address\""

.p2align 12
.p2align (UDB_PMP_GRANULARITY)
TEST_FOR_EXECUTION_0:
    .rept (g>>2)
    jr ra
    .endr

.p2align (UDB_PMP_GRANULARITY)
TEST_FOR_EXECUTION:
    .rept (g>>2)
    jr ra
    .endr

RETURN_INSTRUCTION:
    nop
    nop
    jr ra                                                        // Get back to the point from where TEST_FOR_EXECUTION was called.


RVTEST_DATA_END

// Signature region for self-checking
RVTEST_SIG_SETUP
