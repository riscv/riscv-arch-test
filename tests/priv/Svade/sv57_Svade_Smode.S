// --------------------------------------------------------------------------------------------------------------------------------
// Developed by: Umer Shahid & Muhammad Zain
// --------------------------------------------------------------------------------------------------------------------------------
// Test cases are as follows:
// --------------------------------------------------------------------------------------------------------------------------------
// 1. PTE.D unset, PTE.A set at level 4, RWX permissions (read, write, execute page):
//        Then, access the page in S-Mode. Expected: Store-page-fault
// 2. PTE.D set, PTE.A set at level 4, RWX permissions (read, write, execute page):
//        Then, access the page in S-Mode. Expected: No fault should occur.
// 3. PTE.D set, PTE.A unset at level 4, RWX permissions (read, write, execute page):
//        Then access the page in S-Mode. Expected: Store, Load & Fetch page fault
// 4. PTE.D unset, PTE.A unset at level 4, RWX permissions (read, write, execute page):
//        Then access the page in S-Mode. Expected: Store, Load & Fetch page fault
// 5. PTE.D unset, PTE.A set at level 3, RWX permissions (read, write, execute page):
//        Then, access the page in S-Mode. Expected: Store-page-fault
// 6. PTE.D set, PTE.A set at level 3, RWX permissions (read, write, execute page):
//        Then, access the page in S-Mode. Expected: No fault should occur.
// 7. PTE.D set, PTE.A unset at level 3, RWX permissions (read, write, execute page):
//        Then access the page in S-Mode. Expected: Store, Load & Fetch page fault
// 8. PTE.D unset, PTE.A unset at level 3, RWX permissions (read, write, execute page):
//        Then access the page in S-Mode. Expected: Store, Load & Fetch page fault
// 9. PTE.D unset, PTE.A set at level 2, RWX permissions (read, write, execute page):
//        Then, access the page in S-Mode. Expected: Store-page-fault
// 10. PTE.D set, PTE.A set at level 2, RWX permissions (read, write, execute page):
//        Then, access the page in S-Mode. Expected: No fault should occur.
// 11. PTE.D set, PTE.A unset at level 2, RWX permissions (read, write, execute page):
//        Then access the page in S-Mode. Expected: Store, Load & Fetch page fault
// 12. PTE.D unset, PTE.A unset at level 2, RWX permissions (read, write, execute page):
//        Then access the page in S-Mode. Expected: Store, Load & Fetch page fault
// 13. PTE.D unset, PTE.A set at level 1, RWX permissions (read, write, execute page):
//        Then, access the page in S-Mode. Expected: Store-page-fault
// 14. PTE.D set, PTE.A set at level 1, RWX permissions (read, write, execute page):
//        Then, access the page in S-Mode. Expected: No fault should occur.
// 15. PTE.D set, PTE.A unset at level 1, RWX permissions (read, write, execute page):
//        Then access the page in S-Mode. Expected: Store, Load & Fetch page fault
// 16. PTE.D unset, PTE.A unset at level 1, RWX permissions (read, write, execute page):
//        Then access the page in S-Mode. Expected: Store, Load & Fetch page fault
// 17. PTE.D unset, PTE.A set at level 0, RWX permissions (read, write, execute page):
//        Then, access the page in S-Mode. Expected: Store-page-fault
// 18. PTE.D set, PTE.A set at level 0, RWX permissions (read, write, execute page):
//        Then, access the page in S-Mode. Expected: No fault should occur.
// 19. PTE.D set, PTE.A unset at level 0, RWX permissions (read, write, execute page):
//        Then access the page in S-Mode. Expected: Store, Load & Fetch page fault
// 20. PTE.D unset, PTE.A unset at level 0, RWX permissions (read, write, execute page):
//        Then access the page in S-Mode. Expected: Store, Load & Fetch page fault
//
// Total Expected Faults :: 35
// --------------------------------------------------------------------------------------------------------------------------------

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: [I, Sv57]
# MARCH: rv64i_zicsr
# CONFIG_DEPENDENT: true
##### END_TEST_CONFIG #####

#define TEST_FILE "sv57_Svade_Smode.S"
#define SIGUPD_COUNT 65
#define TRAP_SIGUPD_COUNT 150
#define rvtest_mtrap_routine
#define rvtest_strap_routine
#define RVTEST_PRIV_TEST
#define SKIP_MEPC

#include "riscv_arch_test.h"

RVTEST_BEGIN

//---------------------------------------------------------------------------------------------------------------------------------
// Test RWX permissions
.macro VERIFICATION_RWX TEST_CASE
  addi a2, a2, 16

  // Test store permission
  \TEST_CASE\()_store:
  sw  a2, 20(a5)
  nop

  // Test load permission
  \TEST_CASE\()_load:
  lw a3, 20(a5)
  nop

  // Test execute permission
  LI(  x4, 0xACCE)            // Store a value which is to be checked in trap handler
  \TEST_CASE\()_exec:
  jalr ra, a5, 0
  nop
.endm

.macro TEST_CASES_RUNNER LOWER_MODE, VA, level, TEST_CASE

  // Adjust offset of VA to point to test region
  .set VA_SHIFT, (\level*9)+12
  LI(a5, (\VA>>VA_SHIFT)<<VA_SHIFT)
  LA(a0, rvtest_data_1)
  slli a0, a0, 64-VA_SHIFT
  srli a0, a0, 64-VA_SHIFT
  add  a5, a5, a0             // Virtual Address

  RVTEST_GOTO_LOWER_MODE \LOWER_MODE

  VERIFICATION_RWX \TEST_CASE

  RVTEST_GOTO_MMODE

  // Signature Update
  RVTEST_SIGUPD(x2, x5, x4, a2, \TEST_CASE\()_store, \TEST_CASE\()_store_str)
  RVTEST_SIGUPD(x2, x5, x4, a3, \TEST_CASE\()_load, \TEST_CASE\()_load_str)
  RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_exec, \TEST_CASE\()_exec_str)
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

  LI(t0, MENVCFG_ADUE)
  CSRC(menvcfg, t0)                                                      // Enable Svade

///---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------
//                                                  TESTS AT LEVEL 4
//---------------------------------------------------------------------------------------------------------------------------------
//                  256TB PAGE  Region 1 under test at level 4 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 1: PTE.D unset and PTE.A set | Test in S-Mode | RWX bit set | expected = Store page fault
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL4)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL4, test1

//---------------------------------------------------------------------------------------------------------------------------------
//                  256TB PAGE  Region 1 under test at level 4 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 2: Both PTE.D and PTE.A set | Test in S-Mode | RWX bit set | expected = No Fault
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL4)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL4, test2

//---------------------------------------------------------------------------------------------------------------------------------
//                  256TB PAGE  Region 1 under test at level 4 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 3: PTE.D set and PTE.A unset | Test in S-Mode | RWX bit set | expected = Store, Load & Fetch page fault
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL4)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL4, test3

//---------------------------------------------------------------------------------------------------------------------------------
//                  256TB PAGE  Region 1 under test at level 4 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 4: Both PTE.D and PTE.A unset | Test in S-Mode | RWX bit set | expected = Store, Load & Fetch page fault
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL4)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL4, test4


//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------
//                                                  TESTS AT LEVEL 3
//---------------------------------------------------------------------------------------------------------------------------------
//                  512GB PAGE  Region 1 under test at level 3 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 5: PTE.D unset and PTE.A set | Test in S-Mode | RWX bit set | expected = Store page fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL3)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL3, test5

//---------------------------------------------------------------------------------------------------------------------------------
//                  512GB PAGE  Region 1 under test at level 3 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 6: Both PTE.D and PTE.A set | Test in S-Mode | RWX bit set | expected = No Fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL3)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL3, test6

//---------------------------------------------------------------------------------------------------------------------------------
//                  512GB PAGE  Region 1 under test at level 3 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 7: PTE.D set and PTE.A unset | Test in S-Mode | RWX bit set | expected = Store, Load & Fetch page fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL3)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL3, test7

//---------------------------------------------------------------------------------------------------------------------------------
//                  512GB PAGE  Region 1 under test at level 3 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 8: Both PTE.D and PTE.A unset | Test in S-Mode | RWX bit set | expected = Store, Load & Fetch page fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL3)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL3, test8


//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------
//                                                  TESTS AT LEVEL 2
//---------------------------------------------------------------------------------------------------------------------------------
//                  1GB PAGE    Region 1 under test at level 2 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 9: PTE.D unset and PTE.A set | Test in S-Mode | RWX bit set | expected = Store page fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL2)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL2, test9

//---------------------------------------------------------------------------------------------------------------------------------
//                  1GB PAGE    Region 1 under test at level 2 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 10: Both PTE.D and PTE.A set | Test in S-Mode | RWX bit set | expected = No Fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL2)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL2, test10

//---------------------------------------------------------------------------------------------------------------------------------
//                  1GB PAGE    Region 1 under test at level 2 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 11: PTE.D set and PTE.A unset | Test in S-Mode | RWX bit set | expected = Store, Load & Fetch page fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL2)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL2, test11

//---------------------------------------------------------------------------------------------------------------------------------
//                  1GB PAGE    Region 1 under test at level 2 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 12: Both PTE.D and PTE.A unset | Test in S-Mode | RWX bit set | expected = Store, Load & Fetch page fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL2)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL2, test12


//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------
//                                                  TESTS AT LEVEL 1
//---------------------------------------------------------------------------------------------------------------------------------
//                  2MB PAGE    Region 1 under test at level 1 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 13: PTE.D unset and PTE.A set | Test in S-Mode | RWX bit set | expected = Store page fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV57(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL1, test13

//---------------------------------------------------------------------------------------------------------------------------------
//                  2MB PAGE    Region 1 under test at level 1 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 14: Both PTE.D and PTE.A set | Test in S-Mode | RWX bit set | expected = No Fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV57(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL1, test14

//---------------------------------------------------------------------------------------------------------------------------------
//                  2MB PAGE    Region 1 under test at level 1 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 15: PTE.D set and PTE.A unset | Test in S-Mode | RWX bit set | expected = Store, Load & Fetch page fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV57(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL1, test15

//---------------------------------------------------------------------------------------------------------------------------------
//                  2MB PAGE    Region 1 under test at level 1 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 16: Both PTE.D and PTE.A unset | Test in S-Mode | RWX bit set | expected = Store, Load & Fetch page fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV57(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL1, test16


//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------
//                                                  TESTS AT LEVEL 0
//---------------------------------------------------------------------------------------------------------------------------------
//                  4KB PAGE    Region 1 under test at level 0 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 17: PTE.D unset and PTE.A set | Test in S-Mode | RWX bit set | expected = Store page fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV57(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  PTE_SETUP_SV57(rvtest_slvl0_pg_tbl, (PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV57(rvtest_data_1, (PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL0, test17

//---------------------------------------------------------------------------------------------------------------------------------
//                  4KB PAGE    Region 1 under test at level 0 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 18: Both PTE.D and PTE.A set | Test in S-Mode | RWX bit set | expected = No Fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV57(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  PTE_SETUP_SV57(rvtest_slvl0_pg_tbl, (PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL0, test18

//---------------------------------------------------------------------------------------------------------------------------------
//                  4KB PAGE    Region 1 under test at level 0 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 19: PTE.D set and PTE.A unset | Test in S-Mode | RWX bit set | expected = Store, Load & Fetch page fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV57(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  PTE_SETUP_SV57(rvtest_slvl0_pg_tbl, (PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL0, test19

//---------------------------------------------------------------------------------------------------------------------------------
//                  4KB PAGE    Region 1 under test at level 0 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 20: Both PTE.D and PTE.A unset | Test in S-Mode | RWX bit set | expected = Store, Load & Fetch page fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV57(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  PTE_SETUP_SV57(rvtest_slvl0_pg_tbl, (PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV57(rvtest_data_1, (PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL0, test20


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
  addi a4, a2, 4
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
test1_store_str: .string "\"Mismatch during sw in Test Case 1!\""
test1_load_str:  .string "\"Mismatch during lw in Test Case 1!\""
test1_exec_str:  .string "\"Mismatch during jalr in Test Case 1!\""
test2_store_str: .string "\"Mismatch during sw in Test Case 2!\""
test2_load_str:  .string "\"Mismatch during lw in Test Case 2!\""
test2_exec_str:  .string "\"Mismatch during jalr in Test Case 2!\""
test3_store_str: .string "\"Mismatch during sw in Test Case 3!\""
test3_load_str:  .string "\"Mismatch during lw in Test Case 3!\""
test3_exec_str:  .string "\"Mismatch during jalr in Test Case 3!\""
test4_store_str: .string "\"Mismatch during sw in Test Case 4!\""
test4_load_str:  .string "\"Mismatch during lw in Test Case 4!\""
test4_exec_str:  .string "\"Mismatch during jalr in Test Case 4!\""
test5_store_str: .string "\"Mismatch during sw in Test Case 5!\""
test5_load_str:  .string "\"Mismatch during lw in Test Case 5!\""
test5_exec_str:  .string "\"Mismatch during jalr in Test Case 5!\""
test6_store_str: .string "\"Mismatch during sw in Test Case 6!\""
test6_load_str:  .string "\"Mismatch during lw in Test Case 6!\""
test6_exec_str:  .string "\"Mismatch during jalr in Test Case 6!\""
test7_store_str: .string "\"Mismatch during sw in Test Case 7!\""
test7_load_str:  .string "\"Mismatch during lw in Test Case 7!\""
test7_exec_str:  .string "\"Mismatch during jalr in Test Case 7!\""
test8_store_str: .string "\"Mismatch during sw in Test Case 8!\""
test8_load_str:  .string "\"Mismatch during lw in Test Case 8!\""
test8_exec_str:  .string "\"Mismatch during jalr in Test Case 8!\""
test9_store_str: .string "\"Mismatch during sw in Test Case 9!\""
test9_load_str:  .string "\"Mismatch during lw in Test Case 9!\""
test9_exec_str:  .string "\"Mismatch during jalr in Test Case 9!\""
test10_store_str: .string "\"Mismatch during sw in Test Case 10!\""
test10_load_str:  .string "\"Mismatch during lw in Test Case 10!\""
test10_exec_str:  .string "\"Mismatch during jalr in Test Case 10!\""
test11_store_str: .string "\"Mismatch during sw in Test Case 11!\""
test11_load_str:  .string "\"Mismatch during lw in Test Case 11!\""
test11_exec_str:  .string "\"Mismatch during jalr in Test Case 11!\""
test12_store_str: .string "\"Mismatch during sw in Test Case 12!\""
test12_load_str:  .string "\"Mismatch during lw in Test Case 12!\""
test12_exec_str:  .string "\"Mismatch during jalr in Test Case 12!\""
test13_store_str: .string "\"Mismatch during sw in Test Case 13!\""
test13_load_str:  .string "\"Mismatch during lw in Test Case 13!\""
test13_exec_str:  .string "\"Mismatch during jalr in Test Case 13!\""
test14_store_str: .string "\"Mismatch during sw in Test Case 14!\""
test14_load_str:  .string "\"Mismatch during lw in Test Case 14!\""
test14_exec_str:  .string "\"Mismatch during jalr in Test Case 14!\""
test15_store_str: .string "\"Mismatch during sw in Test Case 15!\""
test15_load_str:  .string "\"Mismatch during lw in Test Case 15!\""
test15_exec_str:  .string "\"Mismatch during jalr in Test Case 15!\""
test16_store_str: .string "\"Mismatch during sw in Test Case 16!\""
test16_load_str:  .string "\"Mismatch during lw in Test Case 16!\""
test16_exec_str:  .string "\"Mismatch during jalr in Test Case 16!\""
test17_store_str: .string "\"Mismatch during sw in Test Case 17!\""
test17_load_str:  .string "\"Mismatch during lw in Test Case 17!\""
test17_exec_str:  .string "\"Mismatch during jalr in Test Case 17!\""
test18_store_str: .string "\"Mismatch during sw in Test Case 18!\""
test18_load_str:  .string "\"Mismatch during lw in Test Case 18!\""
test18_exec_str:  .string "\"Mismatch during jalr in Test Case 18!\""
test19_store_str: .string "\"Mismatch during sw in Test Case 19!\""
test19_load_str:  .string "\"Mismatch during lw in Test Case 19!\""
test19_exec_str:  .string "\"Mismatch during jalr in Test Case 19!\""
test20_store_str: .string "\"Mismatch during sw in Test Case 20!\""
test20_load_str:  .string "\"Mismatch during lw in Test Case 20!\""
test20_exec_str:  .string "\"Mismatch during jalr in Test Case 20!\""

RVTEST_DATA_END
RVTEST_SIG_SETUP
