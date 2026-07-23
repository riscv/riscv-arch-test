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
// Coverpoints : cp_cfg_A_tor for PMPS is partially covered in this test file.
//
// Test Cases  : Configuring PMP in M mode and then switching to S mode.
//               Checking XWR controls accesses in matching TOR region. With
//               pmpcfg_i.L =1, pmpcfg_i.A = TOR, all legal pmpcfg_i.XWR,
//               default TOR region, address-g in pmpaddr_i-1: making {lw,sw,jalr}
//               address, address-4, address-g, address-g-4.  Observing proper
//               access faults for restricted regions.
// --------------------------------------------------------------------------------

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS:  ['S']
# params:
#   MXLEN: 64
#   NUM_PMP_ENTRIES: '>0'
#   PMP_TOR_SUPPORTED: true
# MARCH: rv64i_zicsr_zifencei
##### END_TEST_CONFIG #####

#define TEST_FILE "pmps_tor_legal_lxwr.S"
#define SIGUPD_COUNT 150
#define rvtest_mtrap_routine
#define rvtest_strap_routine
#define RVTEST_PRIV_TEST


#include "riscv_arch_test.h"

RVTEST_BEGIN

#define g    (1<<(UDB_PMP_GRANULARITY))

.macro VERIFICATION_RWX ADDRESS TEST_CASE

    RVTEST_FENCEI

    // Execution Access Check
    LA (a4, \ADDRESS)
    LA(x1, 1f)                          // Store the return Address in x1
    \TEST_CASE\()_11:
    jalr ra, 0(a4)
    nop
    nop
1:
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_11, test_11_str)

    LA (a4, \ADDRESS)
    addi a4, a4, -4                     // REGIONSTART - 4
    LA(x1, 2f)                          // Store the return Address in x1
    \TEST_CASE\()_12:
    jalr ra, 0(a4)
    nop
    nop
2:
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_12, test_12_str)

    LA (a4, \ADDRESS)
    addi a4, a4, 8                      // REGIONSTART + 4
    LA(x1, 3f)                          // Store the return Address in x1
    \TEST_CASE\()_13:
    jalr ra, 0(a4)
    nop
    nop
3:
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_13, test_13_str)

    LA (a4, \ADDRESS)
    li t0, (g-8)
    add a4, a4, t0                  // REGIONSTART + g - 4
    LA(x1, 4f)                          // Store the return Address in x1
    \TEST_CASE\()_14:
    jalr ra, 0(a4)
    nop
    nop
4:
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_14, test_14_str)

    LA (a4, \ADDRESS)
    addi a4, a4, 4                      // REGIONSTART + g
    \TEST_CASE\()_15:
    LA(x1, 5f)                          // Store the return Address in x1
    jalr ra, 0(a4)
    nop
    nop
5:
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_15, test_15_str)

    LI(a4, NOP)                                             // Value to write (NOP)
    // Store Access Check
    LA(a5, \ADDRESS)                                        // Address to be verified

    \TEST_CASE\()_1:
    sw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_1, test_1_str)

    LA(a5, \ADDRESS)                                        // Address to be verified
    addi a5, a5, -4                                         // REGIONSTART - 4

    \TEST_CASE\()_2:
    sw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_2, test_2_str)

    LA(a5, \ADDRESS)                                        // Address to be verified
    addi a5, a5, 8                                          // REGIONSTART + 4

    \TEST_CASE\()_3:
    sw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_3, test_3_str)

    LA(a5, \ADDRESS)                                        // Address to be verified
    li t0, (g-8)
    add a5, a5, t0                                      // REGIONSTART + g - 4

    \TEST_CASE\()_4:
    sw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_4, test_4_str)

    LA(a5, \ADDRESS)                                        // Address to be verified
    addi a5, a5, 4                                          // REGIONSTART + g

    \TEST_CASE\()_5:
    sw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_5, test_5_str)

    LA(a5, \ADDRESS)                                        // Address to be verified

    \TEST_CASE\()_6:
    lw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_6, test_6_str)                                   // Signature update

    addi a5, a5, -4                                         // REGIONSTART - 4

    \TEST_CASE\()_7:
    lw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_7, test_7_str)                                   // Signature update

    addi a5, a5, 8                                          // REGIONSTART + 4

    \TEST_CASE\()_8:
    lw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_8, test_8_str)                                   // Signature update

    li t0, (g-8)
    add a5, a5, t0                                     // REGIONSTART + g - 4

    \TEST_CASE\()_9:
    lw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_9, test_9_str)                                   // Signature update

    addi a5, a5, 4                                          // REGIONSTART + g

    \TEST_CASE\()_10:
    lw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_10, test_10_str)                                   // Signature update

.endm

main:
    // Loop to SET ALL pmpcfg REGs to zero
    .set pmpcfgi, CSR_PMPCFG0
    .rept UDB_NUM_PMP_ENTRIES/8
    csrw pmpcfgi , x0
    .set pmpcfgi, pmpcfgi+2
    .endr

    // Loop to SET ALL pmpaddr REGs to zero
    .set pmpaddri, CSR_PMPADDR0
    .rept UDB_NUM_PMP_ENTRIES
    csrw pmpaddri, x0
    .set pmpaddri, pmpaddri+1
    .endr

#define PMPREGION_LXWR_0100 ((((                    PMP_X|PMP_TOR  )&0xFF) << PMP5_CFG_SHIFT))
#define PMPREGION_LXWR_0101 ((((      PMP_R         |PMP_X|PMP_TOR  )&0xFF) << PMP3_CFG_SHIFT))
#define PMPREGION_LXWR_0111 ((((      PMP_R|PMP_W|PMP_X|PMP_TOR  )&0xFF) << PMP1_CFG_SHIFT))

#define REGIONSTART            TEST_FOR_EXECUTION        // RAM_BASE_ADDR + PROGRAM_SIZE


    RVTEST_PMP_SET_BACKGROUND x4

//                                            Verification Section

// Test Case: 4 : L -> 0 and X Permissions given to the PMP Region 5

    LA(x6, REGIONSTART)
    li t0, g
    add x6, x6, t0
    srl x6, x6, PMP_SHIFT
    csrw pmpaddr5, x6
    LA(x5, REGIONSTART)
    srl x5, x5, PMP_SHIFT
    csrw pmpaddr4, x5
    LI(x4, PMPREGION_LXWR_0100)
    csrw pmpcfg0, x4

    RVTEST_GOTO_LOWER_MODE    Smode        // SWITCH TO S-mode
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_4
    RVTEST_GOTO_MMODE

// Test Case: 5 : L -> 0 and RX Permissions given to the PMP Region 3

    LA(x6, REGIONSTART)
    li t0, g
    add x6, x6, t0
    srl x6, x6, PMP_SHIFT
    csrw pmpaddr3, x6
    LA(x5, REGIONSTART)
    srl x5, x5, PMP_SHIFT
    csrw pmpaddr2, x5
    LI(x4, PMPREGION_LXWR_0101)
    csrw pmpcfg0, x4

    RVTEST_GOTO_LOWER_MODE    Smode        // SWITCH TO S-mode
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_5
    RVTEST_GOTO_MMODE

// Test Case: 6 : L -> 0 and XWR Permissions given to the PMP Region 1

    LA(x6, REGIONSTART)
    li t0, g
    add x6, x6, t0
    srl x6, x6, PMP_SHIFT
    csrw pmpaddr1, x6
    LA(x5, REGIONSTART)
    srl x5, x5, PMP_SHIFT
    csrw pmpaddr0, x5
    LI(x4, PMPREGION_LXWR_0111)
    csrw pmpcfg0, x4

    RVTEST_GOTO_LOWER_MODE    Smode        // SWITCH TO S-mode
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_6
    RVTEST_GOTO_MMODE

    j exit                                                        // Verification Complete, exit the test

exit:

RVTEST_CODE_END

RVTEST_DATA_BEGIN
.p2align 4

// Test case strings for reporting
test_1_str:  .string "\"test: 1;  cp: cp_cfg_A_tor_sw_address\""
test_2_str:  .string "\"test: 2;  cp: cp_cfg_A_tor_sw_address-4\""
test_3_str:  .string "\"test: 3;  cp: cp_cfg_A_tor_sw_address+4\""
test_4_str:  .string "\"test: 4;  cp: cp_cfg_A_tor_sw_address+g-4\""
test_5_str:  .string "\"test: 5;  cp: cp_cfg_A_tor_sw_address+g\""

test_6_str:  .string "\"test: 6;  cp: cp_cfg_A_tor_lw_address\""
test_7_str:  .string "\"test: 7;  cp: cp_cfg_A_tor_lw_address-4\""
test_8_str:  .string "\"test: 8;  cp: cp_cfg_A_tor_lw_address+4\""
test_9_str:  .string "\"test: 9;  cp: cp_cfg_A_tor_lw_address+g-4\""
test_10_str: .string "\"test: 10; cp: cp_cfg_A_tor_lw_address+g\""

test_11_str: .string "\"test: 11; cp: cp_cfg_A_tor_jalr_address\""
test_12_str: .string "\"test: 12; cp: cp_cfg_A_tor_jalr_address-4\""
test_13_str: .string "\"test: 13; cp: cp_cfg_A_tor_jalr_address+4\""
test_14_str: .string "\"test: 14; cp: cp_cfg_A_tor_jalr_address+g-4\""
test_15_str: .string "\"test: 15; cp: cp_cfg_A_tor_jalr_address+g\""

.p2align 12
.p2align (UDB_PMP_GRANULARITY)
TEST_FOR_EXECUTION_0:
    .rept ((1<<(UDB_PMP_GRANULARITY))>>2)
    jr ra
    .endr

.p2align (UDB_PMP_GRANULARITY)
TEST_FOR_EXECUTION:
    .rept ((1<<(UDB_PMP_GRANULARITY))>>2)
    jr ra
    .endr

RETURN_INSTRUCTION:
    nop
    nop
    jr ra                                                        // Get back to the point from where TEST_FOR_EXECUTION was called.


RVTEST_DATA_END

// Signature region for self-checking
RVTEST_SIG_SETUP
