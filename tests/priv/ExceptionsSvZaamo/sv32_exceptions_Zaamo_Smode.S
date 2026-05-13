// --------------------------------------------------------------------------------------------------------------------------------
// Developed by: Umer Shahid & Muhammad Zain
// --------------------------------------------------------------------------------------------------------------------------------
// NOTE: Exception types may vary according to section 13.4 of Unpriv ISA Spec and Table 15 of Priv ISA Spec
// --------------------------------------------------------------------------------------------------------------------------------
// Test cases are as follows:
// --------------------------------------------------------------------------------------------------------------------------------
// 1. Setup a valid PTE at level 1 with RWX permissions pointing to test region
//        Then, in S-Mode, execute amoadd.w. Expected: No fault
// 2. Setup a valid PTE at level 1 with RWX permissions pointing to test region
//        Then, in S-Mode, execute amoadd.w using a misaligned VA. Expected: Store/AMO address-misaligned/access fault
// 3. Setup a valid PTE at level 1 with RWX permissions pointing to RVMODEL_ACCESS_FAULT_ADDRESS
//        Then, in S-Mode, execute amoadd.w. Expected: Store/AMO access fault
// 4. Setup a valid PTE at level 1 with RWX permissions pointing to RVMODEL_ACCESS_FAULT_ADDRESS
//        Then, in S-Mode, execute amoadd.w using a misaligned VA. Expected: Store/AMO address-misaligned/access fault
// 5. Setup an invalid PTE at level 1 with RWX permissions pointing to test region
//        Then, in S-Mode, execute amoadd.w. Expected: Store/AMO page fault
// 6. Setup an invalid PTE at level 1 with RWX permissions pointing to test region
//        Then, in S-Mode, execute amoadd.w using a misaligned VA. Expected: Store/AMO address-misaligned/access/page fault
// 7. Setup an invalid PTE at level 1 with RWX permissions pointing to RVMODEL_ACCESS_FAULT_ADDRESS
//        Then, in S-Mode, execute amoadd.w. Expected: Store/AMO page fault
// 8. Setup an invalid PTE at level 1 with RWX permissions pointing to RVMODEL_ACCESS_FAULT_ADDRESS
//        Then, in S-Mode, execute amoadd.w using a misaligned VA. Expected: Store/AMO address-misaligned/access/page fault
// 9-36. Setup valid and invalid PTEs at level 1 with RWX permissions
//        Then, in S-Mode walk through medeleg and execute amoadd.w. Expected: 14 Store/AMO page faults
//
// Total Expected Faults :: 21 (+2 while transitioning to higher priv-mode)
// --------------------------------------------------------------------------------------------------------------------------------

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: [I, Sv32, Zaamo]
# MARCH: rv32i_zicsr_zaamo
##### END_TEST_CONFIG #####

#define TEST_FILE "sv32_exceptions_Zaamo_Smode.S"
#define SIGUPD_COUNT 45
#define TRAP_SIGUPD_COUNT 110
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

  \TEST_CASE\():
  amoadd.w a3, a2, (a5)
  nop

.endm

.macro TEST_CASES_RUNNER LOWER_MODE, VA, level, TEST_CASE, PA=, ECALL_DELEG=

  // Adjust offset of VA to point to test region
  .set VA_MASK, ~(((1<<((\level*10)+12))-1)&~3)
  .set PA_SHIFT, 32-((\level*10)+12)
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
  RVTEST_SIGUPD(x2, x5, x4, a3, \TEST_CASE\(), \TEST_CASE\()_str)
.endm


main:
  LI( a2, 0x8)                // Test signature initialization

//---------------------------------------------------------------------------------------------------------------------------------
//                               Virtual addresses definition for code, data and test regions
//---------------------------------------------------------------------------------------------------------------------------------

  // Virtual Address of Test section (rvtest_data_1)
  .set va_data,               0x90407000
  .set va_data_inv,           0x90807000

  // Virtual Address for code & data regions
  .set va_rvtest_code_begin,  0x30000000
  .set va_rvtest_data_begin,  0x80000000


  // PTE setup for Code Region
  SUPERPAGE_PTE_SETUP_SV32(rvtest_code_begin, (PTE_D | PTE_A | PTE_X | PTE_R | PTE_V), va_rvtest_code_begin, LEVEL1)
  sfence.vma
  // PTE setup for Data Region (Identity mapped)
  SUPERPAGE_PTE_SETUP_SV32(rvtest_data_begin, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_rvtest_data_begin, LEVEL1)
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

  // Test case 1-2: Test in S-Mode | Valid PTE | RWX set | expected = 1 fault
  SUPERPAGE_PTE_SETUP_SV32(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL1, test1
  sfence.vma
  TEST_CASES_RUNNER Smode, (va_data+0x2), LEVEL1, test2

//---------------------------------------------------------------------------------------------------------------------------------
//                    4MB PAGE    Region 1 under test at level 1 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 3-4: Test in S-Mode | Valid PTE | RWX set | Points to RVMODEL_ACCESS_FAULT_ADDRESS | expected = 2 faults
  SUPERPAGE_PTE_SETUP_SV32(RVMODEL_ACCESS_FAULT_ADDRESS, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL1, test3, RVMODEL_ACCESS_FAULT_ADDRESS
  sfence.vma
  TEST_CASES_RUNNER Smode, (va_data+0x2), LEVEL1, test4, RVMODEL_ACCESS_FAULT_ADDRESS

//---------------------------------------------------------------------------------------------------------------------------------
//                    4MB PAGE    Region 1 under test at level 1 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 5-6: Test in S-Mode | Invalid PTE | RWX set | expected = 2 faults
  SUPERPAGE_PTE_SETUP_SV32(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R), va_data, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL1, test5
  sfence.vma
  TEST_CASES_RUNNER Smode, (va_data+0x2), LEVEL1, test6

//---------------------------------------------------------------------------------------------------------------------------------
//                    4MB PAGE    Region 1 under test at level 1 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 7-8: Test in S-Mode | Invalid PTE | RWX set | Points to RVMODEL_ACCESS_FAULT_ADDRESS | expected = 2 faults
  SUPERPAGE_PTE_SETUP_SV32(RVMODEL_ACCESS_FAULT_ADDRESS, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R), va_data, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL1, test7, RVMODEL_ACCESS_FAULT_ADDRESS
  sfence.vma
  TEST_CASES_RUNNER Smode, (va_data+0x2), LEVEL1, test8, RVMODEL_ACCESS_FAULT_ADDRESS


//---------------------------------------------------------------------------------------------------------------------------------
//                    4MB PAGE    Region 1 under test at level 1 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  SUPERPAGE_PTE_SETUP_SV32(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL1)   // Valid PTE
  SUPERPAGE_PTE_SETUP_SV32(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R), va_data_inv, LEVEL1)       // Invalid PTE
  sfence.vma

  // Test case 9-10: Test in S-Mode | Valid & Invalid PTEs | RWX set | medeleg[0] set | expected = 1 Store/AMO page fault
  li a1, 1
  CSRW(medeleg, a1)
  TEST_CASES_RUNNER Smode, va_data, LEVEL1, test9
  sfence.vma
  TEST_CASES_RUNNER Smode, va_data_inv, LEVEL1, test10
  sfence.vma

  // Test case 11-12: Test in S-Mode | Valid & Invalid PTEs | RWX set | medeleg[1] set | expected = 1 Store/AMO page fault
  slli a1, a1, 1
  CSRW(medeleg, a1)
  TEST_CASES_RUNNER Smode, va_data, LEVEL1, test11
  sfence.vma
  TEST_CASES_RUNNER Smode, va_data_inv, LEVEL1, test12
  sfence.vma

  // Test case 13-14: Test in S-Mode | Valid & Invalid PTEs | RWX set | medeleg[2] set | expected = 1 Store/AMO page fault
  slli a1, a1, 1
  CSRW(medeleg, a1)
  TEST_CASES_RUNNER Smode, va_data, LEVEL1, test13
  sfence.vma
  TEST_CASES_RUNNER Smode, va_data_inv, LEVEL1, test14
  sfence.vma

  // Test case 15-16: Test in S-Mode | Valid & Invalid PTEs | RWX set | medeleg[3] set | expected = 1 Store/AMO page fault
  slli a1, a1, 1
  CSRW(medeleg, a1)
  TEST_CASES_RUNNER Smode, va_data, LEVEL1, test15
  sfence.vma
  TEST_CASES_RUNNER Smode, va_data_inv, LEVEL1, test16
  sfence.vma

  // Test case 17-18: Test in S-Mode | Valid & Invalid PTEs | RWX set | medeleg[4] set | expected = 1 Store/AMO page fault
  slli a1, a1, 1
  CSRW(medeleg, a1)
  TEST_CASES_RUNNER Smode, va_data, LEVEL1, test17
  sfence.vma
  TEST_CASES_RUNNER Smode, va_data_inv, LEVEL1, test18
  sfence.vma

  // Test case 19-20: Test in S-Mode | Valid & Invalid PTEs | RWX set | medeleg[5] set | expected = 1 Store/AMO page fault
  slli a1, a1, 1
  CSRW(medeleg, a1)
  TEST_CASES_RUNNER Smode, va_data, LEVEL1, test19
  sfence.vma
  TEST_CASES_RUNNER Smode, va_data_inv, LEVEL1, test20
  sfence.vma

  // Test case 21-22: Test in S-Mode | Valid & Invalid PTEs | RWX set | medeleg[6] set | expected = 1 Store/AMO page fault
  slli a1, a1, 1
  CSRW(medeleg, a1)
  TEST_CASES_RUNNER Smode, va_data, LEVEL1, test21
  sfence.vma
  TEST_CASES_RUNNER Smode, va_data_inv, LEVEL1, test22
  sfence.vma

  // Test case 23-24: Test in S-Mode | Valid & Invalid PTEs | RWX set | medeleg[7] set | expected = 1 Store/AMO page fault
  slli a1, a1, 1
  CSRW(medeleg, a1)
  TEST_CASES_RUNNER Smode, va_data, LEVEL1, test23
  sfence.vma
  TEST_CASES_RUNNER Smode, va_data_inv, LEVEL1, test24
  sfence.vma

  // Test case 25-26: Test in S-Mode | Valid & Invalid PTEs | RWX set | medeleg[8] set | expected = 1 Store/AMO page fault
  slli a1, a1, 1
  CSRW(medeleg, a1)
  TEST_CASES_RUNNER Smode, va_data, LEVEL1, test25
  sfence.vma
  TEST_CASES_RUNNER Smode, va_data_inv, LEVEL1, test26
  sfence.vma

  // Test case 27-28: Test in S-Mode | Valid & Invalid PTEs | RWX set | medeleg[9] set | expected = 1 Store/AMO page fault
  slli a1, a1, 1
  CSRW(medeleg, a1)
  TEST_CASES_RUNNER Smode, va_data, LEVEL1, test27, ECALL_DELEG=1
  sfence.vma
  TEST_CASES_RUNNER Smode, va_data_inv, LEVEL1, test28, ECALL_DELEG=1
  sfence.vma

  // Test case 29-30: Test in S-Mode | Valid & Invalid PTEs | RWX set | medeleg[12] set | expected = 1 Store/AMO page fault
  slli a1, a1, 3
  CSRW(medeleg, a1)
  TEST_CASES_RUNNER Smode, va_data, LEVEL1, test29
  sfence.vma
  TEST_CASES_RUNNER Smode, va_data_inv, LEVEL1, test30
  sfence.vma

  // Test case 31-32: Test in S-Mode | Valid & Invalid PTEs | RWX set | medeleg[13] set | expected = 1 Store/AMO page fault
  slli a1, a1, 1
  CSRW(medeleg, a1)
  TEST_CASES_RUNNER Smode, va_data, LEVEL1, test31
  sfence.vma
  TEST_CASES_RUNNER Smode, va_data_inv, LEVEL1, test32
  sfence.vma

  // Test case 33-34: Test in S-Mode | Valid & Invalid PTEs | RWX set | medeleg[15] set | expected = 1 Store/AMO page fault
  slli a1, a1, 2
  CSRW(medeleg, a1)
  TEST_CASES_RUNNER Smode, va_data, LEVEL1, test33
  sfence.vma
  TEST_CASES_RUNNER Smode, va_data_inv, LEVEL1, test34
  sfence.vma

  // Test case 35-36: Test in S-Mode | Valid & Invalid PTEs | RWX set | set medeleg = 0xB1FF | expected = 1 Store/AMO page fault
  LI(a1, 0xB1FF)
  CSRW(medeleg, a1)
  TEST_CASES_RUNNER Smode, va_data, LEVEL1, test35
  sfence.vma
  TEST_CASES_RUNNER Smode, va_data_inv, LEVEL1, test36
  sfence.vma


//---------------------------------------------------------------------------------------------------------------------------------
RVTEST_CODE_END
RVTEST_DATA_BEGIN

//---------------------------------------------------------------------------------------------------------------------------------
//                                            PHYSICAL ADDRESS REGION FOR TESTING
//---------------------------------------------------------------------------------------------------------------------------------
// Physical Address region under testing for LEVEL 0 and 1
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

test1_str:  .string "\"Mismatch in Test Case 1!\""
test2_str:  .string "\"Mismatch in Test Case 2!\""
test3_str:  .string "\"Mismatch in Test Case 3!\""
test4_str:  .string "\"Mismatch in Test Case 4!\""
test5_str:  .string "\"Mismatch in Test Case 5!\""
test6_str:  .string "\"Mismatch in Test Case 6!\""
test7_str:  .string "\"Mismatch in Test Case 7!\""
test8_str:  .string "\"Mismatch in Test Case 8!\""
test9_str:  .string "\"Mismatch in Test Case 9!\""
test10_str:  .string "\"Mismatch in Test Case 10!\""
test11_str:  .string "\"Mismatch in Test Case 11!\""
test12_str:  .string "\"Mismatch in Test Case 12!\""
test13_str:  .string "\"Mismatch in Test Case 13!\""
test14_str:  .string "\"Mismatch in Test Case 14!\""
test15_str:  .string "\"Mismatch in Test Case 15!\""
test16_str:  .string "\"Mismatch in Test Case 16!\""
test17_str:  .string "\"Mismatch in Test Case 17!\""
test18_str:  .string "\"Mismatch in Test Case 18!\""
test19_str:  .string "\"Mismatch in Test Case 19!\""
test20_str:  .string "\"Mismatch in Test Case 20!\""
test21_str:  .string "\"Mismatch in Test Case 21!\""
test22_str:  .string "\"Mismatch in Test Case 22!\""
test23_str:  .string "\"Mismatch in Test Case 23!\""
test24_str:  .string "\"Mismatch in Test Case 24!\""
test25_str:  .string "\"Mismatch in Test Case 25!\""
test26_str:  .string "\"Mismatch in Test Case 26!\""
test27_str:  .string "\"Mismatch in Test Case 27!\""
test28_str:  .string "\"Mismatch in Test Case 28!\""
test29_str:  .string "\"Mismatch in Test Case 29!\""
test30_str:  .string "\"Mismatch in Test Case 30!\""
test31_str:  .string "\"Mismatch in Test Case 31!\""
test32_str:  .string "\"Mismatch in Test Case 32!\""
test33_str:  .string "\"Mismatch in Test Case 33!\""
test34_str:  .string "\"Mismatch in Test Case 34!\""
test35_str:  .string "\"Mismatch in Test Case 34!\""
test36_str:  .string "\"Mismatch in Test Case 34!\""

RVTEST_DATA_END
RVTEST_SIG_SETUP
