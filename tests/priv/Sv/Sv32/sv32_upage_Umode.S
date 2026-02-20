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
// Note: This test is based on RISC-V Privileged ISA version 1.12, which does not include SVADE and SVADU support.
// Future updates will align with ISA version 1.13.
//
// Test cases are as follows:
// --------------------------------------------------------------------------------------------------------------------------------
// 1. U bit is set for the page at level 1 with RWX Permissions (Read, write, execute page):
//        Then, in U-Mode, the page is accessed --> required: No Fault
// 2. U bit is set for the page at level 1 with X Permissions (Execute only page):
//        Then, in U-Mode, the page is accessed --> required: load-page-fault, store-page-fault
// 3. U bit is set for the page at level 1 with R,X Permissions (Read, Execute page):
//        Then, in U-Mode, the page is accessed --> required: Store-page-fault
// 4. U bit is set for the page at level 1 with R,W Permissions (Read, Store page):
//        Then, in U-Mode, the page is accessed --> required: Fetch-page-fault
// 5. U bit is set for the page at level 1 with R Permissions (Read only page):
//        Then, in U-Mode, the page is accessed --> required: fetch-page-fault, store-page-fault
// 6. U bit is set for the page at level 0 with RWX Permissions (Read, write, execute page):
//        Then, in U-Mode, the page is accessed --> required: No Fault
// 7. U bit is set for the page at level 0 with X Permissions (Execute only page):
//        Then, in U-Mode, the page is accessed --> required: load-page-fault, store-page-fault
// 8. U bit is set for the page at level 0 with R,X Permissions (Read, Execute page):
//        Then, in U-Mode, the page is accessed --> required: Store-page-fault
// 9. U bit is set for the page at level 0 with R,W Permissions (Read, Store page):
//        Then, in U-Mode, the page is accessed --> required: Fetch-page-fault
// 10. U bit is set for the page at level 0 with R Permissions (Read only page):
//        Then, in U-Mode, the page is accessed --> required: fetch-page-fault, store-page-fault
//
// Total Expected Faults :: 12
// --------------------------------------------------------------------------------------------------------------------------------


##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: [I, Sv32]
# MARCH: rv32i_zicsr
# CONFIG_DEPENDENT: true
##### END_TEST_CONFIG #####

#define TEST_FILE "sv32_upage_Umode.S"
#define SIGUPD_COUNT 50
#define rvtest_mtrap_routine
#define rvtest_strap_routine
#define SKIP_MEPC

#include "riscv_arch_test.h"

RVTEST_BEGIN

//---------------------------------------------------------------------------------------------------------------------------------
// Test RWX permissions
.macro VERIFICATION_RWX
  addi a2, a2, 16

  // Test store permission
  sw  a2, 20(a5)
  nop

  // Test load permission
  lw  a4, 20(a5)
  nop

  // Test execute permission
  LI(  x4, 0xACCE)            // Store a value which is to be checked in trap handler
  jalr ra, a5, 0
  nop
.endm

.macro TEST_CASES_RUNNER LOWER_MODE, VA, level, STR_PTR

  .if \level == LEVEL1
    // Adjust offset of VA to point to test region
    LI(  a5, (\VA>>22)<<22)
    LA(  a4, rvtest_data_1)
    slli a4, a4, 10
    srli a4, a4, 10
    add  a5, a5, a4
  .else
    LI(  a5, \VA)
  .endif

  RVTEST_GOTO_LOWER_MODE \LOWER_MODE

  VERIFICATION_RWX

  RVTEST_GOTO_MMODE

  // Signature Update
  RVTEST_SIGUPD(x2, x5, x4, a2, \STR_PTR)
  RVTEST_SIGUPD(x2, x5, x4, a4, \STR_PTR)
.endm


main:
  li a2, 0x800                // Test signature initialization

//---------------------------------------------------------------------------------------------------------------------------------
//                                   Virtual addresses definition for code and test regions
//---------------------------------------------------------------------------------------------------------------------------------

  // Virtual Address of Test section (rvtest_data_1)
  .set va_data,               0x90407000

  // Virtual Address for code region
  .set va_rvtest_code_begin,  0x30000000


  // PTE setup for Code Region
  SUPERPAGE_PTE_SETUP_SV32(rvtest_code_begin, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_R | PTE_V), va_rvtest_code_begin, LEVEL1)
  sfence.vma

  // Save area setup for code region
  csrr a0, mscratch
  SAVE_AREA_SETUP(va_rvtest_code_begin, rvtest_code_begin, code)

//---------------------------------------------------------------------------------------------------------------------------------
//                                               Test Cases Start from here
//---------------------------------------------------------------------------------------------------------------------------------

  SATP_SETUP_SV32                                                        // Set SATP for virtualization
  sfence.vma                                                             // Flush TLB

//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------
//                                                    TESTS AT LEVEL 1
//---------------------------------------------------------------------------------------------------------------------------------
//                    4MB PAGE    Region 1 under test at level 1 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 1: U bit set | Test in U-Mode | RWX bit set | expected = No RWX fault
  SUPERPAGE_PTE_SETUP_SV32(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL1, "test_1"

//---------------------------------------------------------------------------------------------------------------------------------
//                    4MB PAGE    Region 2 under test at level 1 -- X permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 2: U bit set | Test in U-Mode | X bit set | expected = Load, Store Fault
  SUPERPAGE_PTE_SETUP_SV32(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_V), va_data, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL1, "test_2"

//---------------------------------------------------------------------------------------------------------------------------------
//                    4MB PAGE    Region 3 under test at level 1 -- RX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 3: U bit set | Test in U-Mode | RX bit set | expected = Store Fault
  SUPERPAGE_PTE_SETUP_SV32(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_R | PTE_X | PTE_V), va_data, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL1, "test_3"

//---------------------------------------------------------------------------------------------------------------------------------
//                    4MB PAGE    Region 4 under test at level 1 -- RW permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 4: U bit set | Test in U-Mode |  RW bit set | expected = fetch-page-fault
  SUPERPAGE_PTE_SETUP_SV32(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_R | PTE_W | PTE_V), va_data, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL1, "test_4"

//---------------------------------------------------------------------------------------------------------------------------------
//                    4MB PAGE    Region 5 under test at level 1 -- R permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 5: U bit set | Test in U-Mode |  X bit set | expected = fetch-page-fault, store-page-fault
  SUPERPAGE_PTE_SETUP_SV32(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_R | PTE_V), va_data, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL1, "test_5"


//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------
//                                                    TESTS AT LEVEL 0
//---------------------------------------------------------------------------------------------------------------------------------
//                    4KB PAGE    Region 1 under test at level 0 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 6: U bit set | Test in U-Mode | RWX bit set | expected = No RWX fault
  PTE_SETUP_SV32(rvtest_slvl0_pg_tbl, (PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV32(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL0, "test_6"

//---------------------------------------------------------------------------------------------------------------------------------
//                    4KB PAGE    Region 2 under test at level 0 -- X permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 7: U bit set | Test in U-Mode | X bit set | expected = Load, Store Fault
  PTE_SETUP_SV32(rvtest_slvl0_pg_tbl, (PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV32(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL0, "test_7"

//---------------------------------------------------------------------------------------------------------------------------------
//                    4KB PAGE    Region 3 under test at level 0 -- RX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 8: U bit set | Test in U-Mode | RX bit set | expected = Store Fault
  PTE_SETUP_SV32(rvtest_slvl0_pg_tbl, (PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV32(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_R | PTE_X | PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL0, "test_8"

//---------------------------------------------------------------------------------------------------------------------------------
//                    4kB PAGE    Region 4 under test at level 0 -- RW permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 9: U bit set | Test in U-Mode |  R bit set | expected = Store-page-fault, fetch-page-fault
  PTE_SETUP_SV32(rvtest_slvl0_pg_tbl, (PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV32(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_R | PTE_W | PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL0, "test_9"

//---------------------------------------------------------------------------------------------------------------------------------
//                    4KB PAGE    Region 5 under test at level 0 -- W permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 10: U bit set | Test in U-Mode |  X bit set | expected = load-page-fault, store-page-fault
  PTE_SETUP_SV32(rvtest_slvl0_pg_tbl, (PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV32(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_R | PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL0, "test_10"


//---------------------------------------------------------------------------------------------------------------------------------
RVTEST_CODE_END
RVTEST_DATA_BEGIN

//---------------------------------------------------------------------------------------------------------------------------------
//                                            PHYSICAL ADDRESS REGION FOR TESTING
//---------------------------------------------------------------------------------------------------------------------------------
// Physical Address region under testing for LEVEL 0 and 1
.align 12
rvtest_data_1:
  nop
  addi ra, ra, 4
  jr ra
  nop
  .word 0xbeefcaf1          // Random word
  .word 0xbeefcaf2          // Random word
  nop
  jr ra

//---------------------------------------------------------------------------------------------------------------------------------

// Page Table
.align 12
rvtest_slvl0_pg_tbl:
    .skip(4096)

canary_mismatch: .string "Testcase signature canary mismatch!"
test_1: .string "\"Mismatch in Test Case 1!\""
test_2: .string "\"Mismatch in Test Case 2!\""
test_3: .string "\"Mismatch in Test Case 3!\""
test_4: .string "\"Mismatch in Test Case 4!\""
test_5: .string "\"Mismatch in Test Case 5!\""
test_6: .string "\"Mismatch in Test Case 6!\""
test_7: .string "\"Mismatch in Test Case 7!\""
test_8: .string "\"Mismatch in Test Case 8!\""
test_9: .string "\"Mismatch in Test Case 9!\""
test_10: .string "\"Mismatch in Test Case 10!\""

RVTEST_DATA_END
RVTEST_SIG_SETUP
