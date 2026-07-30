// --------------------------------------------------------------------------------
// Copyright (C) 2025 Harvey Mudd College & Oklahoma State University, UET Lahore, Habib University
// Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
// SPDX-License-Identifier: Apache-2.0
//
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
// Coverpoints : cp_cfg_A_tor for PMPU is partially covered in this test file.
//
// Test Cases  : Configuring PMP in M mode and then switching to U mode.
//               Checking XWR controls accesses in matching TOR region. With
//               pmpcfg_i.L =1, pmpcfg_i.A = TOR, all legal pmpcfg_i.XWR,
//               default TOR region, address-g in pmpaddr_i-1: making {lw,sw,jalr}
//               address, address-4, address-g, address-g-4.  Observing proper
//               access faults for restricted regions.
// --------------------------------------------------------------------------------

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS:  ['U']
# params:
#   MXLEN: 32
#   NUM_PMP_ENTRIES: '>0'
#   PMP_TOR_SUPPORTED: true
# MARCH: rv32i_zicsr_zifencei
##### END_TEST_CONFIG #####

#define SIGUPD_COUNT 150
#define RVTEST_PRIV_TEST


#include "riscv_arch_test.h"

RVTEST_BEGIN
#define g    (1<<(UDB_PMP_GRANULARITY))


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

#define PMPREGION_LXWR_0000 ((((                        PMP_TOR  )&0xFF) << PMP1_CFG_SHIFT))
#define PMPREGION_LXWR_0001 ((((      PMP_R|            PMP_TOR  )&0xFF) << PMP3_CFG_SHIFT))
#define PMPREGION_LXWR_0011 ((((      PMP_R|PMP_W       |PMP_TOR  )&0xFF) << PMP1_CFG_SHIFT))
#define REGIONSTART            TEST_FOR_EXECUTION        // RAM_BASE_ADDR + PROGRAM_SIZE


    RVTEST_PMP_SET_BACKGROUND x4

//                                            Verification Section
// Test Case: 1 : L -> 0 and No Permissions given to the PMP Region 5

    LA(x6, REGIONSTART)
    li t0, g
    add x6, x6, t0
    srl x6, x6, PMP_SHIFT
    csrw pmpaddr5, x6
    LA(x5, REGIONSTART)
    srl x5, x5, PMP_SHIFT
    csrw pmpaddr4, x5
    LI(x4, PMPREGION_LXWR_0000)
    csrw pmpcfg1, x4

    RVTEST_GOTO_LOWER_MODE    Umode        // SWITCH TO U-mode
    PMP_VERIFICATION_RWX_LEGAL    TEST_FOR_EXECUTION, test_1
    RVTEST_GOTO_MMODE

// Test Case: 2 : L -> 0 and R Permissions given to the PMP Region 3

    LA(x6, REGIONSTART)
    li t0, g
    add x6, x6, t0
    srl x6, x6, PMP_SHIFT
    csrw pmpaddr3, x6
    LA(x5, REGIONSTART)
    srl x5, x5, PMP_SHIFT
    csrw pmpaddr2, x5
    LI(x4, PMPREGION_LXWR_0001)
    csrw pmpcfg0, x4

    RVTEST_GOTO_LOWER_MODE    Umode        // SWITCH TO U-mode
    PMP_VERIFICATION_RWX_LEGAL    TEST_FOR_EXECUTION, test_2
    RVTEST_GOTO_MMODE

// Test Case: 3 : L -> 0 and WR Permissions given to the PMP Region 1

    LA(x6, REGIONSTART)
    li t0, g
    add x6, x6, t0
    srl x6, x6, PMP_SHIFT
    csrw pmpaddr1, x6
    LA(x5, REGIONSTART)
    srl x5, x5, PMP_SHIFT
    csrw pmpaddr0, x5
    LI(x4, PMPREGION_LXWR_0011)
    csrw pmpcfg0, x4

    RVTEST_GOTO_LOWER_MODE    Umode        // SWITCH TO U-mode
    PMP_VERIFICATION_RWX_LEGAL    TEST_FOR_EXECUTION, test_3
    RVTEST_GOTO_MMODE

    j exit                                                        // Verification Complete, exit the test

exit:

RVTEST_CODE_END

RVTEST_DATA_BEGIN
.p2align 4

// Test case strings for reporting
test_1_str:  .string "\"test: 1; cp: cp_cfg_A_tor_jalr_address\""
test_2_str:  .string "\"test: 2; cp: cp_cfg_A_tor_jalr_address-4\""
test_3_str:  .string "\"test: 3; cp: cp_cfg_A_tor_jalr_address+4\""
test_4_str:  .string "\"test: 4; cp: cp_cfg_A_tor_jalr_address+g-4\""
test_5_str:  .string "\"test: 5; cp: cp_cfg_A_tor_jalr_address+g\""

test_6_str:  .string "\"test: 6; cp: cp_cfg_A_tor_sw_address\""
test_7_str:  .string "\"test: 7; cp: cp_cfg_A_tor_sw_address-4\""
test_8_str:  .string "\"test: 8; cp: cp_cfg_A_tor_sw_address+4\""
test_9_str:  .string "\"test: 9; cp: cp_cfg_A_tor_sw_address+g-4\""
test_10_str: .string "\"test: 10; cp: cp_cfg_A_tor_sw_address+g\""

test_11_str: .string "\"test: 11; cp: cp_cfg_A_tor_lw_address\""
test_12_str: .string "\"test: 12; cp: cp_cfg_A_tor_lw_address-4\""
test_13_str: .string "\"test: 13; cp: cp_cfg_A_tor_lw_address+4\""
test_14_str: .string "\"test: 14; cp: cp_cfg_A_tor_lw_address+g-4\""
test_15_str: .string "\"test: 15; cp: cp_cfg_A_tor_lw_address+g\""

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
