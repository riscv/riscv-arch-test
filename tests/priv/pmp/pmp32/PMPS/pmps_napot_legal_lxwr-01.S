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
// Coverpoints : cp_cfg_X, cp_cfg_A_napot and cp_cfg_RW from PMPS are partially covered in this
//                 test file.
//
// Test Cases  : Checking XWR controls accesses in matching NAPOT region. Configuring
//               PMP in M mode and then switching to S mode. For a standard region with
//               pmpcfg_i.L = {0/1}, pmpcfg_i.A=NAPOT, all legal pmpcfg_i.XWR, making
//               {lw, sw, jalr} at that start of region, start - 4, start + 4, highest
//               word in region, just beyond top of the region. Observing proper access
//               faults for restricted regions, and accesses beyond and below the region
//               should succeed because of background region with RWX permissions.
//
// --------------------------------------------------------------------------------

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS:  ['S']
# params:
#   MXLEN: 32
#   NUM_PMP_ENTRIES: '>0'
# MARCH: rv32i_zicsr
##### END_TEST_CONFIG #####

#define TEST_FILE "pmps_napot_legal_lxwr.S"
#define SIGUPD_COUNT 150
#define rvtest_mtrap_routine
#define rvtest_strap_routine
#define RVTEST_PRIV_TEST
#define SKIP_MEPC

#include "riscv_arch_test.h"

RVTEST_BEGIN

#if RVMODEL_PMP_GRAIN != 0
  #define g   (1 << (RVMODEL_PMP_GRAIN + 2))
#else
  #define g   (1 << (RVMODEL_PMP_GRAIN + 3))
#endif
.macro VERIFICATION_RWX ADDRESS TEST_CASE

    LI(x4, 0xACCE)                      // Store a value which is to be checked in trap handler
    // Execution Access Check
    LA (a4, \ADDRESS)
    LA(x1, 1f)                          // Store the return Address in x1
    \TEST_CASE\()_17:
    jalr ra, 0(a4)
    nop
    nop
1:
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_17, test_17_str)

    addi a4, a4, -4                     // REGIONSTART - 4
    LA(x1, 2f)                          // Store the return Address in x1
    \TEST_CASE\()_18:
    jalr ra, 0(a4)
    nop
    nop
2:
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_18, test_18_str)

    addi a4, a4, 8                      // REGIONSTART + 4
    LA(x1, 3f)                          // Store the return Address in x1
    \TEST_CASE\()_19:
    jalr ra, 0(a4)
    nop
    nop
3:
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_19, test_19_str)

    addi a4, a4, (g-8)                  // REGIONSTART + g - 4
    LA(x1, 4f)                          // Store the return Address in x1
    \TEST_CASE\()_20:
    jalr ra, 0(a4)
    nop
    nop
4:
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_20, test_20_str)

    addi a4, a4, 4                      // REGIONSTART + g
    LA(x1, 5f)                          // Store the return Address in x1
    \TEST_CASE\()_21:
    jalr ra, 0(a4)
    nop
    nop
5:
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_21, test_21_str)

    LI(a4, NOP)                                             // Value to write (NOP)
    // Store Access Check
    LA(a5, \ADDRESS)                                        // Address to be verified

    \TEST_CASE\()_1:
    sb a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_1, test_1_str)

    \TEST_CASE\()_2:
    sh a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_2, test_2_str)

    \TEST_CASE\()_3:
    sw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_3, test_3_str)

    addi a5, a5, -4                                         // REGIONSTART - 4

    \TEST_CASE\()_4:
    sw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_4, test_4_str)

    addi a5, a5, 8                                          // REGIONSTART + 4

    \TEST_CASE\()_5:
    sw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_5, test_5_str)

    addi a5, a5, (g-8)                                      // REGIONSTART + g - 4

    \TEST_CASE\()_6:
    sw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_6, test_6_str)

    addi a5, a5, 4                                          // REGIONSTART + g

    \TEST_CASE\()_7:
    sw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_7, test_7_str)

    LA(a5, \ADDRESS)                                        // Address to be verified

    \TEST_CASE\()_8:
    lb a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_8, test_8_str)                                   // Signature update

    \TEST_CASE\()_9:
    lbu a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_9, test_9_str)                                   // Signature update

    \TEST_CASE\()_10:
    lh a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_10, test_10_str)                                   // Signature update

    \TEST_CASE\()_11:
    lhu a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_11, test_11_str)                                   // Signature update

    \TEST_CASE\()_12:
    lw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_12, test_12_str)                                   // Signature update

    addi a5, a5, -4                                         // REGIONSTART - 4

    \TEST_CASE\()_13:
    lw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_13, test_13_str)                                   // Signature update

    addi a5, a5, 8                                          // REGIONSTART + 4

    \TEST_CASE\()_14:
    lw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_14, test_14_str)                                   // Signature update

    addi a5, a5, (g-8)                                      // REGIONSTART + g - 4

    \TEST_CASE\()_15:
    lw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_15, test_15_str)                                   // Signature update

    addi a5, a5, 4                                          // REGIONSTART + g

    \TEST_CASE\()_16:
    lw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_16, test_16_str)                                    // Signature update

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
#define PMPREGION_LXWR_1000 ((((                        PMP_NAPOT)&0xFF) << PMP1_CFG_SHIFT))
#define PMPREGION_LXWR_1001 ((((      PMP_R|            PMP_NAPOT)&0xFF) << PMP0_CFG_SHIFT))
#define PMPREGION_LXWR_1011 ((((      PMP_R|PMP_W       |PMP_NAPOT)&0xFF) << PMP3_CFG_SHIFT))
#define PMPREGION_LXWR_1100 ((((                    PMP_X|PMP_NAPOT)&0xFF) << PMP2_CFG_SHIFT))
#define PMPREGION_LXWR_1101 ((((      PMP_R         |PMP_X|PMP_NAPOT)&0xFF) << PMP1_CFG_SHIFT))
#define PMPREGION_LXWR_1111 ((((      PMP_R|PMP_W|PMP_X|PMP_NAPOT)&0xFF) << PMP0_CFG_SHIFT))

#define PMPADDRESS_TOP_GLOBAL        -1                                                // All memory region
#define REGIONSTART            TEST_FOR_EXECUTION    // RAM_BASE_ADDR + PROGRAM_SIZE
#if RVMODEL_PMP_GRAIN != 0
    #define PMP_MASK            ~((1 << (RVMODEL_PMP_GRAIN - 1))-1)
    #define PMP_REGION_SIZE     (1 << (RVMODEL_PMP_GRAIN - 1)) - 1
#else
    #define PMP_MASK            ~0
    #define PMP_REGION_SIZE     0
#endif

    csrw satp, zero                // Disable address translation.

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

    RVTEST_GOTO_LOWER_MODE    Smode        // SWITCH TO S-mode
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_1
    RVTEST_GOTO_MMODE

// Test Case: 2 : L -> 1 and R Permissions given to the PMP Region 4

    LA(x5, REGIONSTART)
    srl x5, x5, PMP_SHIFT
    andi x5, x5, PMP_MASK
    ori x5, x5, PMP_REGION_SIZE
    csrw pmpaddr4, x5

    LI(t1, PMPREGION_LXWR_1000|PMPREGION_LXWR_1001)
    csrw pmpcfg1, t1

    RVTEST_GOTO_LOWER_MODE    Smode        // SWITCH TO S-mode
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

    RVTEST_GOTO_LOWER_MODE    Smode        // SWITCH TO S-mode
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_3
    RVTEST_GOTO_MMODE

    j exit                                                        // Verification Complete, exit the test

exit:

RVTEST_CODE_END

RVTEST_DATA_BEGIN
.align 4

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
test_17_str: .string "\"test: 16; cp: pmps_napot_legal_lwxr_jalr_address\""
test_18_str: .string "\"test: 13; cp: pmps_napot_legal_lwxr_jalr_address-4\""
test_19_str: .string "\"test: 14; cp: pmps_napot_legal_lwxr_jalr_address+4\""
test_20_str: .string "\"test: 15; cp: pmps_napot_legal_lwxr_jalr_address+g-4\""
test_21_str: .string "\"test: 16; cp: pmps_napot_legal_lwxr_jalr_address+g\""

.align 12
TEST_FOR_EXECUTION_0:
    .rept 1024
    nop
    .endr

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
