// -----------------------------------------------------------------------------------------------------------------------------------------------
// Developed by: Umer Shahid & Muhammad Zain
// -----------------------------------------------------------------------------------------------------------------------------------------------
// NOTE: Exception types may vary according to Table 15 of Priv ISA Spec
// -----------------------------------------------------------------------------------------------------------------------------------------------
// Test cases are as follows:
// -----------------------------------------------------------------------------------------------------------------------------------------------
// 1. Setup a valid PTE at level 1 with RWX permissions pointing to test region
//        Then, in M-Mode (mstatus.MPRV set, mstatus.MPP=Smode), execute sw, lw & jalr.
//        Expected: No fault
// 2. Setup a valid PTE at level 1 with RWX permissions pointing to test region
//        Then, in M-Mode (mstatus.MPRV set, mstatus.MPP=Smode), execute sw, lw & jalr using a misaligned VA.
//        Expected: Store address misaligned fault & Load address misaligned fault
// 3. Setup a valid PTE at level 1 with RWX permissions pointing to RVMODEL_ACCESS_FAULT_ADDRESS
//        Then, in M-Mode (mstatus.MPRV set, mstatus.MPP=Smode), execute sw, lw & jalr.
//        Expected: Store access fault & Load access fault
// 4. Setup a valid PTE at level 1 with RWX permissions pointing to RVMODEL_ACCESS_FAULT_ADDRESS
//        Then, in M-Mode (mstatus.MPRV set, mstatus.MPP=Smode), execute sw, lw & jalr using a misaligned VA.
//        Expected: Store address misaligned fault & Load address misaligned fault
// 5. Setup an invalid PTE at level 1 with RWX permissions pointing to test region
//        Then, in M-Mode (mstatus.MPRV set, mstatus.MPP=Smode), execute sw, lw & jalr.
//        Expected: Store page fault & Load page fault
// 6. Setup an invalid PTE at level 1 with RWX permissions pointing to test region
//        Then, in M-Mode (mstatus.MPRV set, mstatus.MPP=Smode), execute sw, lw & jalr using a misaligned VA.
//        Expected: Store address misaligned fault & Load address misaligned fault
// 7. Setup an invalid PTE at level 1 with RWX permissions pointing to RVMODEL_ACCESS_FAULT_ADDRESS
//        Then, in M-Mode (mstatus.MPRV set, mstatus.MPP=Smode), execute sw, lw & jalr.
//        Expected: Store page fault & Load page fault
// 8. Setup an invalid PTE at level 1 with RWX permissions pointing to RVMODEL_ACCESS_FAULT_ADDRESS
//        Then, in M-Mode (mstatus.MPRV set, mstatus.MPP=Smode), execute sw, lw & jalr using a misaligned VA.
//        Expected: Store address misaligned fault & Load address misaligned fault
// 9-36. Setup valid and invalid PTEs at level 1 with RWX permissions
//        Then, in M-Mode (mstatus.MPRV set, mstatus.MPP=Smode) walk through medeleg and execute sw, lw & jalr.
//        Expected: 14 Store page faults & 14 Load page faults
//
// Total Expected Faults :: 42
// -----------------------------------------------------------------------------------------------------------------------------------------------

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: [I, Sv32]
# MARCH: rv32i_zicsr
# CONFIG_DEPENDENT: true
##### END_TEST_CONFIG #####

#define TEST_FILE "sv32_exceptions_mprv_Mmode.S"
#define SIGUPD_COUNT 115
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
  addi a2, a2, 16

  // Test store permission
  \TEST_CASE\()_store:
  sw  a2, 16(a5)
  nop

  SET_REQ_MSTATUS_VAL

  // Test load permission
  \TEST_CASE\()_load:
  lw a3, 16(a5)
  nop

  LA(a5, rvtest_data_1)       // Using physical address for fetch
  SET_REQ_MSTATUS_VAL

  // Test execute permission
  LI(  x4, 0xACCE)            // Store a value which is to be checked in trap handler
  \TEST_CASE\()_exec:
  jalr ra, a5, 0
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
  RVTEST_SIGUPD(x2, x5, x4, a2, \TEST_CASE\()_store, \TEST_CASE\()_store_str)
  RVTEST_SIGUPD(x2, x5, x4, a3, \TEST_CASE\()_load, \TEST_CASE\()_load_str)
  RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_exec, \TEST_CASE\()_exec_str)
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
  LI( a2, 0x800)              // Test signature initialization

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

  // MPRV does not affect instruction fetches. Setting up an identity mapped PTE with V=0. If MPRV incorrectly
  // affects fetches, it will raise a fault due to PTE.V=0.
  SUPERPAGE_PTE_SETUP_SV32(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R), 0x80000000, LEVEL1)
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
test21_store_str: .string "\"Mismatch during sw in Test Case 21!\""
test21_load_str:  .string "\"Mismatch during lw in Test Case 21!\""
test21_exec_str:  .string "\"Mismatch during jalr in Test Case 21!\""
test22_store_str: .string "\"Mismatch during sw in Test Case 22!\""
test22_load_str:  .string "\"Mismatch during lw in Test Case 22!\""
test22_exec_str:  .string "\"Mismatch during jalr in Test Case 22!\""
test23_store_str: .string "\"Mismatch during sw in Test Case 23!\""
test23_load_str:  .string "\"Mismatch during lw in Test Case 23!\""
test23_exec_str:  .string "\"Mismatch during jalr in Test Case 23!\""
test24_store_str: .string "\"Mismatch during sw in Test Case 24!\""
test24_load_str:  .string "\"Mismatch during lw in Test Case 24!\""
test24_exec_str:  .string "\"Mismatch during jalr in Test Case 24!\""
test25_store_str: .string "\"Mismatch during sw in Test Case 25!\""
test25_load_str:  .string "\"Mismatch during lw in Test Case 25!\""
test25_exec_str:  .string "\"Mismatch during jalr in Test Case 25!\""
test26_store_str: .string "\"Mismatch during sw in Test Case 26!\""
test26_load_str:  .string "\"Mismatch during lw in Test Case 26!\""
test26_exec_str:  .string "\"Mismatch during jalr in Test Case 26!\""
test27_store_str: .string "\"Mismatch during sw in Test Case 27!\""
test27_load_str:  .string "\"Mismatch during lw in Test Case 27!\""
test27_exec_str:  .string "\"Mismatch during jalr in Test Case 27!\""
test28_store_str: .string "\"Mismatch during sw in Test Case 28!\""
test28_load_str:  .string "\"Mismatch during lw in Test Case 28!\""
test28_exec_str:  .string "\"Mismatch during jalr in Test Case 28!\""
test29_store_str: .string "\"Mismatch during sw in Test Case 29!\""
test29_load_str:  .string "\"Mismatch during lw in Test Case 29!\""
test29_exec_str:  .string "\"Mismatch during jalr in Test Case 29!\""
test30_store_str: .string "\"Mismatch during sw in Test Case 30!\""
test30_load_str:  .string "\"Mismatch during lw in Test Case 30!\""
test30_exec_str:  .string "\"Mismatch during jalr in Test Case 30!\""
test31_store_str: .string "\"Mismatch during sw in Test Case 31!\""
test31_load_str:  .string "\"Mismatch during lw in Test Case 31!\""
test31_exec_str:  .string "\"Mismatch during jalr in Test Case 31!\""
test32_store_str: .string "\"Mismatch during sw in Test Case 32!\""
test32_load_str:  .string "\"Mismatch during lw in Test Case 32!\""
test32_exec_str:  .string "\"Mismatch during jalr in Test Case 32!\""
test33_store_str: .string "\"Mismatch during sw in Test Case 33!\""
test33_load_str:  .string "\"Mismatch during lw in Test Case 33!\""
test33_exec_str:  .string "\"Mismatch during jalr in Test Case 33!\""
test34_store_str: .string "\"Mismatch during sw in Test Case 34!\""
test34_load_str:  .string "\"Mismatch during lw in Test Case 34!\""
test34_exec_str:  .string "\"Mismatch during jalr in Test Case 34!\""
test35_store_str: .string "\"Mismatch during sw in Test Case 35!\""
test35_load_str:  .string "\"Mismatch during lw in Test Case 35!\""
test35_exec_str:  .string "\"Mismatch during jalr in Test Case 35!\""
test36_store_str: .string "\"Mismatch during sw in Test Case 36!\""
test36_load_str:  .string "\"Mismatch during lw in Test Case 36!\""
test36_exec_str:  .string "\"Mismatch during jalr in Test Case 36!\""

RVTEST_DATA_END
RVTEST_SIG_SETUP
