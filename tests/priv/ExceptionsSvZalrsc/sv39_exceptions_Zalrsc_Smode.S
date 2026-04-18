//---------------------------------------------------------------------------------------------------------------------------------
// Developed by: Umer Shahid & Muhammad Zain
//---------------------------------------------------------------------------------------------------------------------------------
// NOTE: Exception types may vary according to section 13.2 of Unpriv ISA Spec and Table 15 of Priv ISA Spec
//---------------------------------------------------------------------------------------------------------------------------------
// Test cases are as follows:
//---------------------------------------------------------------------------------------------------------------------------------
// 1. Setup a valid PTE at level 2 with RWX permissions pointing to test region
//        Then, in S-Mode, execute lr.w & sc.w.
//        Expected: No fault
// 2. Setup a valid PTE at level 2 with RWX permissions pointing to test region
//        Then, in S-Mode, execute lr.w & sc.w using a misaligned VA.
//        Expected: 1 Load address-misaligned/access fault & 1 Store/AMO address-misaligned/access fault
// 3. Setup a valid PTE at level 2 with RWX permissions pointing to RVMODEL_ACCESS_FAULT_ADDRESS
//        Then, in S-Mode, execute lr.w & sc.w.
//        Expected: 1 Load access fault & 1 Store/AMO access fault
// 4. Setup a valid PTE at level 2 with RWX permissions pointing to RVMODEL_ACCESS_FAULT_ADDRESS
//        Then, in S-Mode, execute lr.w & sc.w using a misaligned VA.
//        Expected: 1 Load address-misaligned/access fault & 1 Store/AMO address-misaligned/access fault
// 5. Setup an invalid PTE at level 2 with RWX permissions pointing to test region
//        Then, in S-Mode, execute lr.w & sc.w.
//        Expected: 1 Load page fault & 1 Store/AMO page fault
// 6. Setup an invalid PTE at level 2 with RWX permissions pointing to test region
//        Then, in S-Mode, execute lr.w & sc.w using a misaligned VA.
//        Expected: 1 Load address-misaligned/access/page fault & 1 Store/AMO address-misaligned/access/page fault
// 7. Setup an invalid PTE at level 2 with RWX permissions pointing to RVMODEL_ACCESS_FAULT_ADDRESS
//        Then, in S-Mode, execute lr.w & sc.w.
//        Expected: 1 Load page fault & 1 Store/AMO page fault
// 8. Setup an invalid PTE at level 2 with RWX permissions pointing to RVMODEL_ACCESS_FAULT_ADDRESS
//        Then, in S-Mode, execute lr.w & sc.w using a misaligned VA.
//        Expected: 1 Load address-misaligned/access/page fault & 1 Store/AMO address-misaligned/access/page fault
// 9-36. Setup valid and invalid PTEs at level 2 with RWX permissions
//        Then, in S-Mode walk through medeleg and execute lr.w & sc.w.
//        Expected: 14 Load page faults & 14 Store/AMO page faults
//
// Total Expected Faults :: 42 (+2 while transitioning to higher priv-mode)
//---------------------------------------------------------------------------------------------------------------------------------

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: [I, Sv39, Zalrsc]
# MARCH: rv64i_zicsr_zalrsc
# CONFIG_DEPENDENT: true
##### END_TEST_CONFIG #####

#define TEST_FILE "sv39_exceptions_Zalrsc_Smode.S"
#define SIGUPD_COUNT 90
#define TRAP_SIGUPD_COUNT 190
#define rvtest_mtrap_routine
#define rvtest_strap_routine
#define RVTEST_PRIV_TEST
#define SKIP_MEPC

#include "riscv_arch_test.h"

RVTEST_BEGIN

//---------------------------------------------------------------------------------------------------------------------------------
// Test RWX permissions
.macro VERIFICATION_RWX TEST_CASE
  addi a2, a2, 1

  \TEST_CASE\()_lr:
  lr.w a3, (a5)
  nop

  \TEST_CASE\()_sc:
  sc.w a4, a2, (a5)
  nop

.endm

.macro TEST_CASES_RUNNER LOWER_MODE, VA, level, TEST_CASE, PA=, ECALL_DELEG=

  // Adjust offset of VA to point to test region
  .set VA_MASK, ~(((1<<((\level*9)+12))-1)&~3)
  .set PA_SHIFT, 64-((\level*9)+12)
  LI(a5, (\VA & VA_MASK))
  .ifnb \PA                   // If PA is provided as an argument
    LI(a0, \PA)
  .else
    LA(a0, rvtest_data_1)
  .endif
  slli a0, a0, PA_SHIFT
  srli a0, a0, PA_SHIFT
  add  a5, a5, a0             // Virtual Address

  RVTEST_GOTO_LOWER_MODE \LOWER_MODE

  VERIFICATION_RWX \TEST_CASE

  .ifnb \ECALL_DELEG
    RVTEST_GOTO_DELEGATED_MMODE
  .else
    RVTEST_GOTO_MMODE
  .endif

  // Signature Update
  RVTEST_SIGUPD(x2, x5, x4, a3, \TEST_CASE\()_lr, \TEST_CASE\()_lr_str)
  RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_sc, \TEST_CASE\()_sc_str)
.endm


main:
  LI( a2, 0x8)                // Test signature initialization

//---------------------------------------------------------------------------------------------------------------------------------
//                               Virtual addresses definition for code, data and test regions
//---------------------------------------------------------------------------------------------------------------------------------

  // Virtual Address of Test section (rvtest_data_1)
  .set va_data,               0x140802000
  .set va_data_inv,           0x180802000

  // Virtual Address for code & data regions
  .set va_rvtest_code_begin,  0x1C0000000
  .set va_rvtest_data_begin,  0x080000000


  // PTE setup for Code Region
  SUPERPAGE_PTE_SETUP_SV39(rvtest_code_begin, (PTE_D | PTE_A | PTE_X | PTE_R | PTE_V), va_rvtest_code_begin, LEVEL2)
  sfence.vma
  // PTE setup for Data Region (Identity mapped)
  SUPERPAGE_PTE_SETUP_SV39(rvtest_data_begin, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_rvtest_data_begin, LEVEL2)
  sfence.vma

  // Save area setup for code region
  csrr a0, mscratch
  SAVE_AREA_SETUP(va_rvtest_code_begin, rvtest_code_begin, code)

//---------------------------------------------------------------------------------------------------------------------------------
//                                               Test Cases Start from here
//---------------------------------------------------------------------------------------------------------------------------------

  SATP_SETUP_RV64(sv39)                                                  // Set SATP for virtualization
  sfence.vma                                                             // Flush TLB

//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------
//                                                    TESTS AT LEVEL 2
//---------------------------------------------------------------------------------------------------------------------------------
//                    1GB PAGE    Region 1 under test at level 2 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 1-2: Test in S-Mode | Valid PTE | RWX set | expected = 2 faults
  SUPERPAGE_PTE_SETUP_SV39(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL2)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL2, test1
  sfence.vma
  TEST_CASES_RUNNER Smode, (va_data+0x2), LEVEL2, test2

//---------------------------------------------------------------------------------------------------------------------------------
//                    1GB PAGE    Region 1 under test at level 2 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 3-4: Test in S-Mode | Valid PTE | RWX set | Points to RVMODEL_ACCESS_FAULT_ADDRESS | expected = 4 faults
  SUPERPAGE_PTE_SETUP_SV39(RVMODEL_ACCESS_FAULT_ADDRESS, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL2)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL2, test3, RVMODEL_ACCESS_FAULT_ADDRESS
  sfence.vma
  TEST_CASES_RUNNER Smode, (va_data+0x2), LEVEL2, test4, RVMODEL_ACCESS_FAULT_ADDRESS

//---------------------------------------------------------------------------------------------------------------------------------
//                    1GB PAGE    Region 1 under test at level 2 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 5-6: Test in S-Mode | Invalid PTE | RWX set | expected = 4 faults
  SUPERPAGE_PTE_SETUP_SV39(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R), va_data, LEVEL2)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL2, test5
  sfence.vma
  TEST_CASES_RUNNER Smode, (va_data+0x2), LEVEL2, test6

//---------------------------------------------------------------------------------------------------------------------------------
//                    1GB PAGE    Region 1 under test at level 2 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 7-8: Test in S-Mode | Invalid PTE | RWX set | Points to RVMODEL_ACCESS_FAULT_ADDRESS | expected = 4 faults
  SUPERPAGE_PTE_SETUP_SV39(RVMODEL_ACCESS_FAULT_ADDRESS, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R), va_data, LEVEL2)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL2, test7, RVMODEL_ACCESS_FAULT_ADDRESS
  sfence.vma
  TEST_CASES_RUNNER Smode, (va_data+0x2), LEVEL2, test8, RVMODEL_ACCESS_FAULT_ADDRESS


//---------------------------------------------------------------------------------------------------------------------------------
//                    1GB PAGE    Region 1 under test at level 2 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  SUPERPAGE_PTE_SETUP_SV39(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL2)   // Valid PTE
  SUPERPAGE_PTE_SETUP_SV39(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R), va_data_inv, LEVEL2)       // Invalid PTE
  sfence.vma

  // Test case 9-10: Test in S-Mode | Valid & Invalid PTEs | RWX set | medeleg[0] set | expected = 2 faults
  li a1, 1
  CSRW(medeleg, a1)
  TEST_CASES_RUNNER Smode, va_data, LEVEL2, test9
  sfence.vma
  TEST_CASES_RUNNER Smode, va_data_inv, LEVEL2, test10
  sfence.vma

  // Test case 11-12: Test in S-Mode | Valid & Invalid PTEs | RWX set | medeleg[1] set | expected = 2 faults
  slli a1, a1, 1
  CSRW(medeleg, a1)
  TEST_CASES_RUNNER Smode, va_data, LEVEL2, test11
  sfence.vma
  TEST_CASES_RUNNER Smode, va_data_inv, LEVEL2, test12
  sfence.vma

  // Test case 13-14: Test in S-Mode | Valid & Invalid PTEs | RWX set | medeleg[2] set | expected = 2 faults
  slli a1, a1, 1
  CSRW(medeleg, a1)
  TEST_CASES_RUNNER Smode, va_data, LEVEL2, test13
  sfence.vma
  TEST_CASES_RUNNER Smode, va_data_inv, LEVEL2, test14
  sfence.vma

  // Test case 15-16: Test in S-Mode | Valid & Invalid PTEs | RWX set | medeleg[3] set | expected = 2 faults
  slli a1, a1, 1
  CSRW(medeleg, a1)
  TEST_CASES_RUNNER Smode, va_data, LEVEL2, test15
  sfence.vma
  TEST_CASES_RUNNER Smode, va_data_inv, LEVEL2, test16
  sfence.vma

  // Test case 17-18: Test in S-Mode | Valid & Invalid PTEs | RWX set | medeleg[4] set | expected = 2 faults
  slli a1, a1, 1
  CSRW(medeleg, a1)
  TEST_CASES_RUNNER Smode, va_data, LEVEL2, test17
  sfence.vma
  TEST_CASES_RUNNER Smode, va_data_inv, LEVEL2, test18
  sfence.vma

  // Test case 19-20: Test in S-Mode | Valid & Invalid PTEs | RWX set | medeleg[5] set | expected = 2 faults
  slli a1, a1, 1
  CSRW(medeleg, a1)
  TEST_CASES_RUNNER Smode, va_data, LEVEL2, test19
  sfence.vma
  TEST_CASES_RUNNER Smode, va_data_inv, LEVEL2, test20
  sfence.vma

  // Test case 21-22: Test in S-Mode | Valid & Invalid PTEs | RWX set | medeleg[6] set | expected = 2 faults
  slli a1, a1, 1
  CSRW(medeleg, a1)
  TEST_CASES_RUNNER Smode, va_data, LEVEL2, test21
  sfence.vma
  TEST_CASES_RUNNER Smode, va_data_inv, LEVEL2, test22
  sfence.vma

  // Test case 23-24: Test in S-Mode | Valid & Invalid PTEs | RWX set | medeleg[7] set | expected = 2 faults
  slli a1, a1, 1
  CSRW(medeleg, a1)
  TEST_CASES_RUNNER Smode, va_data, LEVEL2, test23
  sfence.vma
  TEST_CASES_RUNNER Smode, va_data_inv, LEVEL2, test24
  sfence.vma

  // Test case 25-26: Test in S-Mode | Valid & Invalid PTEs | RWX set | medeleg[8] set | expected = 2 faults
  slli a1, a1, 1
  CSRW(medeleg, a1)
  TEST_CASES_RUNNER Smode, va_data, LEVEL2, test25
  sfence.vma
  TEST_CASES_RUNNER Smode, va_data_inv, LEVEL2, test26
  sfence.vma

  // Test case 27-28: Test in S-Mode | Valid & Invalid PTEs | RWX set | medeleg[9] set | expected = 2 faults
  slli a1, a1, 1
  CSRW(medeleg, a1)
  TEST_CASES_RUNNER Smode, va_data, LEVEL2, test27, ECALL_DELEG=1
  sfence.vma
  TEST_CASES_RUNNER Smode, va_data_inv, LEVEL2, test28, ECALL_DELEG=1
  sfence.vma

  // Test case 29-30: Test in S-Mode | Valid & Invalid PTEs | RWX set | medeleg[12] set | expected = 2 faults
  slli a1, a1, 3
  CSRW(medeleg, a1)
  TEST_CASES_RUNNER Smode, va_data, LEVEL2, test29
  sfence.vma
  TEST_CASES_RUNNER Smode, va_data_inv, LEVEL2, test30
  sfence.vma

  // Test case 31-32: Test in S-Mode | Valid & Invalid PTEs | RWX set | medeleg[13] set | expected = 2 faults
  slli a1, a1, 1
  CSRW(medeleg, a1)
  TEST_CASES_RUNNER Smode, va_data, LEVEL2, test31
  sfence.vma
  TEST_CASES_RUNNER Smode, va_data_inv, LEVEL2, test32
  sfence.vma

  // Test case 33-34: Test in S-Mode | Valid & Invalid PTEs | RWX set | medeleg[15] set | expected = 2 faults
  slli a1, a1, 2
  CSRW(medeleg, a1)
  TEST_CASES_RUNNER Smode, va_data, LEVEL2, test33
  sfence.vma
  TEST_CASES_RUNNER Smode, va_data_inv, LEVEL2, test34
  sfence.vma

  // Test case 35-36: Test in S-Mode | Valid & Invalid PTEs | RWX set | set medeleg = 0xB1FF | expected = 2 faults
  LI(a1, 0xB1FF)
  CSRW(medeleg, a1)
  TEST_CASES_RUNNER Smode, va_data, LEVEL2, test35
  sfence.vma
  TEST_CASES_RUNNER Smode, va_data_inv, LEVEL2, test36
  sfence.vma


//---------------------------------------------------------------------------------------------------------------------------------
RVTEST_CODE_END
RVTEST_DATA_BEGIN

//---------------------------------------------------------------------------------------------------------------------------------
//                                            PHYSICAL ADDRESS REGION FOR TESTING
//---------------------------------------------------------------------------------------------------------------------------------
// Physical Address region under testing for LEVEL 0, 1 and 2
.align 12
rvtest_data_1:
  .word 0xbeef0000
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

test1_lr_str:  .string "\"Mismatch during lr.w in Test Case 1!\""
test1_sc_str:  .string "\"Mismatch during sc.w in Test Case 1!\""
test2_lr_str:  .string "\"Mismatch during lr.w in Test Case 2!\""
test2_sc_str:  .string "\"Mismatch during sc.w in Test Case 2!\""
test3_lr_str:  .string "\"Mismatch during lr.w in Test Case 3!\""
test3_sc_str:  .string "\"Mismatch during sc.w in Test Case 3!\""
test4_lr_str:  .string "\"Mismatch during lr.w in Test Case 4!\""
test4_sc_str:  .string "\"Mismatch during sc.w in Test Case 4!\""
test5_lr_str:  .string "\"Mismatch during lr.w in Test Case 5!\""
test5_sc_str:  .string "\"Mismatch during sc.w in Test Case 5!\""
test6_lr_str:  .string "\"Mismatch during lr.w in Test Case 6!\""
test6_sc_str:  .string "\"Mismatch during sc.w in Test Case 6!\""
test7_lr_str:  .string "\"Mismatch during lr.w in Test Case 7!\""
test7_sc_str:  .string "\"Mismatch during sc.w in Test Case 7!\""
test8_lr_str:  .string "\"Mismatch during lr.w in Test Case 8!\""
test8_sc_str:  .string "\"Mismatch during sc.w in Test Case 8!\""
test9_lr_str:  .string "\"Mismatch during lr.w in Test Case 9!\""
test9_sc_str:  .string "\"Mismatch during sc.w in Test Case 9!\""
test10_lr_str:  .string "\"Mismatch during lr.w in Test Case 10!\""
test10_sc_str:  .string "\"Mismatch during sc.w in Test Case 10!\""
test11_lr_str:  .string "\"Mismatch during lr.w in Test Case 11!\""
test11_sc_str:  .string "\"Mismatch during sc.w in Test Case 11!\""
test12_lr_str:  .string "\"Mismatch during lr.w in Test Case 12!\""
test12_sc_str:  .string "\"Mismatch during sc.w in Test Case 12!\""
test13_lr_str:  .string "\"Mismatch during lr.w in Test Case 13!\""
test13_sc_str:  .string "\"Mismatch during sc.w in Test Case 13!\""
test14_lr_str:  .string "\"Mismatch during lr.w in Test Case 14!\""
test14_sc_str:  .string "\"Mismatch during sc.w in Test Case 14!\""
test15_lr_str:  .string "\"Mismatch during lr.w in Test Case 15!\""
test15_sc_str:  .string "\"Mismatch during sc.w in Test Case 15!\""
test16_lr_str:  .string "\"Mismatch during lr.w in Test Case 16!\""
test16_sc_str:  .string "\"Mismatch during sc.w in Test Case 16!\""
test17_lr_str:  .string "\"Mismatch during lr.w in Test Case 17!\""
test17_sc_str:  .string "\"Mismatch during sc.w in Test Case 17!\""
test18_lr_str:  .string "\"Mismatch during lr.w in Test Case 18!\""
test18_sc_str:  .string "\"Mismatch during sc.w in Test Case 18!\""
test19_lr_str:  .string "\"Mismatch during lr.w in Test Case 19!\""
test19_sc_str:  .string "\"Mismatch during sc.w in Test Case 19!\""
test20_lr_str:  .string "\"Mismatch during lr.w in Test Case 20!\""
test20_sc_str:  .string "\"Mismatch during sc.w in Test Case 20!\""
test21_lr_str:  .string "\"Mismatch during lr.w in Test Case 21!\""
test21_sc_str:  .string "\"Mismatch during sc.w in Test Case 21!\""
test22_lr_str:  .string "\"Mismatch during lr.w in Test Case 22!\""
test22_sc_str:  .string "\"Mismatch during sc.w in Test Case 22!\""
test23_lr_str:  .string "\"Mismatch during lr.w in Test Case 23!\""
test23_sc_str:  .string "\"Mismatch during sc.w in Test Case 23!\""
test24_lr_str:  .string "\"Mismatch during lr.w in Test Case 24!\""
test24_sc_str:  .string "\"Mismatch during sc.w in Test Case 24!\""
test25_lr_str:  .string "\"Mismatch during lr.w in Test Case 25!\""
test25_sc_str:  .string "\"Mismatch during sc.w in Test Case 25!\""
test26_lr_str:  .string "\"Mismatch during lr.w in Test Case 26!\""
test26_sc_str:  .string "\"Mismatch during sc.w in Test Case 26!\""
test27_lr_str:  .string "\"Mismatch during lr.w in Test Case 27!\""
test27_sc_str:  .string "\"Mismatch during sc.w in Test Case 27!\""
test28_lr_str:  .string "\"Mismatch during lr.w in Test Case 28!\""
test28_sc_str:  .string "\"Mismatch during sc.w in Test Case 28!\""
test29_lr_str:  .string "\"Mismatch during lr.w in Test Case 29!\""
test29_sc_str:  .string "\"Mismatch during sc.w in Test Case 29!\""
test30_lr_str:  .string "\"Mismatch during lr.w in Test Case 30!\""
test30_sc_str:  .string "\"Mismatch during sc.w in Test Case 30!\""
test31_lr_str:  .string "\"Mismatch during lr.w in Test Case 31!\""
test31_sc_str:  .string "\"Mismatch during sc.w in Test Case 31!\""
test32_lr_str:  .string "\"Mismatch during lr.w in Test Case 32!\""
test32_sc_str:  .string "\"Mismatch during sc.w in Test Case 32!\""
test33_lr_str:  .string "\"Mismatch during lr.w in Test Case 33!\""
test33_sc_str:  .string "\"Mismatch during sc.w in Test Case 33!\""
test34_lr_str:  .string "\"Mismatch during lr.w in Test Case 34!\""
test34_sc_str:  .string "\"Mismatch during sc.w in Test Case 34!\""
test35_lr_str:  .string "\"Mismatch during lr.w in Test Case 35!\""
test35_sc_str:  .string "\"Mismatch during sc.w in Test Case 35!\""
test36_lr_str:  .string "\"Mismatch during lr.w in Test Case 36!\""
test36_sc_str:  .string "\"Mismatch during sc.w in Test Case 36!\""

RVTEST_DATA_END
RVTEST_SIG_SETUP
