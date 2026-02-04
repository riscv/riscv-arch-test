// --------------------------------------------------------------------------------------------------------------------------------
// This test is part of the test plan for the SV-32-based Virtual Memory System, available at:
// https://docs.google.com/spreadsheets/d/1Y8fEu2PnT69w-h8hZc2QQSNKi7DBI0pbXHu2IB8soaQ/edit#gid=0
// Developed by: Muhammad Hammad Bashir, Allen Baum, Umer Shahid
// --------------------------------------------------------------------------------------------------------------------------------
// Copyright (c) 2020. RISC-V International. All rights reserved.
// SPDX-License-Identifier: BSD-3-Clause
// --------------------------------------------------------------------------------------------------------------------------------
// Test Explanation:
// RISC-V Privileged Architecture ISA Manual -- Section 10.3
//
// Note: This test is based on RISC-V Privileged ISA version 1.12, which does not include SVADE and SVADU support.
// Future updates will align with ISA version 1.13.
//
// This test verifies the functionality of mstatus.TVM bit with the satp and sfence.vma
// Test cases are as follows:
// --------------------------------------------------------------------------------------------------------------------------------
//  1. satp accessed in M-Mode with mstatus.TVM set -> Successful
//  2. sfence.vma accessed in M-Mode with mstatus.TVM set -> Successful
//  3. satp accessed in S-Mode with mstatus.TVM set -> 3 Illegal instruction exceptions
//  4. sfence.vma accessed in S-Mode with mstatus.TVM set -> Illegal instruction exception
//
// Total Expected Faults: 4
// --------------------------------------------------------------------------------------------------------------------------------

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: [I, S]
# MARCH: rv32i_zicsr
# CONFIG_DEPENDENT: true
##### END_TEST_CONFIG #####

#define TEST_FILE "vm_mstatus_tvm_test.S"
#define SIGUPD_COUNT 50
#define rvtest_mtrap_routine
#define rvtest_strap_routine
#define SKIP_MEPC
#define SKIP_MTVAL

#include "riscv_arch_test.h"

RVTEST_BEGIN

//---------------------------------------------------------------------------------------------------------------------------------
main:
  // Set mstatus.TVM
  LI(   a0, MSTATUS_TVM)
  CSRS( mstatus, a0)
  RVTEST_SIGUPD_CSR_READ(mstatus, a0, "tvm_mismatch")


//---------------------------------------------------------------------------------------------------------------------------------
// Test case 1: Access satp in M-mode | mstatus.TVM set | Expected: Successful access
//---------------------------------------------------------------------------------------------------------------------------------

  li a0, 1
  RVTEST_SIGUPD_CSR_WRITE(satp, a0, "test_1")

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 2: Access sfence.vma in M-mode | mstatus.TVM set | Expected: Successful access
//---------------------------------------------------------------------------------------------------------------------------------

  SFENCE_VMA

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 3: Access satp in S-mode | mstatus.TVM set | Expected: 3 Illegal instruction exceptions
//---------------------------------------------------------------------------------------------------------------------------------

  RVTEST_GOTO_LOWER_MODE Smode

  li a0, 1
  CSRW(satp, a0)

  li a0, 2
  CSRS(satp, a0)

  li a0, 3
  CSRC(satp, a0)

  RVTEST_GOTO_MMODE

  RVTEST_SIGUPD_CSR_READ(satp, a0, "test_3")

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 4: Access satp in S-mode | mstatus.TVM set | Expected: Illegal instruction exception
//---------------------------------------------------------------------------------------------------------------------------------

  RVTEST_GOTO_LOWER_MODE Smode

  SFENCE_VMA

  RVTEST_GOTO_MMODE


//---------------------------------------------------------------------------------------------------------------------------------
RVTEST_CODE_END
RVTEST_DATA_BEGIN

//---------------------------------------------------------------------------------------------------------------------------------

canary_mismatch: .string "Testcase signature canary mismatch!"
tvm_mismatch: .string "Mismatch while setting mstatus.TVM"
test_1: .string "\"Mismatch in Test Case 1!\""
test_3: .string "\"Mismatch in Test Case 3!\""

RVTEST_DATA_END
RVTEST_SIG_SETUP
