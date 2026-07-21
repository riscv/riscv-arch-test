// --------------------------------------------------------------------------------------------------------------------------------
// Developed by: Umer Shahid, Muhammad Zain, Hamza Ali, Muhammad Abdullah and Muhammad Ahmed
// --------------------------------------------------------------------------------------------------------------------------------
// This test verifies the functionality of mstatus.TVM bit with the satp and sfence.vma
// Test cases are as follows:
// --------------------------------------------------------------------------------------------------------------------------------
//  1. satp accessed in M-Mode with mstatus.TVM set -> Successful
//  2. sfence.vma accessed in M-Mode with mstatus.TVM set -> Successful
//  3. satp accessed in S-Mode with mstatus.TVM set -> 3 Illegal instruction exceptions
//  4. sfence.vma accessed in S-Mode with mstatus.TVM set -> Illegal instruction exception
//
// Total Expected Faults :: 4
// --------------------------------------------------------------------------------------------------------------------------------

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: [I, S]
# MARCH: rv${XLEN}i_zicsr_zifencei
##### END_TEST_CONFIG #####

#define TEST_FILE "sv_mstatus_tvm_test.S"
#define SIGUPD_COUNT 10
#define TRAP_SIGUPD_COUNT 30
#define BOOT_TO_MMODE


#include "riscv_arch_test.h"

RVTEST_BEGIN

//---------------------------------------------------------------------------------------------------------------------------------
main:

  // Set mstatus.TVM
  LI(   a0, MSTATUS_TVM)
  CSRS( mstatus, a0)

  tvm:
  RVTEST_SIGUPD_CSR_READ(mstatus, a4, tvm, tvm_str)

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 1: Access satp in M-mode | mstatus.TVM set | Expected: Successful access
//---------------------------------------------------------------------------------------------------------------------------------

  CSRW(satp, zero)

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 2: Access sfence.vma in M-mode | mstatus.TVM set | Expected: Successful access
//---------------------------------------------------------------------------------------------------------------------------------

  SFENCE_VMA

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 3: Access satp in S-mode | mstatus.TVM set | Expected: 3 Illegal instruction exceptions
//---------------------------------------------------------------------------------------------------------------------------------

  RVTEST_GOTO_LOWER_MODE Smode

  CSRW(satp, zero)

  CSRS(satp, zero)

  CSRC(satp, zero)

  RVTEST_GOTO_MMODE

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 4: Access satp in S-mode | mstatus.TVM set | Expected: Illegal instruction exception
//---------------------------------------------------------------------------------------------------------------------------------

  RVTEST_GOTO_LOWER_MODE Smode

  SFENCE_VMA

  RVTEST_GOTO_MMODE


//---------------------------------------------------------------------------------------------------------------------------------
RVTEST_CODE_END
RVTEST_DATA_BEGIN

//---------------------------------------------------------------------------------------------------------------------------------

tvm_str:   .string "\"Mismatch in mstatus value while setting TVM bit!\""

RVTEST_DATA_END
RVTEST_SIG_SETUP
