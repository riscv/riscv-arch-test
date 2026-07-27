// --------------------------------------------------------------------------------------------------------------------------------
// Developed by: Umer Shahid & Muhammad Zain
// --------------------------------------------------------------------------------------------------------------------------------
// Test cases are as follows:
// --------------------------------------------------------------------------------------------------------------------------------
// 2. Execute sfence.w.inval, sinval.vma, sfence.inval.ir & sfence.vma in S-Mode.
//        Expected: No fault
// 3. Execute sfence.w.inval, sinval.vma, sfence.inval.ir & sfence.vma in U-Mode.
//        Expected: 4 Illegal instruction exceptions
//
// Total Expected Faults :: 4
//---------------------------------------------------------------------------------------------------------------------------------

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: [S, Svinval]
# MARCH: rv${XLEN}i_zicsr_zifencei_svinval
##### END_TEST_CONFIG #####

#define SIGUPD_COUNT 10
#define TRAP_SIGUPD_COUNT 30


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
// Test case 1: S-Mode | Execute sfence.w.inval, sinval.vma, sfence.inval.r & sfence.vma
//---------------------------------------------------------------------------------------------------------------------------------

  RVTEST_GOTO_LOWER_MODE Smode

  VERIFICATION_MACRO test1

  RVTEST_GOTO_MMODE

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 2: U-Mode | Execute sfence.w.inval, sinval.vma, sfence.inval.r & sfence.vma
//---------------------------------------------------------------------------------------------------------------------------------

  RVTEST_GOTO_LOWER_MODE Umode

  VERIFICATION_MACRO test2

  RVTEST_GOTO_MMODE

//---------------------------------------------------------------------------------------------------------------------------------
RVTEST_CODE_END
RVTEST_DATA_BEGIN

//---------------------------------------------------------------------------------------------------------------------------------

test1_sfence_w_inval_str:   .string "\"Mismatch during sfence.w.inval in Test Case 1!\""
test1_sinval_vma_str:       .string "\"Mismatch during sinval.vma in Test Case 1!\""
test1_sfence_inval_ir_str:  .string "\"Mismatch during sfence.inval.ir in Test Case 1!\""
test1_sfence_vma_str:       .string "\"Mismatch during sfence.vma in Test Case 1!\""
test2_sfence_w_inval_str:   .string "\"Mismatch during sfence.w.inval in Test Case 2!\""
test2_sinval_vma_str:       .string "\"Mismatch during sinval.vma in Test Case 2!\""
test2_sfence_inval_ir_str:  .string "\"Mismatch during sfence.inval.ir in Test Case 2!\""
test2_sfence_vma_str:       .string "\"Mismatch during sfence.vma in Test Case 2!\""

RVTEST_DATA_END
RVTEST_SIG_SETUP
