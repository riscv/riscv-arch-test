// --------------------------------------------------------------------------------------------------------------------------------
// Developed by: Alexander Portland & Noah Rousell
// --------------------------------------------------------------------------------------------------------------------------------
// Test cases are as follows:
// --------------------------------------------------------------------------------------------------------------------------------
// 1. UKTE disabled, no PTE for the top-half virtual address:
//        Then, in U-Mode, execute sw, lw & jalr.
//        Expected: Store-page-fault, Load-page-fault, Fetch-page-fault
// 2. UKTE enabled, no PTE for the top-half virtual address:
//        Then, in U-Mode, execute sw, lw & jalr.
//        Expected: Store-page-fault, Load-page-fault, Fetch-page-fault
// 3. UKTE disabled, valid RWXU PTE for the top-half virtual address:
//        Then, in U-Mode, execute sw, lw & jalr.
//        Expected: All accesses complete successfully
// 4. UKTE enabled, valid RWXU PTE for the top-half virtual address:
//        Then, in U-Mode, execute sw, lw & jalr.
//        Expected: Store-page-fault, Load-page-fault, Fetch-page-fault
// 5. UKTE disabled, no PTE for the lower-half virtual address:
//        Then, in U-Mode, execute sw, lw & jalr.
//        Expected: Store-page-fault, Load-page-fault, Fetch-page-fault
// 6. UKTE enabled, no PTE for the lower-half virtual address:
//        Then, in U-Mode, execute sw, lw & jalr.
//        Expected: Store-page-fault, Load-page-fault, Fetch-page-fault
// 7. UKTE disabled, valid RWXU PTE for the lower-half virtual address:
//        Then, in U-Mode, execute sw, lw & jalr.
//        Expected: All accesses complete successfully
// 8. UKTE enabled, valid RWXU PTE for the lower-half virtual address:
//        Then, in U-Mode, execute sw, lw & jalr.
//        Expected: All accesses complete successfully
// --------------------------------------------------------------------------------------------------------------------------------
// Total Expected Faults :: 15
// --------------------------------------------------------------------------------------------------------------------------------

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: [I, Sv48, Svukte]
# MARCH: rv64i_zicsr_zifencei
##### END_TEST_CONFIG #####

#define SIGUPD_COUNT 24
#define TRAP_SIGUPD_COUNT 64

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
  \TEST_CASE\()_exec:
  jalr ra, a5, 0
  nop
.endm

.macro TEST_CASES_RUNNER QUAL, VA, level, TEST_CASE

  // Set or clear senvcfg.UKTE for this test case.
  LI(t0, SENVCFG_UKTE)
  .ifc \QUAL, Qualified
    csrs senvcfg, t0
  .else
    csrc senvcfg, t0
  .endif

  // Adjust offset of VA to point to the test region.
  .set VA_SHIFT, (\level*9)+12
  LI(a5, (\VA>>VA_SHIFT)<<VA_SHIFT)
  LA(a0, rvtest_data_1)
  slli a0, a0, 64-VA_SHIFT
  srli a0, a0, 64-VA_SHIFT
  add  a5, a5, a0             // Virtual Address

  // Initialize result registers so a fault leaves their sentinels unchanged.
  LI(a3, 0xdeadbeef)
  LI(a4, 0xdeadbeef)

  RVTEST_GOTO_LOWER_MODE Umode

  VERIFICATION_RWX \TEST_CASE

  RVTEST_GOTO_MMODE

  // Signature Update
  RVTEST_SIGUPD(x2, x5, x4, a2, \TEST_CASE\()_store, \TEST_CASE\()_store_str)
  RVTEST_SIGUPD(x2, x5, x4, a3, \TEST_CASE\()_load, \TEST_CASE\()_load_str)
  RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_exec, \TEST_CASE\()_exec_str)
.endm

main:
  LI( a2, 0x800)            // Test signature initialization

//---------------------------------------------------------------------------------------------------------------------------------
//                                   Virtual addresses definition for code and test regions
//---------------------------------------------------------------------------------------------------------------------------------

  // First canonical upper-half region for Sv48.
  .set va_data, 0xFFFF800000000000

  // Virtual address in the lower, canonical half of the Sv48 address space.
  .set va_data_lower, 0x0000400000000000

  // Virtual Address for code region
  .set va_rvtest_code_begin,  0x030080000000

  // PTE setup for Code Region
  SUPERPAGE_PTE_SETUP_SV48(rvtest_code_begin, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_R | PTE_V), va_rvtest_code_begin, LEVEL3)
  sfence.vma

  // Save area setup for code region
  csrr a0, mscratch
  SAVE_AREA_SETUP(va_rvtest_code_begin, rvtest_code_begin, code, LEVEL3)

//---------------------------------------------------------------------------------------------------------------------------------
//                                               Test Cases Start from here
//---------------------------------------------------------------------------------------------------------------------------------

  SATP_SETUP_RV64(sv48)                                                  // Set SATP for virtualization
  sfence.vma                                                             // Flush TLB

//---------------------------------------------------------------------------------------------------------------------------------
//                                                    TESTS WITHOUT A DATA PTE
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 1: UKTE disabled | Test in U-Mode | no PTE | expected = RWX fault
  TEST_CASES_RUNNER Unqualified, va_data, LEVEL3, test1

  // Test case 2: UKTE enabled | Test in U-Mode | no PTE | expected = RWX fault
  TEST_CASES_RUNNER Qualified, va_data, LEVEL3, test2

//---------------------------------------------------------------------------------------------------------------------------------
//                                                    TESTS WITH A VALID DATA PTE
//---------------------------------------------------------------------------------------------------------------------------------

  // Valid RWXU PTE for the top-half test region.
  SUPERPAGE_PTE_SETUP_SV48(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL3)
  sfence.vma

  // Test case 3: UKTE disabled | Test in U-Mode | valid RWXU PTE | expected = no fault
  TEST_CASES_RUNNER Unqualified, va_data, LEVEL3, test3

  // Test case 4: UKTE enabled | Test in U-Mode | valid RWXU PTE | expected = RWX fault
  TEST_CASES_RUNNER Qualified, va_data, LEVEL3, test4

//---------------------------------------------------------------------------------------------------------------------------------
//                                                    TESTS IN THE LOWER HALF
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 5: UKTE disabled | Test in U-Mode | no PTE | expected = RWX fault
  TEST_CASES_RUNNER Unqualified, va_data_lower, LEVEL3, test5

  // Test case 6: UKTE enabled | Test in U-Mode | no PTE | expected = RWX fault
  // UKTE does not change accesses below 2^(SXLEN-1).
  TEST_CASES_RUNNER Qualified, va_data_lower, LEVEL3, test6

  // Valid RWXU PTE for the lower-half test region.
  SUPERPAGE_PTE_SETUP_SV48(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_data_lower, LEVEL3)
  sfence.vma

  // Test case 7: UKTE disabled | Test in U-Mode | valid RWXU PTE | expected = no fault
  TEST_CASES_RUNNER Unqualified, va_data_lower, LEVEL3, test7

  // Test case 8: UKTE enabled | Test in U-Mode | valid RWXU PTE | expected = no fault
  // UKTE does not change accesses below 2^(SXLEN-1).
  TEST_CASES_RUNNER Qualified, va_data_lower, LEVEL3, test8

//---------------------------------------------------------------------------------------------------------------------------------
RVTEST_CODE_END
RVTEST_DATA_BEGIN

//---------------------------------------------------------------------------------------------------------------------------------

.p2align 12
rvtest_data_1:
  nop
  addi a4, a2, 4
  jr ra
  nop
  .word 0xbeefcaf1          // Random word
  .word 0xbeefcaf2          // Random word
  nop
  jr ra

// Page Tables
.p2align 12
rvtest_slvl0_pg_tbl:
    .skip(4096)
rvtest_slvl1_pg_tbl:
    .skip(4096)
rvtest_slvl2_pg_tbl:
    .skip(4096)

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

RVTEST_DATA_END
RVTEST_SIG_SETUP
