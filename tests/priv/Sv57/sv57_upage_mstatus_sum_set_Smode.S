// --------------------------------------------------------------------------------------------------------------------------------
// Developed by: Umer Shahid & Muhammad Zain
// --------------------------------------------------------------------------------------------------------------------------------
// Test cases are as follows:
// --------------------------------------------------------------------------------------------------------------------------------
// 1. mstatus.SUM set and PTE.U set for the page at level 4 with RWX Permissions (Read, write, execute page):
//        Then, in S-Mode, the page is accessed --> required: Fetch-page-fault
// 2. mstatus.SUM set and PTE.U set for the page at level 4 with X Permission (Execute only page):
//        Then, in S-Mode, the page is accessed --> required: Load-page-fault, Store-page-fault, Fetch-page-fault
// 3. mstatus.SUM set and PTE.U set for the page at level 4 with R,X Permissions (Read, Execute page):
//        Then, in S-Mode, the page is accessed --> required: Store-page-fault, Fetch-page-fault
// 4. mstatus.SUM set and PTE.U set for the page at level 4 with R,W Permissions (Read, Store page):
//        Then, in S-Mode, the page is accessed --> required: Fetch-page-fault
// 5. mstatus.SUM set and PTE.U set for the page at level 4 with R Permission (execute page):
//        Then, in S-Mode, the page is accessed --> required: Store-page-fault, Fetch-page-fault
// 6. mstatus.SUM set and PTE.U set for the page at level 3 with RWX Permissions (Read, write, execute page):
//        Then, in S-Mode, the page is accessed --> required: Fetch-page-fault
// 7. mstatus.SUM set and PTE.U set for the page at level 3 with X Permission (Execute only page):
//        Then, in S-Mode, the page is accessed --> required: Load-page-fault, Store-page-fault, Fetch-page-fault
// 8. mstatus.SUM set and PTE.U set for the page at level 3 with R,X Permissions (Read, Execute page):
//        Then, in S-Mode, the page is accessed --> required: Store-page-fault, Fetch-page-fault
// 9. mstatus.SUM set and PTE.U set for the page at level 3 with R,W Permissions (Read, Store page):
//        Then, in S-Mode, the page is accessed --> required: Fetch-page-fault
// 10. mstatus.SUM set and PTE.U set for the page at level 3 with R Permission (execute page):
//        Then, in S-Mode, the page is accessed --> required: Store-page-fault, Fetch-page-fault
// 11. mstatus.SUM set and PTE.U set for the page at level 2 with RWX Permissions (Read, write, execute page):
//        Then, in S-Mode, the page is accessed --> required: Fetch-page-fault
// 12. mstatus.SUM set and PTE.U set for the page at level 2 with X Permission (Execute only page):
//        Then, in S-Mode, the page is accessed --> required: Load-page-fault, Store-page-fault, Fetch-page-fault
// 13. mstatus.SUM set and PTE.U set for the page at level 2 with R,X Permissions (Read, Execute page):
//        Then, in S-Mode, the page is accessed --> required: Store-page-fault, Fetch-page-fault
// 14. mstatus.SUM set and PTE.U set for the page at level 2 with R,W Permissions (Read, Store page):
//        Then, in S-Mode, the page is accessed --> required: Fetch-page-fault
// 15. mstatus.SUM set and PTE.U set for the page at level 2 with R Permission (execute page):
//        Then, in S-Mode, the page is accessed --> required: Store-page-fault, Fetch-page-fault
// 16. mstatus.SUM set and PTE.U set for the page at level 1 with RWX Permissions (Read, write, execute page):
//        Then, in S-Mode, the page is accessed --> required: Fetch-page-fault
// 17. mstatus.SUM set and PTE.U set for the page at level 1 with X Permission (Execute only page):
//        Then, in S-Mode, the page is accessed --> required: Load-page-fault, Store-page-fault, Fetch-page-fault
// 18. mstatus.SUM set and PTE.U set for the page at level 1 with R,X Permissions (Read, Execute page):
//        Then, in S-Mode, the page is accessed --> required: Store-page-fault, Fetch-page-fault
// 19. mstatus.SUM set and PTE.U set for the page at level 1 with R,W Permissions (Read, Store page):
//        Then, in S-Mode, the page is accessed --> required: Fetch-page-fault
// 20. mstatus.SUM set and PTE.U set for the page at level 1 with R Permission (execute page):
//        Then, in S-Mode, the page is accessed --> required: Store-page-fault, Fetch-page-fault
// 21. mstatus.SUM set and PTE.U set for the page at level 0 with RWX Permissions (Read, write, execute page):
//        Then, in S-Mode, the page is accessed --> required: Fetch-page-fault
// 22. mstatus.SUM set and PTE.U set for the page at level 0 with X Permission (Execute only page):
//        Then, in S-Mode, the page is accessed --> required: Load-page-fault, Store-page-fault, Fetch-page-fault
// 23. mstatus.SUM set and PTE.U set for the page at level 0 with R,X Permissions (Read, Execute page):
//        Then, in S-Mode, the page is accessed --> required: Store-page-fault, Fetch-page-fault
// 24. mstatus.SUM set and PTE.U set for the page at level 0 with R,W Permissions (Read, Store page):
//        Then, in S-Mode, the page is accessed --> required: Fetch-page-fault
// 25. mstatus.SUM set and PTE.U set for the page at level 0 with R Permission (execute page):
//        Then, in S-Mode, the page is accessed --> required: Store-page-fault, Fetch-page-fault
//
// Total Expected Faults :: 45
// --------------------------------------------------------------------------------------------------------------------------------

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: [I, Sv57]
# MARCH: rv64i_zicsr
# CONFIG_DEPENDENT: true
##### END_TEST_CONFIG #####

#define TEST_FILE "sv57_upage_mstatus_sum_set_Smode.S"
#define SIGUPD_COUNT 50
#define rvtest_mtrap_routine
#define rvtest_strap_routine
#define SKIP_MEPC
#define SKIP_MTVAL

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

  // Set mstatus.SUM
  LI(t0, MSTATUS_SUM)
  CSRS(mstatus, t0)

  // Adjust offset of VA to point to test region
  .set VA_SHIFT, (\level*9)+12
  LI(a5, (\VA>>VA_SHIFT)<<VA_SHIFT)
  LA(a4, rvtest_data_1)
  slli a4, a4, 64-VA_SHIFT
  srli a4, a4, 64-VA_SHIFT
  add  a5, a5, a4             // Virtual Address

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
  .set va_data,               0x07028500403000

  // Virtual Address for code region
  .set va_rvtest_code_begin,  0x03000080000000


  // PTE setup for Code Region
  SUPERPAGE_PTE_SETUP_SV57(rvtest_code_begin, (PTE_D | PTE_A | PTE_X | PTE_R | PTE_V), va_rvtest_code_begin, LEVEL4)
  sfence.vma

  // Save area setup for code region
  csrr a0, mscratch
  SAVE_AREA_SETUP(va_rvtest_code_begin, rvtest_code_begin, code)

//---------------------------------------------------------------------------------------------------------------------------------
//                                               Test Cases Start from here
//---------------------------------------------------------------------------------------------------------------------------------

  SATP_SETUP_RV64(sv57)                                                  // Set SATP for virtualization
  sfence.vma                                                             // Flush TLB


//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------
//                                                  TESTS AT LEVEL 4
//---------------------------------------------------------------------------------------------------------------------------------
//                  256TB PAGE  Region 1 under test at level 4 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 1: U bit set | Test in S-Mode | RWX bit set | expected = fetch-page-fault
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL4)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL4, "test_1"

//---------------------------------------------------------------------------------------------------------------------------------
//                  256TB PAGE  Region 1 under test at level 4 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 2: U bit set | Test in S-Mode | X bit set | expected = RWX Fault
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_V), va_data, LEVEL4)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL4, "test_2"

//---------------------------------------------------------------------------------------------------------------------------------
//                  256TB PAGE  Region 1 under test at level 4 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 3: U bit set | Test in S-Mode | RX bit set | expected = store-page-fault, fetch-page-fault
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_R | PTE_X | PTE_V), va_data, LEVEL4)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL4, "test_3"

//---------------------------------------------------------------------------------------------------------------------------------
//                  256TB PAGE  Region 1 under test at level 4 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 4: U bit set | Test in S-Mode |  RW bit set | expected = fetch-page-fault
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_R | PTE_W | PTE_V), va_data, LEVEL4)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL4, "test_4"

//---------------------------------------------------------------------------------------------------------------------------------
//                  256TB PAGE  Region 1 under test at level 4 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 5: U bit set | Test in S-Mode | R bit set | expected = fetch-page-fault, store-page-fault
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_R | PTE_V), va_data, LEVEL4)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL4, "test_5"


//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------
//                                                  TESTS AT LEVEL 3
//---------------------------------------------------------------------------------------------------------------------------------
//                  512GB PAGE  Region 1 under test at level 3 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 6: U bit set | Test in S-Mode | RWX bit set | expected = fetch-page-fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL3)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL3, "test_6"

//---------------------------------------------------------------------------------------------------------------------------------
//                  512GB PAGE  Region 1 under test at level 3 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 7: U bit set | Test in S-Mode | X bit set | expected = RWX Fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_V), va_data, LEVEL3)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL3, "test_7"

//---------------------------------------------------------------------------------------------------------------------------------
//                  512GB PAGE  Region 1 under test at level 3 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 8: U bit set | Test in S-Mode | RX bit set | expected = store-page-fault, fetch-page-fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_R | PTE_X | PTE_V), va_data, LEVEL3)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL3, "test_8"

//---------------------------------------------------------------------------------------------------------------------------------
//                  512GB PAGE  Region 1 under test at level 3 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 9: U bit set | Test in S-Mode |  RW bit set | expected = fetch-page-fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_R | PTE_W | PTE_V), va_data, LEVEL3)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL3, "test_9"

//---------------------------------------------------------------------------------------------------------------------------------
//                  512GB PAGE  Region 1 under test at level 3 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 10: U bit set | Test in S-Mode | R bit set | expected = fetch-page-fault, store-page-fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_R | PTE_V), va_data, LEVEL3)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL3, "test_10"


//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------
//                                                  TESTS AT LEVEL 2
//---------------------------------------------------------------------------------------------------------------------------------
//                  1GB PAGE    Region 1 under test at level 2 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 11: U bit set | Test in S-Mode | RWX bit set | expected = fetch-page-fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL2)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL2, "test_11"

//---------------------------------------------------------------------------------------------------------------------------------
//                  1GB PAGE    Region 1 under test at level 2 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 12: U bit set | Test in S-Mode | X bit set | expected = RWX Fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_V), va_data, LEVEL2)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL2, "test_12"

//---------------------------------------------------------------------------------------------------------------------------------
//                  1GB PAGE    Region 1 under test at level 2 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 13: U bit set | Test in S-Mode | RX bit set | expected = store-page-fault, fetch-page-fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_R | PTE_X | PTE_V), va_data, LEVEL2)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL2, "test_13"

//---------------------------------------------------------------------------------------------------------------------------------
//                  1GB PAGE    Region 1 under test at level 2 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 14: U bit set | Test in S-Mode |  RW bit set | expected = fetch-page-fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_R | PTE_W | PTE_V), va_data, LEVEL2)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL2, "test_14"

//---------------------------------------------------------------------------------------------------------------------------------
//                  1GB PAGE    Region 1 under test at level 2 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 15: U bit set | Test in S-Mode | R bit set | expected = fetch-page-fault, store-page-fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_R | PTE_V), va_data, LEVEL2)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL2, "test_15"


//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------
//                                                  TESTS AT LEVEL 1
//---------------------------------------------------------------------------------------------------------------------------------
//                  2MB PAGE    Region 1 under test at level 1 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 16: U bit set | Test in S-Mode | RWX bit set | expected = fetch-page-fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV57(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL1, "test_16"

//---------------------------------------------------------------------------------------------------------------------------------
//                  2MB PAGE    Region 1 under test at level 1 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 17: U bit set | Test in S-Mode | X bit set | expected = RWX Fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV57(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_V), va_data, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL1, "test_17"

//---------------------------------------------------------------------------------------------------------------------------------
//                  2MB PAGE    Region 1 under test at level 1 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 18: U bit set | Test in S-Mode | RX bit set | expected = store-page-fault, fetch-page-fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV57(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_R | PTE_X | PTE_V), va_data, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL1, "test_18"

//---------------------------------------------------------------------------------------------------------------------------------
//                  2MB PAGE    Region 1 under test at level 1 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 19: U bit set | Test in S-Mode |  RW bit set | expected = fetch-page-fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV57(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_R | PTE_W | PTE_V), va_data, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL1, "test_19"

//---------------------------------------------------------------------------------------------------------------------------------
//                  2MB PAGE    Region 1 under test at level 1 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 20: U bit set | Test in S-Mode | R bit set | expected = fetch-page-fault, store-page-fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV57(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_R | PTE_V), va_data, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL1, "test_20"


//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------
//                                                  TESTS AT LEVEL 0
//---------------------------------------------------------------------------------------------------------------------------------
//                  4KB PAGE    Region 1 under test at level 0 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 21: U bit set | Test in S-Mode | RWX bit set | expected = fetch-page-fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV57(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  PTE_SETUP_SV57(rvtest_slvl0_pg_tbl, (PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL0, "test_21"

//---------------------------------------------------------------------------------------------------------------------------------
//                  4KB PAGE    Region 1 under test at level 0 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 22: U bit set | Test in S-Mode | X bit set | expected = RWX Fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV57(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  PTE_SETUP_SV57(rvtest_slvl0_pg_tbl, (PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL0, "test_22"

//---------------------------------------------------------------------------------------------------------------------------------
//                  4KB PAGE    Region 1 under test at level 0 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 23: U bit set | Test in S-Mode | RX bit set | expected = store-page-fault, fetch-page-fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV57(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  PTE_SETUP_SV57(rvtest_slvl0_pg_tbl, (PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_R | PTE_X | PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL0, "test_23"

//---------------------------------------------------------------------------------------------------------------------------------
//                  4KB PAGE    Region 1 under test at level 0 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 24: U bit set | Test in S-Mode | RW bit set | expected = fetch-page-fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV57(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  PTE_SETUP_SV57(rvtest_slvl0_pg_tbl, (PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_R | PTE_W | PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL0, "test_24"

//---------------------------------------------------------------------------------------------------------------------------------
//                  4KB PAGE    Region 1 under test at level 0 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 25: U bit set | Test in S-Mode | R bit set | expected = load-page-fault, store-page-fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV57(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  PTE_SETUP_SV57(rvtest_slvl0_pg_tbl, (PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_R | PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL0, "test_25"


//---------------------------------------------------------------------------------------------------------------------------------
RVTEST_CODE_END
RVTEST_DATA_BEGIN

//---------------------------------------------------------------------------------------------------------------------------------
//                                            PHYSICAL ADDRESS REGION FOR TESTING
//---------------------------------------------------------------------------------------------------------------------------------
// Physical Address region under testing for LEVEL 0, 1, 2, 3 and 4
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

// Page Tables
.align 12
rvtest_slvl0_pg_tbl:
    .skip(4096)
rvtest_slvl1_pg_tbl:
    .skip(4096)
rvtest_slvl2_pg_tbl:
    .skip(4096)
rvtest_slvl3_pg_tbl:
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
test_11: .string "\"Mismatch in Test Case 11!\""
test_12: .string "\"Mismatch in Test Case 12!\""
test_13: .string "\"Mismatch in Test Case 13!\""
test_14: .string "\"Mismatch in Test Case 14!\""
test_15: .string "\"Mismatch in Test Case 15!\""
test_16: .string "\"Mismatch in Test Case 16!\""
test_17: .string "\"Mismatch in Test Case 17!\""
test_18: .string "\"Mismatch in Test Case 18!\""
test_19: .string "\"Mismatch in Test Case 19!\""
test_20: .string "\"Mismatch in Test Case 20!\""
test_21: .string "\"Mismatch in Test Case 21!\""
test_22: .string "\"Mismatch in Test Case 22!\""
test_23: .string "\"Mismatch in Test Case 23!\""
test_24: .string "\"Mismatch in Test Case 24!\""
test_25: .string "\"Mismatch in Test Case 25!\""

RVTEST_DATA_END
RVTEST_SIG_SETUP
