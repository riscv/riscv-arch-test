//---------------------------------------------------------------------------------------------------------------------------------
// Developed by: Umer Shahid & Muhammad Zain
//---------------------------------------------------------------------------------------------------------------------------------
// NOTE: Exception types may vary according to section 13.2 of Unpriv ISA Spec and Table 15 of Priv ISA Spec
//---------------------------------------------------------------------------------------------------------------------------------
// Test cases are as follows:
//---------------------------------------------------------------------------------------------------------------------------------
// 1. Setup a valid PTE at level 1 with RWX permissions pointing to test region
//        Then, in M-Mode (mstatus.MPRV set), execute lr.w & sc.w.
//        Expected: No fault
// 2. Setup a valid PTE at level 1 with RWX permissions pointing to test region
//        Then, in M-Mode (mstatus.MPRV set), execute lr.w & sc.w using a misaligned VA.
//        Expected: 1 Load address-misaligned/access fault & 1 Store/AMO address-misaligned/access fault
// 3. Setup a valid PTE at level 1 with RWX permissions pointing to RVMODEL_ACCESS_FAULT_ADDRESS
//        Then, in M-Mode (mstatus.MPRV set), execute lr.w & sc.w.
//        Expected: 1 Load access fault & 1 Store/AMO access fault
// 4. Setup a valid PTE at level 1 with RWX permissions pointing to RVMODEL_ACCESS_FAULT_ADDRESS
//        Then, in M-Mode (mstatus.MPRV set), execute lr.w & sc.w using a misaligned VA.
//        Expected: 1 Load address-misaligned/access fault & 1 Store/AMO address-misaligned/access fault
// 5. Setup an invalid PTE at level 1 with RWX permissions pointing to test region
//        Then, in M-Mode (mstatus.MPRV set), execute lr.w & sc.w.
//        Expected: 1 Load page fault & 1 Store/AMO page fault
// 6. Setup an invalid PTE at level 1 with RWX permissions pointing to test region
//        Then, in M-Mode (mstatus.MPRV set), execute lr.w & sc.w using a misaligned VA.
//        Expected: 1 Load address-misaligned/access/page fault & 1 Store/AMO address-misaligned/access/page fault
// 7. Setup an invalid PTE at level 1 with RWX permissions pointing to RVMODEL_ACCESS_FAULT_ADDRESS
//        Then, in M-Mode (mstatus.MPRV set), execute lr.w & sc.w.
//        Expected: 1 Load page fault & 1 Store/AMO page fault
// 8. Setup an invalid PTE at level 1 with RWX permissions pointing to RVMODEL_ACCESS_FAULT_ADDRESS
//        Then, in M-Mode (mstatus.MPRV set), execute lr.w & sc.w using a misaligned VA.
//        Expected: 1 Load address-misaligned/access/page fault & 1 Store/AMO address-misaligned/access/page fault
// 9-36. Setup valid and invalid PTEs at level 1 with RWX permissions
//        Then, in M-Mode (mstatus.MPRV set) walk through medeleg and execute lr.w & sc.w.
//        Expected: 14 Load page faults & 14 Store/AMO page faults
//
// Total Expected Faults :: 42
//---------------------------------------------------------------------------------------------------------------------------------

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: [I, Sv32, Zalrsc]
# MARCH: rv32i_zicsr_zalrsc
##### END_TEST_CONFIG #####

#define TEST_FILE "sv32_exceptions_Zalrsc_Mmode.S"
#define SIGUPD_COUNT 90
#define TRAP_SIGUPD_COUNT 180
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

  // Set the value again as it changes due to trap
  SET_REQ_MSTATUS_VAL

  \TEST_CASE\()_sc:
  sc.w a4, a2, (a5)
  nop

.endm

.macro TEST_CASES_RUNNER LOWER_MODE, VA, level, TEST_CASE, PA=

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

  SET_REQ_MSTATUS_VAL

  VERIFICATION_RWX \TEST_CASE

  LI(   t0, MSTATUS_MPRV)
  CSRC( mstatus, t0)          // Clear mstatus.MPRV

  // Signature Update
  RVTEST_SIGUPD(x2, x5, x4, a3, \TEST_CASE\()_lr, \TEST_CASE\()_lr_str)
  RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_sc, \TEST_CASE\()_sc_str)
.endm

.macro SET_REQ_MSTATUS_VAL
  LI(   t0, MSTATUS_MPRV)
  CSRS( mstatus, t0)
  LI(   t0, 0x1800)
  CSRC( mstatus, t0)
  LI(   t0, 0x800)
  CSRS( mstatus, t0)          // Set to Smode
.endm

main:
  LI( a2, 0x8)                // Test signature initialization

//---------------------------------------------------------------------------------------------------------------------------------
//                                   Virtual addresses definition for code and test regions
//---------------------------------------------------------------------------------------------------------------------------------

  // Virtual Address of Test section (rvtest_data_1)
  .set va_data,               0x90407000
  .set va_data_inv,           0x90807000

  // Virtual Address for code region
  .set va_rvtest_code_begin,  0x30000000


  // PTE setup for Code Region
  SUPERPAGE_PTE_SETUP_SV32(rvtest_code_begin, (PTE_D | PTE_A | PTE_X | PTE_R | PTE_V), va_rvtest_code_begin, LEVEL1)
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

  // Test case 1-2: Test in M-Mode | Valid PTE | RWX set | expected = 2 faults
  SUPERPAGE_PTE_SETUP_SV32(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER Mmode, va_data, LEVEL1, test1
  sfence.vma
  TEST_CASES_RUNNER Mmode, (va_data+0x2), LEVEL1, test2

//---------------------------------------------------------------------------------------------------------------------------------
//                    4MB PAGE    Region 1 under test at level 1 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 3-4: Test in M-Mode | Valid PTE | RWX set | Points to RVMODEL_ACCESS_FAULT_ADDRESS | expected = 4 faults
  SUPERPAGE_PTE_SETUP_SV32(RVMODEL_ACCESS_FAULT_ADDRESS, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER Mmode, va_data, LEVEL1, test3, RVMODEL_ACCESS_FAULT_ADDRESS
  sfence.vma
  TEST_CASES_RUNNER Mmode, (va_data+0x2), LEVEL1, test4, RVMODEL_ACCESS_FAULT_ADDRESS

//---------------------------------------------------------------------------------------------------------------------------------
//                    4MB PAGE    Region 1 under test at level 1 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 5-6: Test in M-Mode | Invalid PTE | RWX set | expected = 4 faults
  SUPERPAGE_PTE_SETUP_SV32(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R), va_data, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER Mmode, va_data, LEVEL1, test5
  sfence.vma
  TEST_CASES_RUNNER Mmode, (va_data+0x2), LEVEL1, test6

//---------------------------------------------------------------------------------------------------------------------------------
//                    4MB PAGE    Region 1 under test at level 1 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 7-8: Test in M-Mode | Invalid PTE | RWX set | Points to RVMODEL_ACCESS_FAULT_ADDRESS | expected = 4 faults
  SUPERPAGE_PTE_SETUP_SV32(RVMODEL_ACCESS_FAULT_ADDRESS, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R), va_data, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER Mmode, va_data, LEVEL1, test7, RVMODEL_ACCESS_FAULT_ADDRESS
  sfence.vma
  TEST_CASES_RUNNER Mmode, (va_data+0x2), LEVEL1, test8, RVMODEL_ACCESS_FAULT_ADDRESS


//---------------------------------------------------------------------------------------------------------------------------------
//                    4MB PAGE    Region 1 under test at level 1 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  SUPERPAGE_PTE_SETUP_SV32(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL1)   // Valid PTE
  SUPERPAGE_PTE_SETUP_SV32(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R), va_data_inv, LEVEL1)       // Invalid PTE
  sfence.vma

  // Test case 9-10: Test in M-Mode | Valid & Invalid PTEs | RWX set | medeleg[0] set | expected = 2 faults
  li a1, 1
  CSRW(medeleg, a1)
  TEST_CASES_RUNNER Mmode, va_data, LEVEL1, test9
  sfence.vma
  TEST_CASES_RUNNER Mmode, va_data_inv, LEVEL1, test10
  sfence.vma

  // Test case 11-12: Test in M-Mode | Valid & Invalid PTEs | RWX set | medeleg[1] set | expected = 2 faults
  slli a1, a1, 1
  CSRW(medeleg, a1)
  TEST_CASES_RUNNER Mmode, va_data, LEVEL1, test11
  sfence.vma
  TEST_CASES_RUNNER Mmode, va_data_inv, LEVEL1, test12
  sfence.vma

  // Test case 13-14: Test in M-Mode | Valid & Invalid PTEs | RWX set | medeleg[2] set | expected = 2 faults
  slli a1, a1, 1
  CSRW(medeleg, a1)
  TEST_CASES_RUNNER Mmode, va_data, LEVEL1, test13
  sfence.vma
  TEST_CASES_RUNNER Mmode, va_data_inv, LEVEL1, test14
  sfence.vma

  // Test case 15-16: Test in M-Mode | Valid & Invalid PTEs | RWX set | medeleg[3] set | expected = 2 faults
  slli a1, a1, 1
  CSRW(medeleg, a1)
  TEST_CASES_RUNNER Mmode, va_data, LEVEL1, test15
  sfence.vma
  TEST_CASES_RUNNER Mmode, va_data_inv, LEVEL1, test16
  sfence.vma

  // Test case 17-18: Test in M-Mode | Valid & Invalid PTEs | RWX set | medeleg[4] set | expected = 2 faults
  slli a1, a1, 1
  CSRW(medeleg, a1)
  TEST_CASES_RUNNER Mmode, va_data, LEVEL1, test17
  sfence.vma
  TEST_CASES_RUNNER Mmode, va_data_inv, LEVEL1, test18
  sfence.vma

  // Test case 19-20: Test in M-Mode | Valid & Invalid PTEs | RWX set | medeleg[5] set | expected = 2 faults
  slli a1, a1, 1
  CSRW(medeleg, a1)
  TEST_CASES_RUNNER Mmode, va_data, LEVEL1, test19
  sfence.vma
  TEST_CASES_RUNNER Mmode, va_data_inv, LEVEL1, test20
  sfence.vma

  // Test case 21-22: Test in M-Mode | Valid & Invalid PTEs | RWX set | medeleg[6] set | expected = 2 faults
  slli a1, a1, 1
  CSRW(medeleg, a1)
  TEST_CASES_RUNNER Mmode, va_data, LEVEL1, test21
  sfence.vma
  TEST_CASES_RUNNER Mmode, va_data_inv, LEVEL1, test22
  sfence.vma

  // Test case 23-24: Test in M-Mode | Valid & Invalid PTEs | RWX set | medeleg[7] set | expected = 2 faults
  slli a1, a1, 1
  CSRW(medeleg, a1)
  TEST_CASES_RUNNER Mmode, va_data, LEVEL1, test23
  sfence.vma
  TEST_CASES_RUNNER Mmode, va_data_inv, LEVEL1, test24
  sfence.vma

  // Test case 25-26: Test in M-Mode | Valid & Invalid PTEs | RWX set | medeleg[8] set | expected = 2 faults
  slli a1, a1, 1
  CSRW(medeleg, a1)
  TEST_CASES_RUNNER Mmode, va_data, LEVEL1, test25
  sfence.vma
  TEST_CASES_RUNNER Mmode, va_data_inv, LEVEL1, test26
  sfence.vma

  // Test case 27-28: Test in M-Mode | Valid & Invalid PTEs | RWX set | medeleg[9] set | expected = 2 faults
  slli a1, a1, 1
  CSRW(medeleg, a1)
  TEST_CASES_RUNNER Mmode, va_data, LEVEL1, test27
  sfence.vma
  TEST_CASES_RUNNER Mmode, va_data_inv, LEVEL1, test28
  sfence.vma

  // Test case 29-30: Test in M-Mode | Valid & Invalid PTEs | RWX set | medeleg[12] set | expected = 2 faults
  slli a1, a1, 3
  CSRW(medeleg, a1)
  TEST_CASES_RUNNER Mmode, va_data, LEVEL1, test29
  sfence.vma
  TEST_CASES_RUNNER Mmode, va_data_inv, LEVEL1, test30
  sfence.vma

  // Test case 31-32: Test in M-Mode | Valid & Invalid PTEs | RWX set | medeleg[13] set | expected = 2 faults
  slli a1, a1, 1
  CSRW(medeleg, a1)
  TEST_CASES_RUNNER Mmode, va_data, LEVEL1, test31
  sfence.vma
  TEST_CASES_RUNNER Mmode, va_data_inv, LEVEL1, test32
  sfence.vma

  // Test case 33-34: Test in M-Mode | Valid & Invalid PTEs | RWX set | medeleg[15] set | expected = 2 faults
  slli a1, a1, 2
  CSRW(medeleg, a1)
  TEST_CASES_RUNNER Mmode, va_data, LEVEL1, test33
  sfence.vma
  TEST_CASES_RUNNER Mmode, va_data_inv, LEVEL1, test34
  sfence.vma

  // Test case 35-36: Test in M-Mode | Valid & Invalid PTEs | RWX set | set medeleg = 0xB1FF | expected = 2 faults
  LI(a1, 0xB1FF)
  CSRW(medeleg, a1)
  TEST_CASES_RUNNER Mmode, va_data, LEVEL1, test35
  sfence.vma
  TEST_CASES_RUNNER Mmode, va_data_inv, LEVEL1, test36
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
