// --------------------------------------------------------------------------------------------------------------------------------
// Developed by: Umer Shahid & Muhammad Zain
// --------------------------------------------------------------------------------------------------------------------------------
// Test cases are as follows:
// --------------------------------------------------------------------------------------------------------------------------------
// 1. mstatus.TVM=0, execute sfence.w.inval, sinval.vma, sfence.inval.ir & sfence.vma in M-Mode.
//        Expected: No fault
// 2. mstatus.TVM=1, execute sfence.w.inval, sinval.vma, sfence.inval.ir & sfence.vma in M-Mode.
//        Expected: No fault
// 3. mstatus.TVM=1, execute sfence.w.inval, sinval.vma, sfence.inval.ir & sfence.vma in S-Mode.
//        Expected: 2 Illegal instruction exceptions
// 4. mstatus.TVM=1, execute sfence.w.inval, sinval.vma, sfence.inval.ir & sfence.vma in U-Mode.
//        Expected: 4 Illegal instruction exceptions
//
// Total Expected Faults :: 6
//---------------------------------------------------------------------------------------------------------------------------------

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: [Sm, S, Svinval]
# MARCH: rv${XLEN}i_zicsr_zifencei_svinval
##### END_TEST_CONFIG #####

#define TEST_FILE "Svinval_mstatus_tvm.S"
#define SIGUPD_COUNT 10
#define TRAP_SIGUPD_COUNT 50
#define BOOT_TO_MMODE


#include "riscv_arch_test.h"

RVTEST_BEGIN

//---------------------------------------------------------------------------------------------------------------------------------
// Test RWX permissions
.macro VERIFICATION_MACRO TEST_CASE

  \TEST_CASE\()_sfence_w_inval:
  sfence.w.inval
  nop

  \TEST_CASE\()_sinval_vma:
  sinval.vma x0, x0
  nop

  \TEST_CASE\()_sfence_inval_ir:
  sfence.inval.ir
  nop

  \TEST_CASE\()_sfence_vma:
  sfence.vma x0, x0
  nop

.endm


main:

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 1: mstatus.TVM=0 | M-Mode | Execute sfence.w.inval, sinval.vma, sfence.inval.r & sfence.vma
//---------------------------------------------------------------------------------------------------------------------------------

  VERIFICATION_MACRO test1

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 2: mstatus.TVM=1 | M-Mode | Execute sfence.w.inval, sinval.vma, sfence.inval.r & sfence.vma
//---------------------------------------------------------------------------------------------------------------------------------

  // Set mstatus.TVM
  LI(   a0, MSTATUS_TVM)
  CSRS( mstatus, a0)
  tvm:
  RVTEST_SIGUPD_CSR_READ(mstatus, a4, tvm, tvm_str)

  VERIFICATION_MACRO test2

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 3: mstatus.TVM=1 | S-Mode | Execute sfence.w.inval, sinval.vma, sfence.inval.r & sfence.vma
//---------------------------------------------------------------------------------------------------------------------------------

  RVTEST_GOTO_LOWER_MODE Smode

  VERIFICATION_MACRO test3

  RVTEST_GOTO_MMODE

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 4: mstatus.TVM=1 | U-Mode | Execute sfence.w.inval, sinval.vma, sfence.inval.r & sfence.vma
//---------------------------------------------------------------------------------------------------------------------------------

  RVTEST_GOTO_LOWER_MODE Umode

  VERIFICATION_MACRO test4

  RVTEST_GOTO_MMODE

//---------------------------------------------------------------------------------------------------------------------------------
RVTEST_CODE_END
RVTEST_DATA_BEGIN

//---------------------------------------------------------------------------------------------------------------------------------

tvm_str:                    .string "\"Mismatch in mstatus value while setting TVM bit!\""
test1_sfence_w_inval_str:   .string "\"Mismatch during sfence.w.inval in Test Case 1!\""
test1_sinval_vma_str:       .string "\"Mismatch during sinval.vma in Test Case 1!\""
test1_sfence_inval_ir_str:  .string "\"Mismatch during sfence.inval.ir in Test Case 1!\""
test1_sfence_vma_str:       .string "\"Mismatch during sfence.vma in Test Case 1!\""
test2_sfence_w_inval_str:   .string "\"Mismatch during sfence.w.inval in Test Case 2!\""
test2_sinval_vma_str:       .string "\"Mismatch during sinval.vma in Test Case 2!\""
test2_sfence_inval_ir_str:  .string "\"Mismatch during sfence.inval.ir in Test Case 2!\""
test2_sfence_vma_str:       .string "\"Mismatch during sfence.vma in Test Case 2!\""
test3_sfence_w_inval_str:   .string "\"Mismatch during sfence.w.inval in Test Case 3!\""
test3_sinval_vma_str:       .string "\"Mismatch during sinval.vma in Test Case 3!\""
test3_sfence_inval_ir_str:  .string "\"Mismatch during sfence.inval.ir in Test Case 3!\""
test3_sfence_vma_str:       .string "\"Mismatch during sfence.vma in Test Case 3!\""
test4_sfence_w_inval_str:   .string "\"Mismatch during sfence.w.inval in Test Case 4!\""
test4_sinval_vma_str:       .string "\"Mismatch during sinval.vma in Test Case 4!\""
test4_sfence_inval_ir_str:  .string "\"Mismatch during sfence.inval.ir in Test Case 4!\""
test4_sfence_vma_str:       .string "\"Mismatch during sfence.vma in Test Case 4!\""

RVTEST_DATA_END
RVTEST_SIG_SETUP
