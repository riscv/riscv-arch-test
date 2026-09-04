// --------------------------------------------------------------------------------------------------------------------------------
// Developed by: Umer Shahid & Muhammad Zain
// --------------------------------------------------------------------------------------------------------------------------------
// Test cases are as follows:
// --------------------------------------------------------------------------------------------------------------------------------
//  1. Set satp.MODE to Sv57 -> Successful
//  2. All zeros, ones and walking ones on the PPN field of satp when satp.MODE=Sv57 -> Successful
//  3. All zeros, ones and walking ones on the ASID field of satp when satp.MODE=Sv57 -> Successful
//
// Total Expected Faults :: 0
// --------------------------------------------------------------------------------------------------------------------------------

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: [I, Sv57]
# MARCH: rv64i_zicsr_zifencei
##### END_TEST_CONFIG #####

// TODO: Remove BOOT_TO_MMODE when converting this test to T-SBI.
#define BOOT_TO_MMODE

#define SIGUPD_COUNT 70
#define TRAP_SIGUPD_COUNT 10


#include "riscv_arch_test.h"

RVTEST_BEGIN


main:
//---------------------------------------------------------------------------------------------------------------------------------
// Test case 1: Set satp.MODE to Sv57 | Expected: Successful
//---------------------------------------------------------------------------------------------------------------------------------

  LI(a0, SATP_MODE_SV57<<60)      // satp.MODE = 4'b1010 (Sv57)
  csrw satp, a0
  test1_sv57:
  RVTEST_SIGUPD_CSR_READ(satp, a4, test1_sv57, test1_sv57_str)


//---------------------------------------------------------------------------------------------------------------------------------
// Test case 3: Zeros, ones and walking ones on satp.ASID | Expected: Successful
//---------------------------------------------------------------------------------------------------------------------------------

  LI(a1, SATP_MODE_SV57<<60)      // satp.MODE = Sv57

  // satp.ASID = All zeros
  mv   a0, a1
  csrw satp, a0
  test3_zeros:
  RVTEST_SIGUPD_CSR_READ(satp, a4, test3_zeros, test3_zeros_str)

  // satp.ASID = All ones
  LI(  a0, 0xFFFF)
  slli a0, a0, 44
  or   a0, a1, a0
  csrw satp, a0
  test3_ones:
  RVTEST_SIGUPD_CSR_READ(satp, a4, test3_ones, test3_ones_str)

  // satp.ASID = Walking Ones
  li   a2, 1
  slli a2, a2, 44
  .rept(16)
    or   a0, a1, a2
    csrw satp, a0
    6:
    RVTEST_SIGUPD_CSR_READ(satp, a4, 6b, test3_walk_str)
    slli  a2, a2, 1
  .endr


//---------------------------------------------------------------------------------------------------------------------------------
RVTEST_CODE_END
RVTEST_DATA_BEGIN


test1_sv57_str:   .string "\"Mismatch on setting satp.MODE=Sv57 in Test Case 1!\""
test3_zeros_str:  .string "\"Mismatch on setting satp.ASID=Zeros in Test Case 3!\""
test3_ones_str:   .string "\"Mismatch on setting satp.ASID=Ones in Test Case 3!\""
test3_walk_str:   .string "\"Mismatch on walking ones in satp.ASID in Test Case 3!\""

RVTEST_DATA_END
RVTEST_SIG_SETUP
