// ----------------------------------------------------------------------------------------------------------------------
// This test is part of the test plan for the SV-32-based Virtual Memory System, available at:
// https://docs.google.com/spreadsheets/d/1Y8fEu2PnT69w-h8hZc2QQSNKi7DBI0pbXHu2IB8soaQ/edit#gid=0
// Developed by: Muhammad Hammad Bashir, Allen Baum, Umer Shahid
// ----------------------------------------------------------------------------------------------------------------------
// Copyright (c) 2020. RISC-V International. All rights reserved.
// SPDX-License-Identifier: BSD-3-Clause
// ----------------------------------------------------------------------------------------------------------------------
// Test Explanation:
// RISC-V Privileged Architecture ISA Manual -- Section 10.3
//
// Note: This test is based on RISC-V Privileged ISA version 1.12, which does not include SVADE and SVADU support.
// Future updates will align with ISA version 1.13.
//
// This test verifies the functionality of mstatus.TVM bit with the satp and sfence.vma
// Test cases are as follows:
// ----------------------------------------------------------------------------------------------------------------------
//  1. satp and sfence.vma accessed in M Mode with mstatus.tvm bit set -> Successful
//  2. satp and sfence.vma accessed in S Mode with mstatus.tvm bit set -> illegal instruction exception
//
// Total Expected Faults: 4
// ----------------------------------------------------------------------------------------------------------------------

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: [I, Sv32]
# MARCH: rv32i_zicsr
# CONFIG_DEPENDENT: true
##### END_TEST_CONFIG #####

//TODO: instead of using two different tests, use a single test for hart/software update.

// Define the name of this test file for reporting and the size of the signature region
#define TEST_FILE "mstatus_tvm_test.S"
#define SIGUPD_COUNT 50

// Enable trap handler
#define rvtest_mtrap_routine
#define rvtest_strap_routine

// Include framework macros
#include "riscv_arch_test.h"

// Set up test environment and declare main entry point
RVTEST_BEGIN

  CSRW(satp, zero)                                           // write satp with all zeros (bare mode)

  #set the mstatus with the TVM bit
check_tvm:
  LI(a0, MSTATUS_TVM)
  RVTEST_SIGUPD_CSR_WRITE(mstatus, a0, "test_1")

// ------------------------------------------------------------------------------------------------------------
//                     satp access in M Mode using csrrw, csrrc, csrrs
// ------------------------------------------------------------------------------------------------------------
check_satp_write:
  li a0, 1                                //initial value for a0 = 1
  RVTEST_SIGUPD_CSR_WRITE(satp, a0, "test_2")


  #successful access
  SFENCE_VMA

// ------------------------------------------------------------------------------------------------------------
//                     satp access in S Mode using csrrw, csrrc, csrrs
// ------------------------------------------------------------------------------------------------------------

  RVTEST_GOTO_LOWER_MODE Smode

  li a0, 1                                //initial value for a0 = 1
  CSRW(satp, a0)                          // write satp with some value

  li a0, 1
  CSRC(satp, a0)

  li a0, 1
  CSRC(satp, a0)

  SFENCE_VMA

  RVTEST_GOTO_MMODE                                                // Switching back to M mode

//---------------------------------------------------------------------------------------------------------------------------------
RVTEST_CODE_END

RVTEST_DATA_BEGIN

canary_mismatch: .string "Testcase signature canary mismatch!"
test_1: .string "\"test: 1; cp: check mstatus.tvm\""
test_2: .string "\"test: 2; cp: check satp\""

//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------

.align 12                       //complete the 4KB permission memory range
rvtest_slvl1_pg_tbl:
    RVTEST_PTE_IDENT_MAP(0,1,PTE_V | PTE_A | PTE_D | PTE_G)

// End of test data section and model specific data
RVTEST_DATA_END

// Signature region for self-checking
RVTEST_SIG_SETUP
