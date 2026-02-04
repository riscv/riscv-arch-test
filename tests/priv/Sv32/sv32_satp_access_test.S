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
// This test verifies the functionality of satp register in M, S and U Mode using csrrw, csrrs, csrrc.
// Test cases are as follows:
// --------------------------------------------------------------------------------------------------------------------------------
//  1. Accessing satp in M and S mode -> Successful
//  2. Accessing satp in U mode -> 3 Illegal Instruction exception
//  3. Set satp.MODE to Sv32 and Bare -> Successful
//  4. All zeros, ones and walking ones on the PPN field of satp when satp.MODE=Sv32 -> Successful
//  5. All zeros, ones and walking ones on the ASID field of satp when satp.MODE=Sv32 -> Successful
//  6. All zeros and random value to satp[59:0] when satp.MODE=Bare -> Successful
//
// Total Expected Faults: 3
// --------------------------------------------------------------------------------------------------------------------------------

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: [I, Sv32]
# MARCH: rv32i_zicsr
# CONFIG_DEPENDENT: true
##### END_TEST_CONFIG #####

#define TEST_FILE "sv32_satp_access_test.S"
#define SIGUPD_COUNT 50
#define rvtest_mtrap_routine
#define rvtest_strap_routine
#define SKIP_MEPC
#define SKIP_MTVAL

#include "riscv_arch_test.h"

RVTEST_BEGIN


main:
//---------------------------------------------------------------------------------------------------------------------------------
// Test case 1: Access satp in M-mode using csrrw, csrrs, csrrc | Expected: Successful access
//---------------------------------------------------------------------------------------------------------------------------------

  li a0, 1
  CSRW(satp, a0)
  RVTEST_SIGUPD_CSR_READ(satp, a4, "test_1_csrw")

  li a0, 2
  CSRS(satp, a0)
  RVTEST_SIGUPD_CSR_READ(satp, a4, "test_1_csrs")

  li a0, 1
  CSRC(satp, t0)
  RVTEST_SIGUPD_CSR_READ(satp, a4, "test_1_csrc")


//---------------------------------------------------------------------------------------------------------------------------------
// Test case 2: Access satp in S-mode using csrrw, csrrs, csrrc | Expected: Successful access
//---------------------------------------------------------------------------------------------------------------------------------

  RVTEST_GOTO_LOWER_MODE Smode

  li a0, 4
  CSRW(satp, a0)
  RVTEST_SIGUPD_CSR_READ(satp, a4, "test_2_csrw")

  li a0, 8
  CSRS(satp, a0)
  RVTEST_SIGUPD_CSR_READ(satp, a4, "test_2_csrs")

  li a0, 4
  CSRC(satp, t0)
  RVTEST_SIGUPD_CSR_READ(satp, a4, "test_2_csrc")

  RVTEST_GOTO_MMODE


//---------------------------------------------------------------------------------------------------------------------------------
// Test case 3: Access satp in U-mode using csrrw, csrrs, csrrc | Expected: 3 Illegal instruction exceptions
//---------------------------------------------------------------------------------------------------------------------------------

  RVTEST_GOTO_LOWER_MODE Umode

  li a0, 16
  CSRW(satp, a0)

  li a0, 32
  CSRS(satp, a0)

  li a0, 16
  CSRC(satp, t0)

  RVTEST_GOTO_MMODE

  RVTEST_SIGUPD_CSR_READ(satp, a4, "test_3")

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 4: Set satp.MODE to Sv32 and Bare | Expected: Successful
//---------------------------------------------------------------------------------------------`------------------------------------

  LI(a0, SATP_MODE_SV32<<31)      // satp.MODE = 1'b1 (Sv32)
  CSRW(satp, a0)
  RVTEST_SIGUPD_CSR_READ(satp, a4, "test_4_Sv32")

  li a0, 0                        // satp.MODE = 1'b0 (Bare)
  CSRW(satp, a0)
  RVTEST_SIGUPD_CSR_READ(satp, a4, "test_4_bare")


//---------------------------------------------------------------------------------------------------------------------------------
// Test case 5: Zeros, ones and walking ones on satp.PPN | Expected: Successful
//---------------------------------------------------------------------------------------------------------------------------------

  LI(a1, SATP_MODE_SV32<<31)      // satp.MODE = Sv32

  // satp.PPN = All zeros
  mv   a0, a1
  CSRW(satp, a0)
  RVTEST_SIGUPD_CSR_READ(satp, a4, "test_5_zeros")

  // satp.PPN = All ones
  LI(  a0, 0x3FFFFF)
  or   a0, a1, a0
  CSRW(satp, a0)
  RVTEST_SIGUPD_CSR_READ(satp, a4, "test_5_ones")

  // satp.PPN = Walking Ones
  li a2, 1
  .rept(22)
    or   a0, a1, a2
    CSRW(satp, a0)
    RVTEST_SIGUPD_CSR_READ(satp, a4, "test_5_walk")
    slli  a2, a2, 1
  .endr


//---------------------------------------------------------------------------------------------------------------------------------
// Test case 6: Zeros, ones and walking ones on satp.ASID | Expected: Successful
//---------------------------------------------------------------------------------------------------------------------------------

  LI(a1, SATP_MODE_SV32<<31)      // satp.MODE = Sv32

  // satp.ASID = All zeros
  mv   a0, a1
  CSRW(satp, a0)
  RVTEST_SIGUPD_CSR_READ(satp, a4, "test_6_zeros")

  // satp.ASID = All ones
  LI(  a0, 0x1FF)
  slli a0, a0, 22
  or   a0, a1, a0
  CSRW(satp, a0)
  RVTEST_SIGUPD_CSR_READ(satp, a4, "test_6_ones")

  // satp.ASID = Walking Ones
  li   a2, 1
  slli a2, a2, 22
  .rept(9)
    or   a0, a1, a2
    CSRW(satp, a0)
    RVTEST_SIGUPD_CSR_READ(satp, a4, "test_6_walk")
    slli  a2, a2, 1
  .endr


//---------------------------------------------------------------------------------------------------------------------------------
// Test case 7: Zeros and random value in satp[30:0] when satp.MODE = Bare | Expected: Successful
//---------------------------------------------------------------------------------------------------------------------------------

  li a0, 0                        // satp.MODE = Bare
  CSRW(satp, a0)
  RVTEST_SIGUPD_CSR_READ(satp, a4, "test_7_zeros")

  LI(a0, 0x789BCDEF)              // satp[30:0]=Random value, satp.MODE=Bare
  CSRW(satp, a0)
  RVTEST_SIGUPD_CSR_READ(satp, a4, "test_7_random")


//---------------------------------------------------------------------------------------------------------------------------------
RVTEST_CODE_END
RVTEST_DATA_BEGIN


canary_mismatch: .string "Testcase signature canary mismatch!"
test_1_csrw:   .string "\"Mismatch on csrw in Test Case 1!\""
test_1_csrs:   .string "\"Mismatch on csrs in Test Case 1!\""
test_1_csrc:   .string "\"Mismatch on csrc in Test Case 1!\""
test_2_csrw:   .string "\"Mismatch on csrw in Test Case 2!\""
test_2_csrs:   .string "\"Mismatch on csrs in Test Case 2!\""
test_2_csrc:   .string "\"Mismatch on csrc in Test Case 2!\""
test_3:        .string "\"Mismatch in Test Case 3!\""
test_4_Sv32:   .string "\"Mismatch on setting satp.MODE=Sv32 in Test Case 4!\""
test_4_bare:   .string "\"Mismatch on setting satp.MODE=Bare in Test Case 4!\""
test_5_zeros:  .string "\"Mismatch on setting satp.PPN=Zeros in Test Case 5!\""
test_5_ones:   .string "\"Mismatch on setting satp.PPN=Ones in Test Case 5!\""
test_5_walk:   .string "\"Mismatch on walking ones in satp.PPN in Test Case 5!\""
test_6_zeros:  .string "\"Mismatch on setting satp.ASID=Zeros in Test Case 6!\""
test_6_ones:   .string "\"Mismatch on setting satp.ASID=Ones in Test Case 6!\""
test_6_walk:   .string "\"Mismatch on walking ones in satp.ASID in Test Case 6!\""
test_7_zeros:  .string "\"Mismatch on setting satp[59:0]=Zeros when satp.MODE=Bare in Test Case 7!\""
test_7_random: .string "\"Mismatch on setting satp[59:0]=Random value when satp.MODE=Bare in Test Case 7!\""

RVTEST_DATA_END
RVTEST_SIG_SETUP
